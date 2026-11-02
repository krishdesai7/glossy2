from glossy2.cli import coverage_stats
from glossy2.dictionary import Dictionary, build_index
from glossy2.models import GoldSentence, GoldToken, Segment
from glossy2.ycoe import YcoeIndex
from pathlib import Path


def sentence(*forms):
    tokens = [GoldToken(f, "", [Segment(f, "x")], "x") for f in forms]
    return GoldSentence(0, "main", tokens, "")


def test_coverage_stats(tmp_path):
    build_index(Path("tests/fixtures/mini-kaikki.jsonl"), tmp_path / "d.sqlite")
    stats = coverage_stats(
        [sentence("land-e", "lande", "Hē", "zzz")],
        YcoeIndex.load(Path("tests/fixtures")),
        Dictionary.open(tmp_path / "d.sqlite"),
    )
    assert stats["tokens"] == 4
    assert stats["in_ycoe"] == 3
    assert stats["in_dictionary"] == 2
    assert stats["in_neither"] == 1
    assert stats["one_lemma"] == 2
    assert stats["top_missing"] == [("zzz", 1)]
