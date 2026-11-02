"""Deterministic checks on a proposed analysis: hints win, links come only from the
dictionary, and flags record evidence rather than the model's confidence."""

from copy import deepcopy

from glossy2.dictionary import Dictionary
from glossy2.models import Flag, InputWord, Segment, WordAnalysis
from glossy2.normalize import normalize
from glossy2.tags import HUMAN_TO_FEATS
from glossy2.ycoe import YcoeIndex, ycoe_features

_SAME_FAMILY = [
    {"NOUN", "PROPN"},
    {"VERB", "AUX"},
    {"DET", "PRON", "ADJ", "NUM"},
    {"ADV", "ADP", "PART"},
    {"SCONJ", "CCONJ"},
]
_TABLE_TAGS = {
    "nominative": ("Case", "Nom"), "accusative": ("Case", "Acc"), "genitive": ("Case", "Gen"),
    "dative": ("Case", "Dat"), "instrumental": ("Case", "Ins"),
    "singular": ("Number", "Sing"), "plural": ("Number", "Plur"),
    "first-person": ("Person", "1"), "second-person": ("Person", "2"), "third-person": ("Person", "3"),
    "present": ("Tense", "Pres"), "past": ("Tense", "Past"),
    "indicative": ("Mood", "Ind"), "subjunctive": ("Mood", "Sub"), "imperative": ("Mood", "Imp"),
}
_TABLE_FEATURES = {"Case", "Number", "Person", "Tense", "Mood"}
_TAG_FOR_FEATS = {frozenset(feats.items()): tag for tag, feats in HUMAN_TO_FEATS.items()}


def segments_rejoin(form: str, segments: list[Segment]) -> bool:
    return normalize("".join(s.form for s in segments)) == normalize(form)


def _same_family(a: str, b: str) -> bool:
    return a == b or any(a in family and b in family for family in _SAME_FAMILY)


def _seen_in_ycoe(analysis: WordAnalysis, tags) -> bool:
    known = [ycoe_features(tag) for tag in tags]
    known = [(upos, feats) for upos, feats in known if upos]
    if not known:
        return True
    for upos, feats in known:
        if analysis.upos and not _same_family(analysis.upos, upos):
            continue
        if all(analysis.feats.get(key, value) == value for key, value in feats.items()):
            return True
    return False


def _rewrite_tag(piece: str, key: str, value: str) -> str:
    feats = HUMAN_TO_FEATS.get(piece)
    if not feats or key not in feats:
        return piece
    return _TAG_FOR_FEATS.get(frozenset({**feats, key: value}.items()), piece)


def _apply_feature_to_gloss(segments: list[Segment], key: str, value: str) -> None:
    for segment in segments:
        segment.gloss = "-".join(
            ".".join(_rewrite_tag(piece, key, value) for piece in part.split("."))
            for part in segment.gloss.split("-")
        )


def _is_tag_only(part: str) -> bool:
    return all(piece in HUMAN_TO_FEATS for piece in part.split("."))


def _apply_stem(segments: list[Segment], stem: str) -> None:
    """Put the given stem where the model had English meaning, keeping every tag."""
    slots = [
        (segment, index)
        for segment in segments
        for index, part in enumerate(segment.gloss.split("-"))
        if not _is_tag_only(part)
    ]
    if not slots:
        return
    stems = stem.split("-")
    if len(stems) != len(slots):
        stems = [stem] + [""] * (len(slots) - 1)
    replacements: dict[int, dict[int, str]] = {}
    for (segment, index), new in zip(slots, stems):
        replacements.setdefault(id(segment), {})[index] = new
    for segment in segments:
        changes = replacements.get(id(segment), {})
        parts = []
        for index, part in enumerate(segment.gloss.split("-")):
            if index not in changes:
                parts.append(part)
                continue
            tags = [piece for piece in part.split(".") if piece in HUMAN_TO_FEATS]
            if changes[index]:
                parts.append(".".join([changes[index], *tags]))
            elif tags:
                parts.append(".".join(tags))
        segment.gloss = "-".join(parts)


def _apply_hints(word: InputWord, result: WordAnalysis) -> None:
    for conflict in word.hint_conflicts:
        result.flags.append(Flag("hint_conflict", f"contradictory hints: {conflict}"))
    if word.hint_upos and result.upos != word.hint_upos:
        if result.upos:
            result.flags.append(
                Flag("hint_conflict", f"you said {word.hint_upos}; the model preferred {result.upos}")
            )
        result.upos = word.hint_upos
    for key, value in word.hint_feats.items():
        preferred = result.feats.get(key)
        if preferred and preferred != value:
            result.flags.append(
                Flag("hint_conflict", f"you said {key}={value}; the model preferred {key}={preferred}")
            )
        result.feats[key] = value
        _apply_feature_to_gloss(result.segments, key, value)
    if word.hint_stem:
        _apply_stem(result.segments, word.hint_stem)
        result.meaning = word.hint_stem


def _check_hints_against_paradigm(word: InputWord, entries: list, result: WordAnalysis) -> None:
    """Flag a hint when the dictionary's inflection table has no such reading of this form."""
    readings = [
        {_TABLE_TAGS[tag][0]: _TABLE_TAGS[tag][1] for tag in tags if tag in _TABLE_TAGS}
        for entry in entries
        for tags in entry.form_tags
    ]
    readings = [reading for reading in readings if reading]
    hinted = {key: value for key, value in word.hint_feats.items() if key in _TABLE_FEATURES}
    if not readings or not hinted:
        return
    for key, value in hinted.items():
        if not any(reading.get(key, value) == value for reading in readings):
            result.flags.append(
                Flag("hint_conflict", f"the dictionary's table has no {key}={value} for {word.form}; your hint was kept")
            )


def _attach_link(result: WordAnalysis, dictionary: Dictionary) -> None:
    result.wiktionary_url = None
    if not result.lemma:
        return
    if not dictionary.has_lemma(result.lemma):
        result.flags.append(Flag("lemma_not_in_dictionary", f"no dictionary entry for {result.lemma}"))
        return
    wanted = normalize(result.lemma)
    for entry in dictionary.lookup(result.lemma):
        if normalize(entry.lemma) == wanted:
            result.wiktionary_url = entry.url
            return


def apply_checks(
    word: InputWord, proposed: WordAnalysis, ycoe: YcoeIndex, dictionary: Dictionary
) -> WordAnalysis:
    result = deepcopy(proposed)
    result.form, result.punct, result.lead = word.form, word.punct, word.lead
    _apply_hints(word, result)
    tags = ycoe.tags(word.form)
    entries = dictionary.lookup(word.form)
    if not tags and not entries:
        result.flags.append(Flag("unknown_form", f"{word.form} isn't in YCOE or the dictionary"))
        result.wiktionary_url = None
        return result
    if tags and not _seen_in_ycoe(result, tags):
        seen = ", ".join(tag for tag, _ in tags.most_common(4))
        result.flags.append(Flag("tag_unseen", f"YCOE only has this form as {seen}"))
    _check_hints_against_paradigm(word, entries, result)
    _attach_link(result, dictionary)
    return result
