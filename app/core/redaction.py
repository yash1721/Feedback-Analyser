import hashlib
import re


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{7,}\d)")


def redact_text_preview(text: str | None, *, max_length: int = 120) -> dict:
    if not text:
        return {"text_length": 0, "text_hash": None, "preview": None}
    normalized = str(text)
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", normalized)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    preview = redacted[:max_length]
    if len(redacted) > max_length:
        preview = f"{preview}..."
    return {
        "text_length": len(normalized),
        "text_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "preview": preview,
    }
