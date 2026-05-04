import pytest

from app.core.exceptions import BadRequestError
from app.domain.ingestion.csv_parser import CsvFeedbackParser


def test_csv_parser_accepts_feedback_text_column():
    rows = CsvFeedbackParser().parse(b"feedback_text\nCheckout failed.\n")

    assert rows[0].row_number == 2
    assert rows[0].text == "Checkout failed."


def test_csv_parser_marks_blank_rows_invalid():
    rows = CsvFeedbackParser().parse(b"text\n   \n")

    assert rows[0].error_message == "Feedback text is required."


def test_csv_parser_requires_text_column():
    with pytest.raises(BadRequestError):
        CsvFeedbackParser().parse(b"message\nhello\n")
