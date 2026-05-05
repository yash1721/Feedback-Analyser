from pathlib import PurePath

from app.config import Settings
from app.core.exceptions import BadRequestError, FeedbackIQError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.metrics import FILE_UPLOAD_REJECTED_TOTAL, INGESTION_REQUESTS_TOTAL, PII_REDACTIONS_TOTAL, PROMPT_INJECTION_DETECTED_TOTAL
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.feedback.service import FeedbackService
from app.domain.guardrails.pii_redaction import PIIRedactionService
from app.domain.guardrails.prompt_injection import PromptInjectionDetector, PromptInjectionRisk
from app.domain.ingestion.csv_parser import CsvFeedbackParser
from app.domain.ingestion.image_downloader import ImageDownloader
from app.domain.ingestion.ingestion_service import IngestionService
from app.domain.ingestion.pdf_text_extractor import PdfTextExtractor
from app.domain.security.service import SecurityAuditService
from app.domain.storage.storage_provider import StorageProvider


class MultimodalIngestionService:
    def __init__(
        self,
        *,
        feedback_service: FeedbackService,
        storage_provider: StorageProvider,
        image_ingestion_service: IngestionService,
        image_downloader: ImageDownloader,
        pdf_text_extractor: PdfTextExtractor,
        csv_parser: CsvFeedbackParser,
        max_image_bytes: int,
        max_pdf_bytes: int,
        max_csv_bytes: int,
        settings: Settings,
        pii_service: PIIRedactionService | None = None,
        prompt_injection_detector: PromptInjectionDetector | None = None,
        security_audit_service: SecurityAuditService | None = None,
    ) -> None:
        self.feedback_service = feedback_service
        self.storage_provider = storage_provider
        self.image_ingestion_service = image_ingestion_service
        self.image_downloader = image_downloader
        self.pdf_text_extractor = pdf_text_extractor
        self.csv_parser = csv_parser
        self.max_image_bytes = max_image_bytes
        self.max_pdf_bytes = max_pdf_bytes
        self.max_csv_bytes = max_csv_bytes
        self.settings = settings
        self.pii_service = pii_service or PIIRedactionService()
        self.prompt_injection_detector = prompt_injection_detector or PromptInjectionDetector()
        self.security_audit_service = security_audit_service

    def ingest_text(self, text: str) -> FeedbackRecord:
        metadata = self._security_metadata(text)
        record = self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text=text if self.settings.pii_store_raw_text else metadata["sanitized_text"],
            extracted_text=text,
            sanitized_text=metadata["sanitized_text"],
            pii_detected=metadata["pii_detected"],
            pii_types_json=metadata["pii_types_json"],
            prompt_injection_detected=metadata["prompt_injection_detected"],
            prompt_injection_risk=metadata["prompt_injection_risk"],
            prompt_injection_patterns_json=metadata["prompt_injection_patterns_json"],
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.TEXT.value, status="success").inc()
        return record

    def ingest_image_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> FeedbackRecord:
        self._validate_filename(filename, {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"})
        self._validate_content_type(content_type, expected_prefix="image/", message="Uploaded file must be an image.")
        self._validate_size(content, self.max_image_bytes, "Uploaded image exceeds the configured maximum size.")
        stored = self.storage_provider.save(content=content, original_filename=filename)
        try:
            extracted_text = self.image_ingestion_service.extract_from_bytes(content)
        except FeedbackIQError as exc:
            record = self._create_failed_record(
                source_type=FeedbackSourceType.IMAGE,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
            INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.IMAGE.value, status="failed").inc()
            return record
        metadata = self._security_metadata(extracted_text)
        record = self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.IMAGE,
            original_input_reference=stored.storage_key,
            extracted_text=extracted_text,
            sanitized_text=metadata["sanitized_text"],
            pii_detected=metadata["pii_detected"],
            pii_types_json=metadata["pii_types_json"],
            prompt_injection_detected=metadata["prompt_injection_detected"],
            prompt_injection_risk=metadata["prompt_injection_risk"],
            prompt_injection_patterns_json=metadata["prompt_injection_patterns_json"],
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.IMAGE.value, status="success").inc()
        return record

    def ingest_image_url(self, url: str) -> FeedbackRecord:
        try:
            downloaded = self.image_downloader.download_image(url)
        except FeedbackIQError as exc:
            if exc.code == "unsafe_url":
                self._audit_security_event(
                    event_type="unsafe_url_blocked",
                    severity="MEDIUM",
                    decision="BLOCKED",
                    reason=exc.message,
                    metadata={},
                )
                if self.security_audit_service is not None:
                    self.security_audit_service.repository.session.commit()
            raise
        stored = self.storage_provider.save(content=downloaded.content, original_filename=self._filename_from_content_type(downloaded.content_type))
        try:
            extracted_text = self.image_ingestion_service.extract_from_image(downloaded.image)
        except FeedbackIQError as exc:
            record = self._create_failed_record(
                source_type=FeedbackSourceType.IMAGE,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
            INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.IMAGE.value, status="failed").inc()
            return record
        metadata = self._security_metadata(extracted_text)
        record = self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.IMAGE,
            original_input_reference=stored.storage_key,
            raw_text=url,
            extracted_text=extracted_text,
            sanitized_text=metadata["sanitized_text"],
            pii_detected=metadata["pii_detected"],
            pii_types_json=metadata["pii_types_json"],
            prompt_injection_detected=metadata["prompt_injection_detected"],
            prompt_injection_risk=metadata["prompt_injection_risk"],
            prompt_injection_patterns_json=metadata["prompt_injection_patterns_json"],
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.IMAGE.value, status="success").inc()
        return record

    def ingest_pdf_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> FeedbackRecord:
        self._validate_filename(filename, {"pdf"})
        if (content_type or "").lower().split(";")[0] != "application/pdf":
            raise UnsupportedMediaTypeError("Uploaded file must be a PDF.", {"content_type": content_type})
        self._validate_size(content, self.max_pdf_bytes, "Uploaded PDF exceeds the configured maximum size.")
        stored = self.storage_provider.save(content=content, original_filename=filename)
        try:
            extracted_text = self.pdf_text_extractor.extract_text(content)
        except FeedbackIQError as exc:
            record = self._create_failed_record(
                source_type=FeedbackSourceType.PDF,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
            INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.PDF.value, status="failed").inc()
            return record
        metadata = self._security_metadata(extracted_text)
        record = self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.PDF,
            original_input_reference=stored.storage_key,
            extracted_text=extracted_text,
            sanitized_text=metadata["sanitized_text"],
            pii_detected=metadata["pii_detected"],
            pii_types_json=metadata["pii_types_json"],
            prompt_injection_detected=metadata["prompt_injection_detected"],
            prompt_injection_risk=metadata["prompt_injection_risk"],
            prompt_injection_patterns_json=metadata["prompt_injection_patterns_json"],
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        INGESTION_REQUESTS_TOTAL.labels(source_type=FeedbackSourceType.PDF.value, status="success").inc()
        return record

    def ingest_csv_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> tuple[str, list[FeedbackRecord], list[dict]]:
        self._validate_filename(filename, {"csv"})
        normalized_content_type = (content_type or "").lower().split(";")[0]
        if normalized_content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"} and not (filename or "").lower().endswith(".csv"):
            raise UnsupportedMediaTypeError("Uploaded file must be a CSV.", {"content_type": content_type})
        self._validate_size(content, self.max_csv_bytes, "Uploaded CSV exceeds the configured maximum size.")
        stored = self.storage_provider.save(content=content, original_filename=filename)
        parsed_rows = self.csv_parser.parse(content)
        records: list[FeedbackRecord] = []
        row_errors: list[dict] = []
        for parsed_row in parsed_rows:
            if parsed_row.error_message is not None or parsed_row.text is None:
                row_errors.append(
                    {
                        "row_number": parsed_row.row_number,
                        "error_code": "invalid_row",
                        "error_message": parsed_row.error_message or "Invalid CSV row.",
                    }
                )
                continue
            metadata = self._security_metadata(parsed_row.text)
            records.append(
                self.feedback_service.create_ingested_feedback(
                    source_type=FeedbackSourceType.CSV,
                    original_input_reference=stored.storage_key,
                    raw_text=parsed_row.text if self.settings.pii_store_raw_text else metadata["sanitized_text"],
                    extracted_text=parsed_row.text,
                    sanitized_text=metadata["sanitized_text"],
                    pii_detected=metadata["pii_detected"],
                    pii_types_json=metadata["pii_types_json"],
                    prompt_injection_detected=metadata["prompt_injection_detected"],
                    prompt_injection_risk=metadata["prompt_injection_risk"],
                    prompt_injection_patterns_json=metadata["prompt_injection_patterns_json"],
                    processing_status=FeedbackProcessingStatus.EXTRACTED,
                )
            )
        INGESTION_REQUESTS_TOTAL.labels(
            source_type=FeedbackSourceType.CSV.value,
            status="partial_failure" if row_errors else "success",
        ).inc()
        return stored.storage_key, records, row_errors

    def _create_failed_record(
        self,
        *,
        source_type: FeedbackSourceType,
        original_input_reference: str,
        error_code: str,
        error_message: str,
    ) -> FeedbackRecord:
        return self.feedback_service.create_ingested_feedback(
            source_type=source_type,
            original_input_reference=original_input_reference,
            processing_status=FeedbackProcessingStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )

    @staticmethod
    def _validate_content_type(content_type: str | None, *, expected_prefix: str, message: str) -> None:
        normalized_content_type = (content_type or "").lower()
        if not normalized_content_type.startswith(expected_prefix):
            raise UnsupportedMediaTypeError(message, {"content_type": content_type})

    @staticmethod
    def _validate_size(content: bytes, max_bytes: int, message: str) -> None:
        if len(content) > max_bytes:
            raise PayloadTooLargeError(message)
        if not content:
            raise BadRequestError("Uploaded file cannot be empty.")

    def _validate_filename(self, filename: str | None, allowed_extensions: set[str]) -> None:
        if not filename:
            return
        if "\x00" in filename or "/" in filename or "\\" in filename or PurePath(filename).name != filename:
            FILE_UPLOAD_REJECTED_TOTAL.labels(reason="unsafe_filename").inc()
            self._audit_security_event(
                event_type="file_upload_rejected",
                severity="MEDIUM",
                decision="BLOCKED",
                reason="Unsafe filename rejected.",
                metadata={"reason": "unsafe_filename"},
            )
            if self.security_audit_service is not None:
                self.security_audit_service.repository.session.commit()
            raise BadRequestError("Uploaded filename is not safe.")
        extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
        if extension not in allowed_extensions:
            FILE_UPLOAD_REJECTED_TOTAL.labels(reason="invalid_extension").inc()
            self._audit_security_event(
                event_type="file_upload_rejected",
                severity="LOW",
                decision="BLOCKED",
                reason="Invalid file extension rejected.",
                metadata={"reason": "invalid_extension", "extension": extension},
            )
            if self.security_audit_service is not None:
                self.security_audit_service.repository.session.commit()
            raise UnsupportedMediaTypeError("Uploaded file extension is not allowed.", {"filename": filename})

    def _security_metadata(self, text: str | None) -> dict:
        pii_result = self.pii_service.redact(text) if self.settings.pii_redaction_enabled else None
        sanitized_text = pii_result.redacted_text if pii_result is not None else text
        if pii_result is not None and pii_result.detected:
            for pii_type in pii_result.pii_types:
                PII_REDACTIONS_TOTAL.labels(pii_type=pii_type).inc()
            self._audit_security_event(
                event_type="pii_redacted",
                severity="LOW",
                decision="REDACTED",
                reason="PII-like data was redacted from input text.",
                metadata={"pii_types": pii_result.pii_types},
            )

        injection = self.prompt_injection_detector.detect(text) if self.settings.prompt_injection_detection_enabled else None
        if injection is not None and injection.detected:
            PROMPT_INJECTION_DETECTED_TOTAL.labels(risk_level=injection.risk_level.value).inc()
            self._audit_security_event(
                event_type="prompt_injection_detected",
                severity=injection.risk_level.value,
                decision="BLOCKED" if self.settings.prompt_injection_mode == "block" and injection.risk_level == PromptInjectionRisk.HIGH else "ALLOWED",
                reason="Prompt-injection-like instructions were detected.",
                metadata={"matched_patterns": injection.matched_patterns},
            )
            if self.settings.prompt_injection_mode == "block" and injection.risk_level == PromptInjectionRisk.HIGH:
                raise BadRequestError("Input contains high-risk prompt-injection instructions.")

        return {
            "sanitized_text": sanitized_text,
            "pii_detected": bool(pii_result and pii_result.detected),
            "pii_types_json": pii_result.pii_types if pii_result is not None and pii_result.detected else None,
            "prompt_injection_detected": bool(injection and injection.detected),
            "prompt_injection_risk": injection.risk_level.value if injection is not None and injection.detected else None,
            "prompt_injection_patterns_json": injection.matched_patterns if injection is not None and injection.detected else None,
        }

    def _audit_security_event(self, *, event_type: str, severity: str, decision: str, reason: str, metadata: dict) -> None:
        if self.security_audit_service is None:
            return
        self.security_audit_service.record_event(
            event_type=event_type,
            severity=severity,
            decision=decision,
            reason=reason,
            metadata=metadata,
            commit=False,
        )

    @staticmethod
    def _filename_from_content_type(content_type: str) -> str:
        subtype = content_type.split("/", maxsplit=1)[-1].split("+", maxsplit=1)[0]
        extension = subtype if subtype else "img"
        return f"downloaded-image.{extension}"
