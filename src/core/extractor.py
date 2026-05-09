import re

_KZ_PREFIX_DIGITS = "77"

_RAW_PATTERN = re.compile(
    r'(?:\+?7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}'
)


def extract_kz_phones(text: str) -> set[str]:
    if not text:
        return set()

    clean_phones: set[str] = set()
    for match in _RAW_PATTERN.findall(text):
        digits_only = re.sub(r"\D", "", match)
        if digits_only.startswith("8"):
            digits_only = "7" + digits_only[1:]
        if len(digits_only) == 11 and digits_only.startswith(_KZ_PREFIX_DIGITS):
            clean_phones.add(f"+{digits_only}")
    return clean_phones
