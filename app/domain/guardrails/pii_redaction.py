import ipaddress
import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s()]{7,}\d)")
CARD_CANDIDATE_RE = re.compile(r"(?:\d[ -]?){13,19}")
LONG_ID_RE = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


@dataclass(frozen=True)
class PiiRedactionResult:
    original_text: str
    redacted_text: str
    detected: bool
    pii_types: list[str]


class PIIRedactionService:
    def redact(self, text: str | None) -> PiiRedactionResult:
        original = text or ""
        redacted = original
        pii_types: set[str] = set()
        if EMAIL_RE.search(redacted):
            pii_types.add("email")
            redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
        for match in CARD_CANDIDATE_RE.findall(redacted):
            digits = re.sub(r"\D", "", match)
            if len(digits) >= 13 and _luhn_valid(digits):
                pii_types.add("credit_card")
                redacted = redacted.replace(match, "[REDACTED_CARD]")
        if PHONE_RE.search(redacted):
            pii_types.add("phone")
            redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
        for match in IP_RE.findall(redacted):
            try:
                ipaddress.ip_address(match)
            except ValueError:
                continue
            pii_types.add("ip_address")
            redacted = redacted.replace(match, "[REDACTED_IP]")
        if LONG_ID_RE.search(redacted):
            pii_types.add("id_number")
            redacted = LONG_ID_RE.sub("[REDACTED_ID]", redacted)
        return PiiRedactionResult(
            original_text=original,
            redacted_text=redacted,
            detected=bool(pii_types),
            pii_types=sorted(pii_types),
        )


def _luhn_valid(digits: str) -> bool:
    total = 0
    reverse_digits = digits[::-1]
    for index, char in enumerate(reverse_digits):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0
