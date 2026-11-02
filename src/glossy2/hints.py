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
_PUNCT = re.compile(r"[.,;:!?\"'’”)·]+$")
_LEAD = re.compile(r"^[\"'“‘(·]+")
# English words that are both grammar labels and likely stem meanings. Never guess.
_AMBIGUOUS = {
    "strong": "str", "weak": "wk", "first": "1", "second": "2", "third": "3",
    "present": "prs", "past": "pst", "name": "propn", "proper": "propn",
}


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
        if label.startswith("="):
            if not label[1:].strip():
                raise HintError(word.form, "= needs a meaning after it")
            stems.append(label[1:].strip())
        elif lowered in _AMBIGUOUS:
            raise HintError(
                word.form,
                f"'{label}' could be grammar or a meaning. Write {_AMBIGUOUS[lowered]} for the grammar "
                f"label, or ={label} for the meaning",
            )
        elif lowered in _NOUNLIKE:
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


def _parse_token(raw: str) -> InputWord:
    shape = _SHAPE.match(raw)
    text, after = shape["word"], shape["after"]
    has_hint = shape["hint"] is not None
    if not text and has_hint:
        raise HintError(raw, "a hint goes straight after its word, with no space, and one bracket per word")
    lead_match = _LEAD.match(text)
    lead = lead_match[0] if lead_match else ""
    form = text[len(lead) :]
    found = _PUNCT.search(form)
    punct = found[0] if found else ""
    if punct:
        form = form[: -len(punct)]
    if not form:
        if has_hint:
            raise HintError(raw, "a hint goes straight after its word")
        return InputWord(raw)
    if after and not _PUNCT.fullmatch(after):
        raise HintError(form, f"unexpected text after the hint: {after}")
    word = InputWord(form, punct=punct + after, lead=lead)
    if "-" in form:
        word.segments = [part for part in form.split("-") if part]
    if has_hint:
        if not shape["close"]:
            raise HintError(form, "the hint has no closing bracket")
        _apply_hint(word, shape["hint"])
    return word


def parse_line(line: str) -> list[InputWord]:
    return [_parse_token(raw) for raw in filter(None, (m[0] for m in _TOKEN.finditer(line)))]
