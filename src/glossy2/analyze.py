"""Ask the model to choose an analysis per sentence, then run the deterministic checks."""

from typing import Any
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from glossy2.checks import apply_checks, segments_rejoin
from glossy2.dictionary import Dictionary
from glossy2.llm import LLMError, complete_json, forget_cached
from glossy2.memory import Memory
from glossy2.models import Flag, GoldSentence, InputWord, Segment, WordAnalysis
from glossy2.normalize import normalize
from glossy2.tags import HUMAN_TO_FEATS
from glossy2.ycoe import YcoeIndex

MAX_SENSES = 3
MAX_TAGS = 5
MAX_ENTRIES = 4
MAX_REMEMBERED = 5

SYSTEM_PROMPT = """You are an expert in Old English philology, producing Leipzig-style interlinear glosses.

For each numbered word, split it into morphemes and gloss each one, following the conventions in the worked examples exactly:
- Segments must rejoin to exactly the word as given.
- Gloss a stem with an English word, and an ending with capitalised tags joined by dots, such as STEM-PST-IND.3SG or STEM-DAT.SG.
- A word that isn't split keeps its whole gloss on one segment, such as STEM.PST.IND.3SG.
- Gloss literally and transparently, morpheme by morpheme: a compound or derived word gets one gloss per part, in plain words, rather than one modern English word that covers the whole.
- Use THM for a thematic vowel in a verb, NMLZ for a nominalising ending, AGT for an agent ending, PFX for the prefix ge-, HAB for the b- forms of "be", and PART for a participle. Number words keep their parts, such as six-ty.
- Tell a definite article (DET.DEF...) from a true demonstrative (DEM.DIST... or DEM.PROX...) and from the complementizer (COMP) by the sentence. The impersonal "man" is one.INDF. The preposition "on" with a place is usually "in".
- Add ADV only to an adverb formed from an adjective; a plain adverb or preposition has no tag. Add STR or WK to adjective and quantifier endings, not to nouns.
- Give one segment entry per morpheme, so a word glossed X-PST-IND.3SG has three entries, such as {{"form": "sǣ", "gloss": "X"}}, {{"form": "d", "gloss": "PST"}}, {{"form": "e", "gloss": "IND.3SG"}}. Most inflected words split like this. Only a word with no separable ending, such as a strong past form, stays whole with dots: X.PST.IND.3SG.
- A fixed stem meaning still needs its grammatical tags around it. Only the English word is given.
- Mark only the features the examples would normally mark. Report your full analysis in "feats", using these exact names and values where they apply: Case=Nom|Acc|Gen|Dat|Ins, Number=Sing|Plur, Gender=Masc|Fem|Neut, Person=1|2|3, Tense=Pres|Past, Mood=Ind|Sub|Imp, VerbForm=Inf|Part, Voice=Pass, Degree=Cmp|Sup, Definite=Def|Ind, PronType=Det|Dem|Rel, Polarity=Neg, Declension=Str|Wk, Aspect=Hab, Thematic=Yes, Derivation=Agt|Nmlz, Prefix=Yes, PartType=Comp, Deixis=Dist|Prox, Form=Adv|Adj.

Tags allowed in glosses: {tags}

Each word lists evidence where available: tags YCOE has recorded for that spelling (with counts), and dictionary entries. Use it, but read the sentence: the most frequent reading is not always the right one, and a word may have no evidence at all. Some words also list how humans glossed that spelling before. The same spelling can be a different word or form elsewhere, so treat those only as possible readings.

Anything listed as "fixed" came from a human and must not be changed. Build your analysis around it.

Do not force a guess. Many endings are truly ambiguous, such as past indicative against past subjunctive, or dative against instrumental. If the sentence doesn't settle a reading, set "ambiguous" to true and say why in "ambiguity_reason". If you don't know the lemma, set it to null rather than inventing one.

Reply with one JSON object only:
{{"words": [{{"index": 0, "segments": [{{"form": "", "gloss": ""}}], "lemma": "", "upos": "", "feats": {{}}, "meaning": "", "ambiguous": false, "ambiguity_reason": ""}}]}}
Include every numbered word, in order, with its index."""


@dataclass
class Context:
    ycoe: YcoeIndex
    dictionary: Dictionary
    examples: list[GoldSentence] = field(default_factory=list)
    complete: Callable[[list[dict]], dict] = complete_json
    memory: Memory | None = None
    forget: Callable[[list[dict]], None] = forget_cached


def _has_letters(form: str) -> bool:
    return any(character.isalpha() for character in form)


def _format_example(sentence: GoldSentence) -> str:
    forms: str = " ".join(token.form + token.punct for token in sentence.tokens)
    glosses: str = " ".join(token.gloss for token in sentence.tokens)
    return f"{forms}\n{glosses}\n'{sentence.translation}'"


def _is_same_sentence(sentence: GoldSentence, words: list[InputWord]) -> bool:
    return [normalize(t.form) for t in sentence.tokens] == [
        normalize(w.form) for w in words
    ]


