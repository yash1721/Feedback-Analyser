import unicodedata


class TextNormalizer:
    def normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        return " ".join(normalized.split())
