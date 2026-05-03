from ExternalData import external_data as legacy_external_data


def _clean_text(text: str) -> str:
    return (
        text.replace("â€™", "'")
        .replace("â€œ", '"')
        .replace("â€", '"')
        .replace("â€˜", "'")
    )


external_data = [_clean_text(item) for item in legacy_external_data]
