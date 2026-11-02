"""Parse input lines: words with optional bracketed hints.

``lande[noun,neuter]`` gives features, ``hlāford-e[lord]`` gives a stem meaning, and a
hyphen in a word fixes its segmentation.
"""

import re

from glossy2.models import InputWord

_NOUNLIKE = {
    "noun": "NOUN", "propn": "PROPN", "proper": "PROPN", "name": "PROPN", "verb": "VERB",
    "aux": "AUX", "adj": "ADJ", "adjective": "ADJ", "adv": "ADV", "adverb": "ADV",
    "pron": "PRON", "pronoun": "PRON", "det": "DET", "determiner": "DET", "num": "NUM",
    "numeral": "NUM", "prep": "ADP", "preposition": "ADP", "conj": "CCONJ",
    "conjunction": "CCONJ", "interjection": "INTJ",
}
_FEATURES = {
    ("Gender", "Masc"): "m masc masculine", ("Gender", "Fem"): "f fem feminine",
    ("Gender", "Neut"): "n neut neuter",
    ("Number", "Sing"): "sg sing singular", ("Number", "Plur"): "pl plur plural",
    ("Case", "Nom"): "nom nominative", ("Case", "Acc"): "acc accusative",
    ("Case", "Gen"): "gen genitive", ("Case", "Dat"): "dat dative",
    ("Case", "Ins"): "ins instrumental",
    ("Tense", "Pres"): "prs pres present", ("Tense", "Past"): "pst past preterite",
    ("Mood", "Ind"): "ind indicative", ("Mood", "Sub"): "sjv subj subjunctive",
    ("Mood", "Imp"): "imp imperative", ("VerbForm", "Inf"): "inf infinitive",
    ("VerbForm", "Part"): "part participle", ("Person", "1"): "1 1st first",
    ("Person", "2"): "2 2nd second", ("Person", "3"): "3 3rd third",
    ("Declension", "Str"): "str strong", ("Declension", "Wk"): "wk weak",
    ("Degree", "Cmp"): "cmp comparative", ("Degree", "Sup"): "sup superlative",
}
HINT_LABELS: dict[str, tuple[str, str]] = {
    label: pair for pair, labels in _FEATURES.items() for label in labels.split()
}
_TOKEN = re.compile(r"[^\s\[]*(?:\[[^\]]*\]?)?[^\s\[]*")
_SHAPE = re.compile(r"^(?P<word>[^\[\]]*)(?:\[(?P<hint>[^\]]*)(?P<close>\]?))?(?P<after>.*)$")
_PUNCT = re.compile(r"[.,;:!?\"'’”)]+$")


class HintError(ValueError):
    def __init__(self, word: str, reason: str):
        super().__init__(f"{word}: {reason}")
        self.word = word
        self.reason = reason


def _apply_hint(word: InputWord, hint: str) -> None:
    labels = [label.strip() for label in hint.split(",")]
    if not any(labels):
        raise HintError(word.form, "empty hint")
    stems = []
    for label in labels:
        lowered = label.lower()
        if lowered in _NOUNLIKE:
            upos = _NOUNLIKE[lowered]
            if word.hint_upos and word.hint_upos != upos:
                word.hint_conflicts.append(f"part of speech: {word.hint_upos} or {upos}")
            word.hint_upos = upos
        elif lowered in HINT_LABELS:
            key, value = HINT_LABELS[lowered]
            if key in word.hint_feats and word.hint_feats[key] != value:
                word.hint_conflicts.append(f"{key}: {word.hint_feats[key]} or {value}")
            word.hint_feats[key] = value
        elif label:
            stems.append(label)
    if len(stems) > 1:
        raise HintError(word.form, f"only one stem meaning is allowed, got {', '.join(stems)}")
    word.hint_stem = stems[0] if stems else None


def parse_line(line: str) -> list[InputWord]:
    words = []
    for raw in filter(None, (m[0] for m in _TOKEN.finditer(line))):
        shape = _SHAPE.match(raw)
        form, after = shape["word"], shape["after"]
        found = _PUNCT.search(form)
        punct = found[0] if found else ""
        if punct:
            form = form[: -len(punct)]
        word = InputWord(form, punct=punct + after)
        if "-" in form:
            word.segments = [part for part in form.split("-") if part]
        if shape["hint"] is not None:
            if not shape["close"]:
                raise HintError(form, "the hint has no closing bracket")
            _apply_hint(word, shape["hint"])
        words.append(word)
    return words