def _describe_word(index: int, word: InputWord, ctx: Context) -> str:
    lines: list[str] = [f"{index}. {word.form.replace('-', '')}"]
    fixed: list[str] = []
    if word.segments:
        fixed.append(f"segments {', '.join(word.segments)}")
    if word.hint_upos:
        fixed.append(f"part of speech {word.hint_upos}")
    fixed.extend(f"{key}={value}" for key, value in word.hint_feats.items())
    if word.hint_stem:
        fixed.append(f"stem meaning '{word.hint_stem}'")
    if fixed:
        lines.append(f"   fixed: {'; '.join(fixed)}")
    tags: list[tuple[Any, int]] = ctx.ycoe.tags(word.form).most_common(MAX_TAGS)
    if tags:
        lines.append(
            "   YCOE tags: " + ", ".join(f"{tag} x{count}" for tag, count in tags)
        )
    for entry in ctx.dictionary.lookup(word.form)[:MAX_ENTRIES]:
        senses: str = "; ".join(entry.senses[:MAX_SENSES])
        forms: str = " | ".join(" ".join(tags) for tags in entry.form_tags[:MAX_TAGS])
        detail: str = f" [{forms}]" if forms else ""
        lines.append(f"   dictionary: {entry.lemma} ({entry.pos}){detail}: {senses}")
    if ctx.memory:
        remembered: list[tuple[str, int, list[str]]] = ctx.memory.human(word.form)[
            :MAX_REMEMBERED
        ]
        if remembered:
            readings: str = ", ".join(
                f"{gloss} x{count} ({', '.join(sources)})"
                for gloss, count, sources in remembered
            )
            lines.append(f"   earlier human glosses, may not apply here: {readings}")
    return "\n".join(lines)


def build_messages(words: list[InputWord], ctx: Context) -> list[dict]:
    system: str = SYSTEM_PROMPT.format(tags=" ".join(HUMAN_TO_FEATS))
    examples: list[str] = [
        _format_example(sentence=s)
        for s in ctx.examples
        if not _is_same_sentence(s, words)
    ]
    example_text = "\n\n".join(examples)
    described: str = "\n".join(
        _describe_word(i, word, ctx) for i, word in enumerate(iterable=words)
    )
    sentence: str = " ".join(
        word.lead + word.form.replace("-", "") + word.punct for word in words
    )
    return [
        {
            "role": "system",
            "content": f"{system}\n\nWorked examples:\n\n{example_text}",
        },
        {"role": "user", "content": f"Sentence: {sentence}\n\nWords:\n{described}"},
    ]


def _failed(word: InputWord, reason: str) -> WordAnalysis:
    return WordAnalysis(
        word.form,
        word.punct,
        segments=[Segment(word.form, gloss="???")],
        flags=[Flag(code="analysis_failed", detail=reason)],
        lead=word.lead,
    )


def _parse_proposal(raw: dict, word: InputWord) -> WordAnalysis:
    if not isinstance(raw["segments"], list):
        raise TypeError("segments must be a list")
    for name in ("lemma", "upos", "meaning"):
        if raw.get(name) is not None and not isinstance(raw[name], str):
            raise TypeError(f"{name} must be text")
    if not isinstance(raw.get("feats") or {}, dict):
        raise TypeError("feats must be an object")
    segments: list[Segment] = [
        Segment(form=str(object=s["form"]), gloss=str(object=s["gloss"]))
        for s in raw["segments"]
    ]
    flags: list[Flag] = []
    if raw.get("ambiguous"):
        flags.append(
            Flag(
                code="ambiguous",
                detail=str(
                    object=raw.get("ambiguity_reason")
                    or "the sentence doesn't settle it"
                ),
            )
        )
    return WordAnalysis(
        word.form,
        word.punct,
        segments,
        lemma=raw.get("lemma") or None,
        upos=raw.get("upos") or None,
        feats={
            str(object=k): str(object=v)
            for k, v in (raw.get("feats") or {}).items()
            if v
        },
        meaning=raw.get("meaning") or None,
        flags=flags,
    )


def _problem_with(
    words: list[InputWord], response: dict
) -> tuple[str | None, list[WordAnalysis]]:
    raw_words: Any | None = response.get("words")
    if not isinstance(raw_words, list) or len(raw_words) != len(words):
        count = len(raw_words) if isinstance(raw_words, list) else 0
        return f"Expected {len(words)} words but got {count}.", []
    proposals: list[WordAnalysis] = []
    for word, raw in zip(words, raw_words):
        try:
            proposal: WordAnalysis = _parse_proposal(raw, word)
        except KeyError, TypeError, AttributeError:
            return f"The entry for {word.form} was malformed.", []
        if not word.segments and not segments_rejoin(word.form, proposal.segments):
            return f"The segments for {word.form} don't rejoin to the word.", proposals
        proposals.append(proposal)
    return None, proposals


