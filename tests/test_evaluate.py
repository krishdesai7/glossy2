from glossy2.dictionary import Entry
from glossy2.evaluate import Withheld, aggregate, make_inputs, score_sentence
from glossy2.gold import align_segments
from glossy2.models import Flag, GoldSentence, GoldToken, Segment, WordAnalysis
from tests.fakes import FakeDictionary

NO_DICTIONARY = FakeDictionary()


def token(form, gloss, punct=""):
    return GoldToken(form, punct, align_segments(form, gloss), gloss)


def sentence(*tokens):
    return GoldSentence(3, "main", list(tokens), "")


SAID = token("sǣ-d-e", "say-PST-IND.3SG")
LAND = token("land-e", "land-DAT.SG")


def predicted(form, gloss, parts=None, feats=None, lemma=None, flags=()):
    segments = [Segment(f, g) for f, g in parts] if parts else [Segment(form, gloss)]
    return WordAnalysis(form, "", segments, lemma, None, feats or {}, None, None, list(flags))


def score(gold_token, analysis, withheld, corrections=None, dictionary=NO_DICTIONARY):
    return score_sentence(sentence(gold_token), [analysis], [withheld], corrections or {}, dictionary)[0]


def all_withheld(gold_token):
    from glossy2.tags import parse_gloss

    stem, feats = parse_gloss(gold_token.gloss)
    return Withheld(bool(stem), set(feats))


def test_inputs_have_no_hyphens():
    for level in ["none", "half", "stem", "stem+half"]:
        words, _ = make_inputs(sentence(SAID), level)
        assert words[0].form == "sǣde" and words[0].segments is None


def test_punct_passes_through():
    assert make_inputs(sentence(token("land-e", "land-DAT.SG", ",")), "none")[0][0].punct == ","


def test_level_none():
    words, withheld = make_inputs(sentence(SAID), "none")
    assert not words[0].hint_feats and not words[0].hint_stem
    assert withheld[0].stem and withheld[0].feats == {"Tense", "Mood", "Person", "Number"}


def test_level_stem():
    words, withheld = make_inputs(sentence(SAID), "stem")
    assert words[0].hint_stem == "say" and not words[0].hint_feats
    assert not withheld[0].stem and withheld[0].feats == {"Tense", "Mood", "Person", "Number"}


def test_level_half_repeatable():
    tokens = [SAID] * 40
    first, withheld = make_inputs(sentence(*tokens), "half")
    second, _ = make_inputs(sentence(*tokens), "half")
    assert [w.hint_feats for w in first] == [w.hint_feats for w in second]
    given = sum(len(w.hint_feats) for w in first)
    assert 40 < given < 120
    assert all(not (set(w.hint_feats) & h.feats) for w, h in zip(first, withheld))
    assert not first[0].hint_stem and withheld[0].stem


def test_level_stem_half():
    words, withheld = make_inputs(sentence(*[SAID] * 10), "stem+half")
    assert all(w.hint_stem == "say" for w in words)
    assert sum(len(w.hint_feats) for w in words) > 0
    assert not withheld[0].stem


def test_only_withheld_scored():
    analysis = predicted("lande", "land-DAT.SG", feats={"Case": "Dat", "Number": "Sing"})
    result = score(LAND, analysis, Withheld(True, {"Number"}))
    assert result.feats == {"Number": True}


def test_unmarked_extra_ignored():
    analysis = predicted("lande", "land-DAT.SG", feats={"Case": "Dat", "Number": "Sing", "Gender": "Neut"})
    assert "Gender" not in score(LAND, analysis, all_withheld(LAND)).feats


def test_wrong_feature_counted():
    analysis = predicted("lande", "land-ACC.SG", feats={"Case": "Acc", "Number": "Sing"})
    assert score(LAND, analysis, all_withheld(LAND)).feats == {"Case": False, "Number": True}


def test_feature_read_from_gloss_when_feats_omit_it():
    analysis = predicted("lande", "land-DAT.SG", feats={})
    assert score(LAND, analysis, all_withheld(LAND)).feats == {"Case": True, "Number": True}


def test_tina_feature_scored():
    corrections = {(3, 0): {"features.gender": "neuter"}}
    good = predicted("lande", "land-DAT.SG", feats={"Gender": "Neut"})
    bad = predicted("lande", "land-DAT.SG", feats={"Gender": "Masc"})
    assert score(LAND, good, all_withheld(LAND), corrections).feats["Gender"] is True
    assert score(LAND, bad, all_withheld(LAND), corrections).feats["Gender"] is False


