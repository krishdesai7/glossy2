"""Ask the model to choose an analysis per sentence, then run the deterministic checks."""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from glossy2.checks import apply_checks, segments_rejoin
from glossy2.dictionary import Dictionary
from glossy2.llm import LLMError, complete_json
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
- A word left unsplit uses dots throughout, never hyphens. The hyphens in a gloss match the hyphens in the word.
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


def _has_letters(form: str) -> bool:
    return any(character.isalpha() for character in form)


def _format_example(sentence: GoldSentence) -> str:
    forms = " ".join(token.form + token.punct for token in sentence.tokens)
    glosses = " ".join(token.gloss for token in sentence.tokens)
    return f"{forms}\n{glosses}\n'{sentence.translation}'"


def _is_same_sentence(sentence: GoldSentence, words: list[InputWord]) -> bool:
    return [normalize(t.form) for t in sentence.tokens] == [normalize(w.form) for w in words]


def _describe_word(index: int, word: InputWord, ctx: Context) -> str:
    lines = [f"{index}. {word.form.replace('-', '')}"]
    fixed = []
    if word.segments:
        fixed.append(f"segments {', '.join(word.segments)}")
    if word.hint_upos:
        fixed.append(f"part of speech {word.hint_upos}")
    fixed.extend(f"{key}={value}" for key, value in word.hint_feats.items())
    if word.hint_stem:
        fixed.append(f"stem meaning '{word.hint_stem}'")
    if fixed:
        lines.append(f"   fixed: {'; '.join(fixed)}")
    tags = ctx.ycoe.tags(word.form).most_common(MAX_TAGS)
    if tags:
        lines.append("   YCOE tags: " + ", ".join(f"{tag} x{count}" for tag, count in tags))
    for entry in ctx.dictionary.lookup(word.form)[:MAX_ENTRIES]:
        senses = "; ".join(entry.senses[:MAX_SENSES])
        forms = " | ".join(" ".join(tags) for tags in entry.form_tags[:MAX_TAGS])
        detail = f" [{forms}]" if forms else ""
        lines.append(f"   dictionary: {entry.lemma} ({entry.pos}){detail}: {senses}")
    if ctx.memory:
        remembered = ctx.memory.human(word.form)[:MAX_REMEMBERED]
        if remembered:
            readings = ", ".join(f"{gloss} x{count} ({', '.join(sources)})" for gloss, count, sources in remembered)
            lines.append(f"   earlier human glosses, may not apply here: {readings}")
    return "\n".join(lines)


def build_messages(words: list[InputWord], ctx: Context) -> list[dict]:
    system = SYSTEM_PROMPT.format(tags=" ".join(HUMAN_TO_FEATS))
    examples = [_format_example(s) for s in ctx.examples if not _is_same_sentence(s, words)]
    example_text = "\n\n".join(examples)
    described = "\n".join(_describe_word(i, word, ctx) for i, word in enumerate(words))
    sentence = " ".join(word.form.replace("-", "") + word.punct for word in words)
    return [
        {"role": "system", "content": f"{system}\n\nWorked examples:\n\n{example_text}"},
        {"role": "user", "content": f"Sentence: {sentence}\n\nWords:\n{described}"},
    ]


def _failed(word: InputWord, reason: str) -> WordAnalysis:
    return WordAnalysis(
        word.form, word.punct, [Segment(word.form, "???")], flags=[Flag("analysis_failed", reason)]
    )


def _parse_proposal(raw: dict, word: InputWord) -> WordAnalysis:
    segments = [Segment(str(s["form"]), str(s["gloss"])) for s in raw["segments"]]
    if len(segments) == 1:
        segments[0].gloss = segments[0].gloss.replace("-", ".")
    flags = []
    if raw.get("ambiguous"):
        flags.append(Flag("ambiguous", str(raw.get("ambiguity_reason") or "the sentence doesn't settle it")))
    return WordAnalysis(
        word.form, word.punct, segments, raw.get("lemma") or None, raw.get("upos") or None,
        {str(k): str(v) for k, v in (raw.get("feats") or {}).items() if v},
        raw.get("meaning") or None, flags=flags,
    )


