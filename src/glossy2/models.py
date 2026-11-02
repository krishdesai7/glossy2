"""Shared data types."""

from dataclasses import dataclass, field


@dataclass
class Segment:
    form: str
    gloss: str


@dataclass
class Flag:
    """code: unknown_form, tag_unseen, lemma_not_in_dictionary, hint_conflict,
    segments_mismatch, ambiguous or analysis_failed."""

    code: str
    detail: str


@dataclass
class InputWord:
    form: str
    punct: str = ""
    segments: list[str] | None = None
    hint_feats: dict[str, str] = field(default_factory=dict)
    hint_upos: str | None = None
    hint_stem: str | None = None
    hint_conflicts: list[str] = field(default_factory=list)
    lead: str = ""


@dataclass
class WordAnalysis:
    form: str
    punct: str = ""
    segments: list[Segment] = field(default_factory=list)
    lemma: str | None = None
    upos: str | None = None
    feats: dict[str, str] = field(default_factory=dict)
    meaning: str | None = None
    wiktionary_url: str | None = None
    flags: list[Flag] = field(default_factory=list)
    lead: str = ""


@dataclass
class GoldToken:
    form: str
    punct: str
    segments: list[Segment]
    gloss: str


@dataclass
class GoldSentence:
    id: int
    passage: str
    tokens: list[GoldToken]
    translation: str
