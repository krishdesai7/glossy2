from glossy2.baselines import BaselineUnavailable, cltk_analyses, ycoe_majority, ycoe_analyses
from glossy2.models import GoldSentence, GoldToken, Segment
from tests.fakes import FakeYcoe

YCOE = FakeYcoe({"lande": {"N^D": 5, "N^A": 1}})


def test_majority():
    assert ycoe_majority("lande", YCOE) == {"Case": "Dat"}


def test_majority_unknown_form():
    assert ycoe_majority("zzz", YCOE) == {}


def sentence():
    return GoldSentence(0, "main", [GoldToken("land-e", ",", [Segment("land", "land"), Segment("e", "DAT.SG")], "land-DAT.SG")], "")


def test_ycoe_analyses_strip_hyphens():
    assert ycoe_analyses(sentence(), YCOE)[0].feats == {"Case": "Dat"}


def test_cltk_aligns_words(monkeypatch):
    from types import SimpleNamespace as NS

    tag = NS(key="Case", value="Dat")
    words = [
        NS(string="lande", lemma="land (NOUN)", upos=NS(tag="NOUN"), features=NS(features=[tag])),
        NS(string=",", lemma=",", upos=NS(tag="PUNCT"), features=NS(features=[])),
    ]
    monkeypatch.setattr("glossy2.baselines._cltk_words", lambda text: words)
    result = cltk_analyses(sentence())[0]
    assert (result.lemma, result.upos, result.feats) == ("land", "NOUN", {"Case": "Dat"})


def test_cltk_missing_word_gets_empty_analysis(monkeypatch):
    monkeypatch.setattr("glossy2.baselines._cltk_words", lambda text: [])
    result = cltk_analyses(sentence())[0]
    assert result.feats == {} and result.lemma is None


def test_cltk_unavailable_is_reported(monkeypatch):
    def missing(text):
        raise BaselineUnavailable("not installed")

    monkeypatch.setattr("glossy2.baselines._cltk_words", missing)
    try:
        cltk_analyses(sentence())
    except BaselineUnavailable as error:
        assert "not installed" in str(error)
    else:
        raise AssertionError("expected BaselineUnavailable")