def _problem_with(words: list[InputWord], response: dict) -> tuple[str | None, list[WordAnalysis]]:
    raw_words = response.get("words")
    if not isinstance(raw_words, list) or len(raw_words) != len(words):
        count = len(raw_words) if isinstance(raw_words, list) else 0
        return f"Expected {len(words)} words but got {count}.", []
    proposals = []
    for word, raw in zip(words, raw_words):
        try:
            proposal = _parse_proposal(raw, word)
        except (KeyError, TypeError, AttributeError):
            return f"The entry for {word.form} was malformed.", []
        if not word.segments and not segments_rejoin(word.form, proposal.segments):
            return f"The segments for {word.form} don't rejoin to the word.", proposals
        proposals.append(proposal)
    return None, proposals


def _fix_segments(word: InputWord, proposal: WordAnalysis) -> None:
    """A human's segmentation stands, whatever the model proposed."""
    forms = [s.form for s in proposal.segments]
    if forms == word.segments:
        return
    glosses = [s.gloss for s in proposal.segments]
    count = len(word.segments)
    if len(glosses) > count:
        glosses = glosses[: count - 1] + ["-".join(glosses[count - 1 :])]
    glosses += ["?"] * (count - len(glosses))
    proposal.segments = [Segment(f, g) for f, g in zip(word.segments, glosses)]
    proposal.flags.append(Flag("hint_conflict", f"the model split this as {'-'.join(forms)}; yours was kept"))


def _analyse_words(words: list[InputWord], ctx: Context) -> list[WordAnalysis]:
    messages = build_messages(words, ctx)
    problem = None
    for _ in range(2):
        try:
            response = ctx.complete(messages)
        except LLMError as error:
            return [_failed(word, error.reason) for word in words]
        problem, proposals = _problem_with(words, response)
        if problem is None:
            return _finish(words, proposals, ctx)
        messages = [*messages, {"role": "user", "content": f"{problem} Reply again with the corrected JSON."}]
    return _salvage(words, response, problem, ctx)


def _salvage(words: list[InputWord], response: dict, problem: str, ctx: Context) -> list[WordAnalysis]:
    """After the retry: keep what's usable if only segments failed, otherwise fail honestly."""
    raw_words = response.get("words")
    if not isinstance(raw_words, list) or len(raw_words) != len(words):
        return [_failed(word, problem) for word in words]
    results = []
    for word, raw in zip(words, raw_words):
        try:
            proposal = _parse_proposal(raw, word)
        except (KeyError, TypeError, AttributeError):
            results.append(_failed(word, problem))
            continue
        if not word.segments and not segments_rejoin(word.form, proposal.segments):
            gloss = "-".join(s.gloss for s in proposal.segments)
            proposal.segments = [Segment(word.form, gloss)]
            proposal.flags.append(Flag("segments_mismatch", "the model's segments didn't rejoin to the word"))
        results.extend(_finish([word], [proposal], ctx))
    return results


def _keep_user_spelling(form: str, segments: list[Segment]) -> None:
    """Move the model's morpheme boundaries onto the word as the user typed it."""
    position = 0
    for segment in segments:
        wanted = len(normalize(segment.form))
        start = position
        while position < len(form) and len(normalize(form[start:position])) < wanted:
            position += 1
        while position < len(form) and unicodedata.combining(form[position]):
            position += 1
        segment.form = form[start:position]


def _finish(words: list[InputWord], proposals: list[WordAnalysis], ctx: Context) -> list[WordAnalysis]:
    results = []
    for word, proposal in zip(words, proposals):
        if word.segments:
            _fix_segments(word, proposal)
        elif segments_rejoin(word.form, proposal.segments):
            _keep_user_spelling(word.form, proposal.segments)
        results.append(apply_checks(word, proposal, ctx.ycoe, ctx.dictionary))
    return results


def analyze_sentence(words: list[InputWord], ctx: Context) -> list[WordAnalysis]:
    """One result per input word, in order. Punctuation-only words aren't sent to the model."""
    real = [word for word in words if _has_letters(word.form)]
    analysed = iter(_analyse_words(real, ctx) if real else [])
    return [
        next(analysed) if _has_letters(word.form) else WordAnalysis(word.form, word.punct, [Segment(word.form, word.form)])
        for word in words
    ]
