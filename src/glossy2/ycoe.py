"""YCOE lookups: which tags each form has been seen with, and what those tags mean.

YCOE is licensed for private scholarly research. Only per-word tag counts may leave
this module for the LLM, never running passages.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path

from glossy2.normalize import normalize

_TOKEN = re.compile(r"(\S+)_([A-Z][A-Z$+^0-9-]*)(?=\s|$)")
_CASES = {"N": "Nom", "A": "Acc", "G": "Gen", "D": "Dat", "I": "Ins"}
_SKIP = {"CODE", "ID"}
_VERB_STEMS = {"VB": "VERB", "BE": "AUX", "HV": "AUX", "AX": "AUX", "MD": "AUX"}
_VERB_ENDINGS = {
    "": {"VerbForm": "Inf"},
    "I": {"Mood": "Imp"},
    "PH": {"Tense": "Pres"},
    "PI": {"Tense": "Pres", "Mood": "Ind"},
    "PS": {"Tense": "Pres", "Mood": "Sub"},
    "P": {"Tense": "Pres"},
    "DI": {"Tense": "Past", "Mood": "Ind"},
    "DS": {"Tense": "Past", "Mood": "Sub"},
    "D": {"Tense": "Past"},
    "N": {"VerbForm": "Part", "Tense": "Past"},
}
_PARTICIPLES = {"VAG": "VERB", "BAG": "AUX", "HAG": "AUX", "AXG": "AUX", "MDG": "AUX"}
_NOMINALS = {
    "N": ("NOUN", {}),
    "NR": ("PROPN", {}),
    "NPR": ("PROPN", {}),
    "PRO": ("PRON", {}),
    "PRO$": ("PRON", {"Poss": "Yes"}),
    "D": ("DET", {}),
    "Q": ("DET", {}),
    "QR": ("DET", {"Degree": "Cmp"}),
    "QS": ("DET", {"Degree": "Sup"}),
    "NUM": ("NUM", {}),
    "NUM$": ("NUM", {"Case": "Gen"}),
    "ADJ": ("ADJ", {}),
    "ADJR": ("ADJ", {"Degree": "Cmp"}),
    "ADJS": ("ADJ", {"Degree": "Sup"}),
    "WPRO": ("PRON", {}),
    "WPRO$": ("PRON", {"Poss": "Yes"}),
    "WQ": ("PRON", {}),
    "WD": ("DET", {}),
    "WADJ": ("ADJ", {}),
}
_UNINFLECTED = {
    "ADV": ("ADV", {}),
    "ADVR": ("ADV", {"Degree": "Cmp"}),
    "ADVS": ("ADV", {"Degree": "Sup"}),
    "WADV": ("ADV", {}),
    "P": ("ADP", {}),
    "RP": ("ADV", {}),
    "C": ("SCONJ", {}),
    "CONJ": ("CCONJ", {}),
    "NEG": ("PART", {"Polarity": "Neg"}),
    "TO": ("PART", {}),
    "INTJ": ("INTJ", {}),
    "FW": ("X", {}),
}


def ycoe_features(tag: str) -> tuple[str | None, dict[str, str]]:
    """Translate a YCOE tag into a UPOS and features. Unknown tags give ``(None, {})``."""
    base = tag.split("+")[-1]
    stem, _, suffix = base.partition("^")
    if stem in _UNINFLECTED:
        upos, feats = _UNINFLECTED[stem]
        return upos, dict(feats)
    if stem in _NOMINALS:
        upos, feats = _NOMINALS[stem]
        result = dict(feats)
        if suffix in _CASES:
            result["Case"] = _CASES[suffix]
        return upos, result
    if stem in _PARTICIPLES:
        return _PARTICIPLES[stem], {"VerbForm": "Part", "Tense": "Pres"}
    verb_stem = stem[:2]
    if verb_stem in _VERB_STEMS and stem[2:] in _VERB_ENDINGS:
        return _VERB_STEMS[verb_stem], dict(_VERB_ENDINGS[stem[2:]])
    return None, {}


class YcoeMissing(FileNotFoundError):
    pass


class YcoeIndex:
    def __init__(self, table: dict[str, Counter]):
        self._table = table

    @classmethod
    def load(cls, pos_dir: Path, exclude: set[str] = frozenset()) -> "YcoeIndex":
        table: dict[str, Counter] = defaultdict(Counter)
        paths = sorted(Path(pos_dir).glob("*.pos"))
        if not paths:
            raise YcoeMissing(f"No YCOE files found in {pos_dir}. Unzip your copy there first.")
        unmatched = set(exclude) - {path.name for path in paths}
        if unmatched:
            raise YcoeMissing(f"Can't exclude {', '.join(sorted(unmatched))}: no such YCOE file in {pos_dir}.")
        for path in paths:
            if path.name in exclude:
                continue
            for word, tag in _TOKEN.findall(path.read_text(encoding="latin-1")):
                if tag not in _SKIP:
                    table[normalize(word)][tag] += 1
        return cls(dict(table))

    def tags(self, form: str) -> Counter:
        return Counter(self._table.get(normalize(form), {}))
