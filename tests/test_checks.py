from glossy2.checks import apply_checks, segments_rejoin
from glossy2.dictionary import Entry
from glossy2.models import InputWord, Segment, WordAnalysis
from glossy2.tags import render_gloss
from tests.fakes import FakeDictionary, FakeYcoe


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


def test_hyphenated_stem_spreads_over_stem_segments():
    segments = [Segment("norþ", "north"), Segment("mon", "man"), Segment("a", "GEN.PL")]
    word = InputWord("norþmona", hint_stem="north-person")
    result = apply_checks(word, proposed(form="norþmona", segments=segments), FakeYcoe(), DICTIONARY)
    assert [s.gloss for s in result.segments] == ["north", "person", "GEN.PL"]


def test_hyphenated_stem_on_one_segment_stays_whole():
    word = InputWord("norþmona", hint_stem="north-person")
    segments = [Segment("norþmon", "northman"), Segment("a", "GEN.PL")]
    result = apply_checks(word, proposed(form="norþmona", segments=segments), FakeYcoe(), DICTIONARY)
    assert result.segments[0].gloss == "north-person"


def test_unknown_form_never_gets_a_link():
    dictionary = FakeDictionary({"land": [LAND]}, ["land"])
    result = apply_checks(InputWord("Beormas"), proposed(form="Beormas", lemma="land"), FakeYcoe(), dictionary)
    assert "unknown_form" in codes(result) and result.wiktionary_url is None


def test_stem_hint_keeps_tags_in_a_hyphenated_single_segment():
    word = InputWord("sǣde", hint_stem="speak")
    segments = [Segment("sǣde", "say-PST-IND.3SG")]
    result = apply_checks(word, proposed(form="sǣde", segments=segments), FakeYcoe(), DICTIONARY)
    assert result.segments[0].gloss == "speak-PST-IND.3SG"


def test_stem_hint_replaces_every_stem_part():
    word = InputWord("forbærned", hint_stem="burn")
    segments = [Segment("forbærned", "for-burn-PART")]
    result = apply_checks(word, proposed(form="forbærned", segments=segments), FakeYcoe(), DICTIONARY)
    assert result.segments[0].gloss == "burn-PART"


def test_stem_hint_over_several_segments_leaves_no_duplicate():
    word = InputWord("forbærned", hint_stem="burn")
    segments = [Segment("for", "for"), Segment("bærn", "burn"), Segment("ed", "PART")]
    result = apply_checks(word, proposed(form="forbærned", segments=segments), FakeYcoe(), DICTIONARY)
    assert render_gloss(result).rstrip("?") == "burn-PART"


def test_stem_hint_keeps_prefix_tag():
    word = InputWord("gesiglan", hint_stem="sail")
    segments = [Segment("gesiglan", "PFX-sail-THM-INF")]
    result = apply_checks(word, proposed(form="gesiglan", segments=segments), FakeYcoe(), DICTIONARY)
    assert result.segments[0].gloss == "PFX-sail-THM-INF"


def test_hint_impossible_in_the_paradigm_is_flagged():
    entry = Entry("land", "noun", ["land"], LAND.url, [["dative", "singular"]])
    dictionary = FakeDictionary({"lande": [entry], "land": [entry]}, ["land"])
    word = InputWord("lande", hint_feats={"Case": "Gen"})
    result = apply_checks(word, proposed(feats={"Case": "Gen"}), FakeYcoe(), dictionary)
    assert result.feats["Case"] == "Gen"
    assert any(f.code == "hint_conflict" and "Case=Gen" in f.detail for f in result.flags)


def test_hint_allowed_by_the_paradigm_is_not_flagged():
    entry = Entry("land", "noun", ["land"], LAND.url, [["dative", "singular"]])
    dictionary = FakeDictionary({"lande": [entry], "land": [entry]}, ["land"])
    word = InputWord("lande", hint_feats={"Case": "Dat"})
    assert codes(apply_checks(word, proposed(), FakeYcoe(), dictionary)) == []


def test_no_paradigm_data_means_no_hint_flag():
    word = InputWord("lande", hint_feats={"Case": "Gen"})
    assert "hint_conflict" not in codes(apply_checks(word, proposed(feats={"Case": "Gen"}), FakeYcoe(), DICTIONARY))
