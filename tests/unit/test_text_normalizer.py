from app.domain.ingestion.text_normalizer import TextNormalizer


def test_text_normalizer_collapses_whitespace_and_preserves_case():
    normalizer = TextNormalizer()

    assert normalizer.normalize("  Checkout\t\tFAILED\nagain.  ") == "Checkout FAILED again."
