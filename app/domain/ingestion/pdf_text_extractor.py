from io import BytesIO

from app.core.exceptions import BadRequestError


class PdfTextExtractor:
    def extract_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise BadRequestError("pypdf is not installed.") from exc

        try:
            reader = PdfReader(BytesIO(content))
            page_text = [(page.extract_text() or "") for page in reader.pages]
        except Exception as exc:
            raise BadRequestError("PDF text could not be extracted.") from exc

        extracted = "\n".join(text for text in page_text if text.strip()).strip()
        if not extracted:
            raise BadRequestError("PDF did not contain extractable text.")
        return extracted
