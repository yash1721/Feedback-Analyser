import csv
from dataclasses import dataclass
from io import StringIO

from app.core.exceptions import BadRequestError


@dataclass(frozen=True)
class CsvParsedRow:
    row_number: int
    text: str | None
    error_message: str | None = None


class CsvFeedbackParser:
    TEXT_COLUMNS = ("text", "feedback_text")

    def parse(self, content: bytes) -> list[CsvParsedRow]:
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise BadRequestError("CSV must be UTF-8 encoded.") from exc

        reader = csv.DictReader(StringIO(decoded))
        if not reader.fieldnames:
            raise BadRequestError("CSV must include a header row.")

        text_column = self._find_text_column(reader.fieldnames)
        if text_column is None:
            raise BadRequestError("CSV must include a text or feedback_text column.")

        parsed_rows: list[CsvParsedRow] = []
        for row_number, row in enumerate(reader, start=2):
            text = (row.get(text_column) or "").strip()
            if not text:
                parsed_rows.append(CsvParsedRow(row_number=row_number, text=None, error_message="Feedback text is required."))
                continue
            parsed_rows.append(CsvParsedRow(row_number=row_number, text=text))
        return parsed_rows

    def _find_text_column(self, fieldnames: list[str]) -> str | None:
        normalized = {field.strip().lower(): field for field in fieldnames}
        for column in self.TEXT_COLUMNS:
            if column in normalized:
                return normalized[column]
        return None