def _fix_segments(word: InputWord, proposal: WordAnalysis) -> None:
    """A human's segmentation stands, whatever the model proposed."""
    forms: list[str] = [s.form for s in proposal.segments]
    if [normalize(form=f) for f in forms] == [normalize(f) for f in word.segments]:
        for segment, form in zip(proposal.segments, word.segments):
            segment.form = form
        return
    glosses: list[str] = [s.gloss for s in proposal.segments]
    count: int = len(word.segments)
    if len(glosses) > count:
        glosses: list[str] = glosses[: count - 1] + ["-".join(glosses[count - 1 :])]
    glosses += ["?"] * (count - len(glosses))
    proposal.segments = [
        Segment(form=f, gloss=g) for f, g in zip(word.segments, glosses)
    ]
    proposal.flags.append(
        Flag(
            code="hint_conflict",
            detail=f"the model split this as {'-'.join(forms)}; yours was kept",
        )
    )


def _analyse_words(words: list[InputWord], ctx: Context) -> list[WordAnalysis]:
    messages = build_messages(words, ctx)
    problem = None
    sent: list[list[dict[str, str]]] = []
    for _ in range(2):
        sent.append(messages)
        try:
            response: dict[Any, Any] = ctx.complete(messages)
        except LLMError as error:
            return [_failed(word, error.reason) for word in words]
        problem, proposals = _problem_with(words, response)
        if problem is None:
            return _finish(words, proposals, ctx)
        messages: list[dict[str, str] | dict[Any, Any]] = [
            *messages,
            {
                "role": "user",
                "content": f"{problem} Reply again with the corrected JSON.",
            },
        ]
    results: list[WordAnalysis] = _salvage(words, response, problem, ctx)
    if any(
        flag.code == "analysis_failed" for result in results for flag in result.flags
    ):
        # Don't let a bad response answer this sentence forever: both attempts go.
        for attempt in sent:
            ctx.forget(attempt)
    return results


def _salvage(
    words: list[InputWord], response: dict, problem: str, ctx: Context
) -> list[WordAnalysis]:
    """After the retry: keep what's usable if only segments failed, otherwise fail honestly."""
    raw_words: Any | None = response.get("words")
    if not isinstance(raw_words, list) or len(raw_words) != len(words):
        return [_failed(word, problem) for word in words]
    results: list[WordAnalysis] = []
    for word, raw in zip(words, raw_words):
        try:
            proposal: WordAnalysis = _parse_proposal(raw, word)
        except KeyError, TypeError, AttributeError:
            results.append(_failed(word, reason=problem))
            continue
        if not word.segments and not segments_rejoin(word.form, proposal.segments):
            gloss: str = "-".join(s.gloss for s in proposal.segments)
            proposal.segments = [Segment(word.form, gloss)]
            proposal.flags.append(
                Flag(
                    "segments_mismatch",
                    "the model's segments didn't rejoin to the word",
                )
            )
        results.extend(_finish([word], [proposal], ctx))
    return results


def _keep_user_spelling(form: str, segments: list[Segment]) -> None:
    """Move the model's morpheme boundaries onto the word as the user typed it."""
    position = 0
    for segment in segments:
        wanted: int = len(normalize(segment.form))
        start: int = position
        while position < len(form) and len(normalize(form[start:position])) < wanted:
            position += 1
        while position < len(form) and unicodedata.combining(form[position]):
            position += 1
        segment.form = form[start:position]


def _finish(
    words: list[InputWord], proposals: list[WordAnalysis], ctx: Context
) -> list[WordAnalysis]:
    results: list[WordAnalysis] = []
    for word, proposal in zip(words, proposals):
        if word.segments:
            _fix_segments(word, proposal)
        elif segments_rejoin(word.form, proposal.segments):
            _keep_user_spelling(word.form, proposal.segments)
        results.append(apply_checks(word, proposal, ctx.ycoe, ctx.dictionary))
    return results


def _unanalysed(word: InputWord) -> WordAnalysis:
    """Punctuation passes through. Anything else without letters, like ⁊ or 7, gets a flag."""
    flags: list[Flag] = []
    if "⁊" in word.form or any(
        unicodedata.category(character)[0] not in "PZ" for character in word.form
    ):
        flags.append(
            Flag(
                code="unknown_form",
                detail=f"{word.form} wasn't analysed: it has no letters",
            )
        )
    return WordAnalysis(
        word.form,
        word.punct,
        segments=[Segment(word.form, gloss=word.form)],
        flags=flags,
        lead=word.lead,
    )


def analyze_sentence(words: list[InputWord], ctx: Context) -> list[WordAnalysis]:
    """One result per input word, in order. Punctuation-only words aren't sent to the model."""
    real = [word for word in words if _has_letters(word.form)]
    analysed = iter(_analyse_words(real, ctx) if real else [])
    return [
        next(analysed) if _has_letters(word.form) else _unanalysed(word)
        for word in words
    ]
