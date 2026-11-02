from pathlib import Path

import pytest

from glossy2.gold import load_corrections, load_gold, normalise_gloss, split_sentences
from glossy2.models import Segment

TEX = Path("corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex")
TINA = Path("corpus/ohthere/tina-corrections.jsonl")


@pytest.fixture(scope="module")
def gold():
    return load_gold(TEX)


def token(gold, form):
    return next(t for s in gold for t in s.tokens if t.form == form)


def test_counts(gold):
    assert len(gold) == 75
    assert sum(len(s.tokens) for s in gold) == 1716
    assert all(t.gloss and t.segments for s in gold for t in s.tokens)


def test_first_token(gold):
    t = gold[0].tokens[0]
    assert (t.form, t.gloss) == ("Ōhthere", "Ohthere.NOM")


def test_segments_align(gold):
    t = token(gold, "sǣ-d-e")
    assert [(s.form, s.gloss) for s in t.segments] == [("sǣ", "say"), ("d", "PST"), ("e", "IND.3SG")]


def test_unsegmented_keeps_whole_gloss(gold):
    t = token(gold, "cwæð")
    assert t.segments == [Segment("cwæð", "say.PST.IND.3SG")]


def test_punct_separated(gold):
    t = token(gold, "hlāford-e")
    assert t.punct == ","
    assert all("," not in x.form for s in gold for x in s.tokens)


def test_comparative_normalised(gold):
    glosses = [t.gloss for s in gold for t in s.tokens]
    assert "COMP" in glosses
    assert not any("COMP" in g and g != "COMP" for g in glosses)
    assert any("CMP" in g for g in glosses)


def test_quirks_parse(gold):
    for s in gold:
        for t in s.tokens:
            assert all(seg.form and seg.gloss for seg in t.segments)
            assert "--" not in t.gloss and "," not in t.gloss


def test_translation_keeps_text_drops_footnote(gold):
    assert all(s.translation for s in gold)
    assert not any("\\footnote" in s.translation for s in gold)
    assert gold[0].translation.startswith("Ohthere said to his lord")


def test_passages(gold):
    assert gold[50].passage == "ohthere"
    assert gold[51].passage == "wulfstan"


def test_split_fixed(gold):
    dev, test = split_sentences(gold)
    assert (len(dev), len(test)) == (15, 60)
    assert not {s.id for s in dev} & {s.id for s in test}
    assert {s.passage for s in dev} == {s.passage for s in test} == {"ohthere", "wulfstan"}
    assert [s.id for s in dev] == [s.id for s in split_sentences(gold)[0]]


def test_tina_applied():
    corrections = load_corrections(TINA)
    assert any(c.get("lemma") == "westanwind" for c in corrections.values())
    glossed = load_gold(TEX, TINA)
    for (sid, idx), fields in corrections.items():
        if "morphologicalGloss" in fields:
            assert glossed[sid].tokens[idx].gloss == normalise_gloss(str(fields["morphologicalGloss"]))
            assert "," not in glossed[sid].tokens[idx].gloss