def test_hinted_tina_feature_not_scored():
    corrections = {(3, 0): {"features.case": "dative"}}
    analysis = predicted("lande", "land-DAT.SG", feats={"Case": "Dat"})
    assert "Case" not in score(LAND, analysis, Withheld(True, {"Number"}), corrections).feats


def test_exact_gloss():
    good = predicted("sǣde", "", [("sǣ", "say"), ("d", "PST"), ("e", "IND.3SG")])
    assert score(SAID, good, all_withheld(SAID)).exact is True
    bad = predicted("sǣde", "", [("sǣ", "speak"), ("d", "PST"), ("e", "IND.3SG")])
    assert score(SAID, bad, all_withheld(SAID)).exact is False


def test_flag_mark_ignored_in_exact():
    flagged = predicted("lande", "", [("land", "land"), ("e", "DAT.SG")], flags=[Flag("ambiguous", "?")])
    assert score(LAND, flagged, all_withheld(LAND)).exact is True


def test_exact_excludes_nothing_withheld():
    analysis = predicted("lande", "land-DAT.SG")
    assert score(LAND, analysis, Withheld(False, set())).exact is None


def test_meaning_exact_and_sense():
    entry = Entry("secgan", "verb", ["to say, tell, speak"], "u", [])
    dictionary = FakeDictionary({"sǣ-d-e": [entry], "sǣde": [entry]})
    analysis = predicted("sǣde", "", [("sǣ", "speak"), ("d", "PST"), ("e", "IND.3SG")])
    result = score(SAID, analysis, all_withheld(SAID), dictionary=dictionary)
    assert result.meaning_exact is False and result.meaning_sense is True


def test_sense_match_needs_both_words_in_one_sense():
    entry = Entry("secgan", "verb", ["to say, tell"], "u", [])
    dictionary = FakeDictionary({"sǣ-d-e": [entry], "sǣde": [entry]})
    analysis = predicted("sǣde", "", [("sǣ", "dog"), ("d", "PST"), ("e", "IND.3SG")])
    assert score(SAID, analysis, all_withheld(SAID), dictionary=dictionary).meaning_sense is False


def test_meaning_not_scored_when_stem_was_given():
    analysis = predicted("sǣde", "", [("sǣ", "say"), ("d", "PST"), ("e", "IND.3SG")])
    result = score(SAID, analysis, Withheld(False, {"Tense"}))
    assert result.meaning_exact is None and result.meaning_sense is None


def test_lemma_only_on_corrections():
    analysis = predicted("lande", "land-DAT.SG", lemma="land")
    assert score(LAND, analysis, all_withheld(LAND)).lemma is None
    assert score(LAND, analysis, all_withheld(LAND), {(3, 0): {"lemma": "lānd"}}).lemma is True
    assert score(LAND, analysis, all_withheld(LAND), {(3, 0): {"lemma": "other"}}).lemma is False


def test_failed_counts_wrong():
    failed = WordAnalysis("lande", "", [Segment("lande", "???")], flags=[Flag("analysis_failed", "x")])
    result = score(LAND, failed, all_withheld(LAND), {(3, 0): {"lemma": "land"}})
    assert result.failed and result.exact is False and result.segmentation is False
    assert set(result.feats.values()) == {False} and result.lemma is False
    assert aggregate([result]).exact == (0, 1)


def test_flag_quality():
    good = score(LAND, predicted("lande", "", [("land", "land"), ("e", "DAT.SG")]), all_withheld(LAND))
    flagged_bad = score(LAND, predicted("lande", "x", flags=[Flag("tag_unseen", "?")]), all_withheld(LAND))
    scores = aggregate([good, flagged_bad])
    assert scores.unflagged == (1, 1) and scores.flagged == (0, 1)


def test_segmentation():
    right = predicted("sǣde", "", [("sǣ", "a"), ("d", "b"), ("e", "c")])
    wrong = predicted("sǣde", "", [("sǣd", "a"), ("e", "b")])
    assert score(SAID, right, all_withheld(SAID)).segmentation is True
    assert score(SAID, wrong, all_withheld(SAID)).segmentation is False


def test_punctuation_tokens_not_scored():
    gold = sentence(token("(", "("), LAND)
    results = score_sentence(gold, [WordAnalysis("("), predicted("lande", "x")], [Withheld(False, set()), all_withheld(LAND)], {}, NO_DICTIONARY)
    assert [r.form for r in results] == ["land-e"]


def test_aggregate_per_feature():
    analysis = predicted("lande", "land-ACC.SG", feats={"Case": "Acc", "Number": "Sing"})
    scores = aggregate([score(LAND, analysis, all_withheld(LAND))])
    assert scores.features == {"Case": (0, 1), "Number": (1, 1)}
    assert scores.tokens == 1
