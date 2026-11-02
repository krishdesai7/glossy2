"""Spelling normalisation for lookups only. Output always keeps the user's spelling."""

import unicodedata

_YCOE_CODES = {"+t": "þ", "+d": "þ", "+a": "æ", "+g": "g", "+l": "l"}


def normalize(form: str) -> str:
    text = form.lower().replace("$", "").replace("-", "")
    for code, letter in _YCOE_CODES.items():
        text = text.replace(code, letter)
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.replace("ð", "þ").replace("ȝ", "g")
