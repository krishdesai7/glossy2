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


def _apply_stem(segments: list[Segment], stem: str) -> None:
    """Put the given stem on the segments that carry lexical meaning, keeping any tags."""
    lexical = [s for s in segments if any(p not in HUMAN_TO_FEATS for p in s.gloss.split("."))]
    if not lexical:
        return
    parts = stem.split("-")
    if len(parts) != len(lexical):
        parts = [stem]
        lexical = lexical[:1]
    for segment, part in zip(lexical, parts):
        tags = [piece for piece in segment.gloss.split(".") if piece in HUMAN_TO_FEATS]
        segment.gloss = ".".join([part, *tags])


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
    result.form, result.punct = word.form, word.punct
    _apply_hints(word, result)
    tags = ycoe.tags(word.form)
    entries = dictionary.lookup(word.form)
    if not tags and not entries:
        result.flags.append(Flag("unknown_form", f"{word.form} isn't in YCOE or the dictionary"))
        result.wiktionary_url = None
        if result.lemma and not dictionary.has_lemma(result.lemma):
            return result
    elif tags and not _seen_in_ycoe(result, tags):
        seen = ", ".join(tag for tag, _ in tags.most_common(4))
        result.flags.append(Flag("tag_unseen", f"YCOE only has this form as {seen}"))
    _attach_link(result, dictionary)
    return result
