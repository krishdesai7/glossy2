"""Comparison baselines: YCOE's most common tag per form, and CLTK's Stanza pipeline."""

from glossy2.models import GoldSentence, Segment, WordAnalysis
from glossy2.normalize import normalize
from glossy2.ycoe import YcoeIndex, ycoe_features

_pipeline = None


class BaselineUnavailable(RuntimeError):
    pass


def ycoe_majority(form: str, ycoe: YcoeIndex) -> dict[str, str]:
    tags = ycoe.tags(form)
    return ycoe_features(tags.most_common(1)[0][0])[1] if tags else {}


def ycoe_analyses(sentence: GoldSentence, ycoe: YcoeIndex) -> list[WordAnalysis]:
    return [
        WordAnalysis(t.form, t.punct, [Segment(t.form.replace("-", ""), "")], feats=ycoe_majority(t.form.replace("-", ""), ycoe))
        for t in sentence.tokens
    ]


def _cltk_words(text: str) -> list:
    global _pipeline
    try:
        if _pipeline is None:
            from cltk import NLP

            _pipeline = NLP("ang", backend="stanza", suppress_banner=True)
        return _pipeline.analyze(text).words
    except ImportError as error:
        raise BaselineUnavailable("not installed: run uv sync --extra baseline") from error


def cltk_analyses(sentence: GoldSentence) -> list[WordAnalysis]:
    text = " ".join(t.form.replace("-", "") + t.punct for t in sentence.tokens)
    remaining = list(_cltk_words(text))
    results = []
    for token in sentence.tokens:
        wanted = normalize(token.form)
        match = next((w for w in remaining if normalize(w.string) == wanted), None)
        analysis = WordAnalysis(token.form, token.punct, [Segment(token.form.replace("-", ""), "")])
        if match is not None:
            remaining = remaining[remaining.index(match) + 1 :]
            analysis.lemma = (match.lemma or "").split(" ")[0] or None
            analysis.upos = match.upos.tag if match.upos else None
            tags = match.features.features if match.features else []
            analysis.feats = {tag.key: tag.value for tag in tags}
        results.append(analysis)
    return results
