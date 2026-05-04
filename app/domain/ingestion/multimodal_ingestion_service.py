from app.core.exceptions import BadRequestError, FeedbackIQError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackRecord, FeedbackSourceType
from app.domain.feedback.service import FeedbackService
from app.domain.ingestion.csv_parser import CsvFeedbackParser
from app.domain.ingestion.image_downloader import ImageDownloader
from app.domain.ingestion.ingestion_service import IngestionService
from app.domain.ingestion.pdf_text_extractor import PdfTextExtractor
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

    def ingest_text(self, text: str) -> FeedbackRecord:
        return self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text=text,
            extracted_text=text,
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )

    def ingest_image_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> FeedbackRecord:
        self._validate_content_type(content_type, expected_prefix="image/", message="Uploaded file must be an image.")
        self._validate_size(content, self.max_image_bytes, "Uploaded image exceeds the configured maximum size.")
        stored = self.storage_provider.save(content=content, original_filename=filename)
        try:
            extracted_text = self.image_ingestion_service.extract_from_bytes(content)
        except FeedbackIQError as exc:
            return self._create_failed_record(
                source_type=FeedbackSourceType.IMAGE,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
        return self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.IMAGE,
            original_input_reference=stored.storage_key,
            extracted_text=extracted_text,
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )

    def ingest_image_url(self, url: str) -> FeedbackRecord:
        try:
            downloaded = self.image_downloader.download_image(url)
        except FeedbackIQError:
            raise
        stored = self.storage_provider.save(content=downloaded.content, original_filename=self._filename_from_content_type(downloaded.content_type))
        try:
            extracted_text = self.image_ingestion_service.extract_from_image(downloaded.image)
        except FeedbackIQError as exc:
            return self._create_failed_record(
                source_type=FeedbackSourceType.IMAGE,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
        return self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.IMAGE,
            original_input_reference=stored.storage_key,
            raw_text=url,
            extracted_text=extracted_text,
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )

    def ingest_pdf_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> FeedbackRecord:
        if (content_type or "").lower().split(";")[0] != "application/pdf":
            raise UnsupportedMediaTypeError("Uploaded file must be a PDF.", {"content_type": content_type})
        self._validate_size(content, self.max_pdf_bytes, "Uploaded PDF exceeds the configured maximum size.")
        stored = self.storage_provider.save(content=content, original_filename=filename)
        try:
            extracted_text = self.pdf_text_extractor.extract_text(content)
        except FeedbackIQError as exc:
            return self._create_failed_record(
                source_type=FeedbackSourceType.PDF,
                original_input_reference=stored.storage_key,
                error_code=exc.code,
                error_message=exc.message,
            )
        return self.feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.PDF,
            original_input_reference=stored.storage_key,
            extracted_text=extracted_text,
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )

    def ingest_csv_upload(self, *, content: bytes, filename: str | None, content_type: str | None) -> tuple[str, list[FeedbackRecord], list[dict]]:
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
            records.append(
                self.feedback_service.create_ingested_feedback(
                    source_type=FeedbackSourceType.CSV,
                    original_input_reference=stored.storage_key,
                    raw_text=parsed_row.text,
                    extracted_text=parsed_row.text,
                    processing_status=FeedbackProcessingStatus.EXTRACTED,
                )
            )
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

    @staticmethod
    def _filename_from_content_type(content_type: str) -> str:
        subtype = content_type.split("/", maxsplit=1)[-1].split("+", maxsplit=1)[0]
        extension = subtype if subtype else "img"
        return f"downloaded-image.{extension}"
