from collections import Counter

from glossy2.checks import apply_checks, segments_rejoin
from glossy2.dictionary import Entry
from glossy2.models import InputWord, Segment, WordAnalysis


class FakeYcoe:
    def __init__(self, table=None):
        self.table = table or {}

    def tags(self, form):
        return Counter(self.table.get(form, {}))


class FakeDictionary:
    def __init__(self, entries=None, lemmas=()):
        self.entries, self.lemmas = entries or {}, set(lemmas)

    def lookup(self, form):
        return self.entries.get(form, [])

    def has_lemma(self, lemma):
        return lemma in self.lemmas


LAND = Entry("land", "noun", ["land"], "https://en.wiktionary.org/wiki/land#Old_English", [])
YCOE = FakeYcoe({"lande": {"N^D": 5}})
DICTIONARY = FakeDictionary({"lande": [LAND], "land": [LAND]}, ["land"])


def proposed(**changes):
    values = dict(
        form="lande", segments=[Segment("land", "land"), Segment("e", "DAT.SG")], lemma="land",
        upos="NOUN", feats={"Case": "Dat", "Number": "Sing"}, meaning="land",
    )
    return WordAnalysis(**{**values, **changes})


def codes(result):
    return [flag.code for flag in result.flags]


def test_clean_word():
    result = apply_checks(InputWord("lande"), proposed(), YCOE, DICTIONARY)
    assert codes(result) == []
    assert result.wiktionary_url == LAND.url


def test_hint_wins_and_flags():
    word = InputWord("lande", hint_feats={"Gender": "Neut"})
    result = apply_checks(word, proposed(feats={"Case": "Dat", "Gender": "Masc"}), YCOE, DICTIONARY)
    assert result.feats["Gender"] == "Neut"
    flag = next(f for f in result.flags if f.code == "hint_conflict")
    assert "Neut" in flag.detail and "Masc" in flag.detail


def test_hint_rewrites_printed_gloss():
    word = InputWord("lande", hint_feats={"Case": "Acc"})
    result = apply_checks(word, proposed(), FakeYcoe(), DICTIONARY)
    assert result.segments[-1].gloss == "ACC.SG"


def test_hint_rewrites_bundled_tag():
    segments = [Segment("sǣ", "say"), Segment("de", "PST.3SG")]
    word = InputWord("sǣde", hint_feats={"Number": "Plur"})
    result = apply_checks(word, proposed(form="sǣde", segments=segments, feats={"Number": "Sing"}), FakeYcoe(), DICTIONARY)
    assert result.segments[-1].gloss == "PST.3PL"


def test_hint_upos_wins():
    word = InputWord("lande", hint_upos="NOUN")
    result = apply_checks(word, proposed(upos="VERB", feats={}), YCOE, DICTIONARY)
    assert result.upos == "NOUN" and "hint_conflict" in codes(result)


def test_hint_stem_wins():
    word = InputWord("lande", hint_stem="lord")
    result = apply_checks(word, proposed(meaning="master"), YCOE, DICTIONARY)
    assert result.segments[0].gloss == "lord" and result.meaning == "lord"
    assert codes(result) == []


def test_hint_stem_keeps_tags_on_same_segment():
    segments = [Segment("cwæð", "speak.PST.IND.3SG")]
    word = InputWord("cwæð", hint_stem="say")
    result = apply_checks(word, proposed(form="cwæð", segments=segments), FakeYcoe(), DICTIONARY)
    assert result.segments[0].gloss == "say.PST.IND.3SG"


def test_contradictory_hints_flagged():
    word = InputWord("lande", hint_conflicts=["Gender: Masc or Neut"])
    assert "hint_conflict" in codes(apply_checks(word, proposed(), YCOE, DICTIONARY))


def test_unknown_form():
    word = InputWord("zzz")
    result = apply_checks(word, proposed(form="zzz", lemma="zzz"), FakeYcoe(), FakeDictionary())
    assert "unknown_form" in codes(result)
    assert result.wiktionary_url is None


def test_tag_unseen():
    result = apply_checks(InputWord("lande"), proposed(feats={"Case": "Acc"}), YCOE, DICTIONARY)
    assert codes(result) == ["tag_unseen"]


def test_tag_compatible_no_flag():
    feats = {"Case": "Dat", "Number": "Sing", "Gender": "Neut"}
    assert codes(apply_checks(InputWord("lande"), proposed(feats=feats), YCOE, DICTIONARY)) == []


def test_quantifier_and_adjective_do_not_conflict():
    ycoe = FakeYcoe({"ealle": {"Q^A": 3}})
    result = apply_checks(InputWord("ealle"), proposed(form="ealle", upos="ADJ", feats={"Case": "Acc"}), ycoe, DICTIONARY)
    assert "tag_unseen" not in codes(result)


def test_known_to_dictionary_only_no_flag():
    result = apply_checks(InputWord("lande"), proposed(), FakeYcoe(), DICTIONARY)
    assert codes(result) == []


def test_lemma_not_in_dictionary():
    result = apply_checks(InputWord("lande"), proposed(lemma="gesceopan"), YCOE, DICTIONARY)
    assert "lemma_not_in_dictionary" in codes(result)
    assert result.wiktionary_url is None and result.lemma == "gesceopan"


def test_url_from_entry_only():
    candidate = proposed(wiktionary_url="https://example.com/made-up")
    assert apply_checks(InputWord("lande"), candidate, YCOE, DICTIONARY).wiktionary_url == LAND.url


def test_url_macrons_case():
    dictionary = FakeDictionary({"lande": [LAND], "lānd": [LAND]}, ["lānd"])
    result = apply_checks(InputWord("lande"), proposed(lemma="lānd"), YCOE, dictionary)
    assert result.wiktionary_url == LAND.url


def test_rejoin():
    assert segments_rejoin("sǣde", [Segment("sǣ", "say"), Segment("d", "PST"), Segment("e", "IND.3SG")])
    assert segments_rejoin("sǣ-d-e", [Segment("sǣ", "say"), Segment("de", "PST")])
    assert not segments_rejoin("sǣde", [Segment("sa", "say"), Segment("de", "PST")])
