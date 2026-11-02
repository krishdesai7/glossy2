"""Hide parts of human glosses, then score what comes back. Only what was withheld counts."""

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field

from glossy2.dictionary import Dictionary
from glossy2.models import GoldSentence, InputWord, WordAnalysis
from glossy2.normalize import normalize
from glossy2.tags import parse_gloss, render_gloss

LEVELS = ["none", "half", "stem", "stem+half"]
_TINA_FEATURES = {
    "case": ("Case", {"nominative": "Nom", "accusative": "Acc", "genitive": "Gen", "dative": "Dat", "instrumental": "Ins"}),
    "number": ("Number", {"singular": "Sing", "plural": "Plur", "dual": "Dual"}),
    "gender": ("Gender", {"masculine": "Masc", "feminine": "Fem", "neuter": "Neut"}),
    "person": ("Person", {"1": "1", "2": "2", "3": "3"}),
    "tense": ("Tense", {"present": "Pres", "past": "Past"}),
    "mood": ("Mood", {"indicative": "Ind", "subjunctive": "Sub", "imperative": "Imp"}),
    "degree": ("Degree", {"comparative": "Cmp", "superlative": "Sup"}),
    "declension": ("Declension", {"strong": "Str", "weak": "Wk"}),
    "voice": ("Voice", {"passive": "Pass"}),
}
Tally = tuple[int, int]


@dataclass
class Withheld:
    stem: bool
    feats: set[str]


@dataclass
class TokenScore:
    sentence: int
    token: int
    form: str
    gold_gloss: str
    predicted_gloss: str
    exact: bool | None
    segmentation: bool
    feats: dict[str, bool]
    meaning_exact: bool | None
    meaning_sense: bool | None
    lemma: bool | None
    flagged: bool
    failed: bool
    flag_codes: list[str] = field(default_factory=list)


@dataclass
class Scores:
    tokens: int
    failed: int
    exact: Tally
    segmentation: Tally
    meaning_exact: Tally
    meaning_sense: Tally
    lemma: Tally
    flagged: Tally
    unflagged: Tally
    features: dict[str, Tally]


def make_inputs(sentence: GoldSentence, level: str, seed: int = 1729) -> tuple[list[InputWord], list[Withheld]]:
    """The sentence as a user would type it, with the hints this level gives."""
    words, withheld = [], []
    for index, token in enumerate(sentence.tokens):
        stem, feats = parse_gloss(token.gloss)
        word = InputWord(token.form.replace("-", ""), token.punct)
        hidden = set(feats)
        if level in ("half", "stem+half"):
            rng = random.Random(f"{seed}:{sentence.id}:{index}")
            for key in sorted(feats):
                if rng.random() < 0.5:
                    word.hint_feats[key] = feats[key]
                    hidden.discard(key)
        if level in ("stem", "stem+half") and stem:
            word.hint_stem = stem
        words.append(word)
        withheld.append(Withheld(bool(stem) and not word.hint_stem, hidden))
    return words, withheld


def _tina_feats(fields: dict[str, object]) -> dict[str, str]:
    feats = {}
    for name, value in fields.items():
        if name.startswith("features.") and name[9:] in _TINA_FEATURES:
            key, values = _TINA_FEATURES[name[9:]]
            if (mapped := values.get(str(value).lower())) is not None:
                feats[key] = mapped
    return feats


def _words(text: str) -> set[str]:
    return {word for word in re.split(r"[^a-z]+", text.lower()) if word}


def _sense_match(form: str, gold_stem: str, predicted_stem: str, dictionary: Dictionary) -> bool:
    gold_words, predicted_words = _words(gold_stem), _words(predicted_stem)
    if gold_words == predicted_words:
        return True
    if not gold_words or not predicted_words:
        return False
    for entry in dictionary.lookup(form):
        for sense in entry.senses:
            words = _words(sense)
            if gold_words <= words and predicted_words <= words:
                return True
    return False


def _score_token(sid, index, token, analysis, hidden, fields, dictionary) -> TokenScore:
    failed = any(flag.code == "analysis_failed" for flag in analysis.flags)
    gold_stem, gold_feats = parse_gloss(token.gloss)
    predicted_gloss = render_gloss(analysis)
    predicted_stem, gloss_feats = parse_gloss(predicted_gloss)
    predicted_feats = {**gloss_feats, **analysis.feats}
    hinted = set(gold_feats) - hidden.feats
    tina = _tina_feats(fields)
    wanted = {key: gold_feats[key] for key in hidden.feats if key in gold_feats}
    wanted.update({key: value for key, value in tina.items() if key not in hinted})
    feats = {key: not failed and predicted_feats.get(key) == value for key, value in wanted.items()}
    something_hidden = hidden.stem or bool(hidden.feats) or bool(wanted)
    exact = (not failed and predicted_gloss.rstrip("?") == token.gloss) if something_hidden else None
    gold_parts = [normalize(part) for part in token.form.split("-") if part]
    predicted_parts = [normalize(segment.form) for segment in analysis.segments]
    meaning_exact = meaning_sense = None
    if hidden.stem:
        meaning_exact = not failed and predicted_stem.casefold() == gold_stem.casefold()
        meaning_sense = not failed and _sense_match(token.form.replace("-", ""), gold_stem, predicted_stem, dictionary)
    lemma = None
    if "lemma" in fields:
        lemma = not failed and bool(analysis.lemma) and normalize(analysis.lemma) == normalize(str(fields["lemma"]))
    return TokenScore(
        sid, index, token.form, token.gloss, predicted_gloss, exact,
        not failed and predicted_parts == gold_parts, feats, meaning_exact, meaning_sense, lemma,
        bool(analysis.flags), failed, [flag.code for flag in analysis.flags],
    )


def score_sentence(
    gold: GoldSentence,
    analyses: list[WordAnalysis],
    withheld: list[Withheld],
    corrections: dict[tuple[int, int], dict[str, object]],
    dictionary: Dictionary,
) -> list[TokenScore]:
    results = []
    for index, (token, analysis, hidden) in enumerate(zip(gold.tokens, analyses, withheld)):
        if any(character.isalpha() for character in token.form):
            fields = corrections.get((gold.id, index), {})
            results.append(_score_token(gold.id, index, token, analysis, hidden, fields, dictionary))
    return results


def _tally(values) -> Tally:
    known = [value for value in values if value is not None]
    return sum(known), len(known)


def aggregate(scores: list[TokenScore]) -> Scores:
    features: dict[str, list[bool]] = defaultdict(list)
    for score in scores:
        for key, right in score.feats.items():
            features[key].append(right)
    return Scores(
        tokens=len(scores),
        failed=sum(score.failed for score in scores),
        exact=_tally(s.exact for s in scores),
        segmentation=_tally(s.segmentation for s in scores),
        meaning_exact=_tally(s.meaning_exact for s in scores),
        meaning_sense=_tally(s.meaning_sense for s in scores),
        lemma=_tally(s.lemma for s in scores),
        flagged=_tally(s.exact for s in scores if s.flagged),
        unflagged=_tally(s.exact for s in scores if not s.flagged),
        features={key: _tally(values) for key, values in sorted(features.items())},
    )
