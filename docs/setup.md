# Setup

## Local Python

Use Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Native OCR Dependency

Tesseract must be installed for real OCR. Docker installs it automatically. For local Windows development, install Tesseract and ensure the executable is on `PATH`.

## Tests

```bash
pytest
```

