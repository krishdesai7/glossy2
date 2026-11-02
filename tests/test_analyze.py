import json

from glossy2.analyze import Context, analyze_sentence, build_messages
from glossy2.dictionary import Entry
from glossy2.llm import LLMError
from glossy2.models import GoldSentence, GoldToken, InputWord, Segment
from tests.fakes import FakeDictionary, FakeYcoe

LAND = Entry("land", "noun", ["land, country"], "https://en.wiktionary.org/wiki/land#Old_English", [["dative", "singular"]])
EXAMPLE = GoldSentence(
    7, "ohthere",
    [GoldToken("hlāford-e", ",", [Segment("hlāford", "lord"), Segment("e", "DAT.SG")], "lord-DAT.SG")],
    "to his lord",
)
UNSEEN_TEXT = "wīdsæ"


def word(index=0, segments=None, lemma="land", ambiguous=False, reason=""):
    return {
        "index": index,
        "segments": segments or [{"form": "land", "gloss": "land"}, {"form": "e", "gloss": "DAT.SG"}],
        "lemma": lemma, "upos": "NOUN", "feats": {"Case": "Dat", "Number": "Sing"},
        "meaning": "land", "ambiguous": ambiguous, "ambiguity_reason": reason,
    }


def context(*responses, ycoe=None, dictionary=None):
    calls = []
    queue = list(responses)

    def complete(messages):
        calls.append(messages)
        outcome = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    ctx = Context(
        ycoe=ycoe or FakeYcoe({"lande": {"N^D": 897}}),
        dictionary=dictionary or FakeDictionary({"lande": [LAND], "land": [LAND]}, ["land"]),
        examples=[EXAMPLE],
        complete=complete,
    )
    return ctx, calls


def prompt(messages):
    return "\n".join(m["content"] for m in messages)


def test_prompt_has_candidates():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("lande")], ctx))
    assert "N^D" in text and "897" in text and "land, country" in text


def test_prompt_has_hints_as_fixed():
    ctx, _ = context({})
    words = [InputWord("land-e", segments=["land", "e"], hint_feats={"Gender": "Neut"}, hint_stem="earth")]
    text = prompt(build_messages(words, ctx))
    assert "Gender=Neut" in text and "earth" in text and "land, e" in text
    assert "must not be changed" in text


def test_prompt_uses_only_given_examples():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("lande")], ctx))
    assert "hlāford-e" in text and "lord-DAT.SG" in text
    assert UNSEEN_TEXT not in text


def test_sentence_being_analysed_is_not_its_own_example():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("hlāforde")], ctx))
    assert "lord-DAT.SG" not in text


def test_prompt_no_ycoe_passages():
    ctx, _ = context({})
    system_free = build_messages([InputWord("lande")], ctx)[-1]["content"]
    assert "coorosiu" not in system_free and "_N^D" not in system_free


def test_prompt_allows_unknown():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("lande")], ctx))
    assert "ambiguous" in text and "null" in text


def test_good_response():
    ctx, calls = context({"words": [word()]})
    result = analyze_sentence([InputWord("lande", punct=",")], ctx)
    assert len(calls) == 1
    assert (result[0].form, result[0].punct, result[0].lemma) == ("lande", ",", "land")
    assert result[0].wiktionary_url == LAND.url and result[0].flags == []


def test_wrong_word_count_retries_once():
    ctx, calls = context({"words": []}, {"words": [word()]})
    assert analyze_sentence([InputWord("lande")], ctx)[0].lemma == "land"
    assert len(calls) == 2


def test_wrong_word_count_twice():
    ctx, calls = context({"words": []})
    result = analyze_sentence([InputWord("lande"), InputWord("on")], ctx)
    assert len(calls) == 2
    assert [r.flags[0].code for r in result] == ["analysis_failed"] * 2


def test_malformed_word_treated_as_failure():
    ctx, _ = context({"words": ["nonsense"]})
    assert analyze_sentence([InputWord("lande")], ctx)[0].flags[0].code == "analysis_failed"


def test_llm_error():
    ctx, _ = context(LLMError("timed out"))
    result = analyze_sentence([InputWord("lande")], ctx)
    assert result[0].flags[0].code == "analysis_failed"
    assert "timed out" in result[0].flags[0].detail


def test_bad_segments_retry_then_flag():
    bad = word(segments=[{"form": "lond", "gloss": "land"}])
    ctx, calls = context({"words": [bad]})
    result = analyze_sentence([InputWord("lande")], ctx)
    assert len(calls) == 2
    assert result[0].flags[0].code == "segments_mismatch"
    assert [s.form for s in result[0].segments] == ["lande"]


def test_fixed_segments_kept():
    response = word(segments=[{"form": "sǣd", "gloss": "say"}, {"form": "e", "gloss": "PST"}])
    ctx, _ = context({"words": [response]}, ycoe=FakeYcoe(), dictionary=FakeDictionary())
    result = analyze_sentence([InputWord("sǣ-d-e", segments=["sǣ", "d", "e"])], ctx)
    assert [s.form for s in result[0].segments] == ["sǣ", "d", "e"]
    assert "hint_conflict" in [f.code for f in result[0].flags]


def test_model_ambiguous_flag():
    ctx, _ = context({"words": [word(ambiguous=True, reason="could be accusative")]})
    flag = analyze_sentence([InputWord("lande")], ctx)[0].flags[0]
    assert (flag.code, flag.detail) == ("ambiguous", "could be accusative")


def test_unknown_word_no_link():
    response = word(segments=[{"form": "zzz", "gloss": "thing"}], lemma="zzz")
    ctx, _ = context({"words": [response]}, ycoe=FakeYcoe(), dictionary=FakeDictionary())
    result = analyze_sentence([InputWord("zzz")], ctx)[0]
    assert "unknown_form" in [f.code for f in result.flags] and result.wiktionary_url is None


def test_punctuation_only_word_not_sent():
    ctx, _ = context({"words": [word(index=0)]})
    result = analyze_sentence([InputWord("("), InputWord("lande")], ctx)
    assert result[0].form == "(" and result[0].flags == [] and result[1].lemma == "land"


def test_output_keeps_the_users_spelling():
    response = word(segments=[{"form": "ġe", "gloss": "PFX"}, {"form": "hālg", "gloss": "hallow"}, {"form": "od", "gloss": "PART"}], lemma=None)
    ctx, _ = context({"words": [response]}, ycoe=FakeYcoe(), dictionary=FakeDictionary())
    result = analyze_sentence([InputWord("gehalgod")], ctx)[0]
    assert [s.form for s in result.segments] == ["ge", "halg", "od"]


def test_hyphens_in_a_single_segment_gloss_are_left_alone():
    # Round 2 of tuning: rewriting these to dots broke 46 correct dev glosses.
    response = word(segments=[{"form": "lande", "gloss": "land-DAT.SG"}])
    ctx, _ = context({"words": [response]})
    assert analyze_sentence([InputWord("lande")], ctx)[0].segments[0].gloss == "land-DAT.SG"


def test_prompt_shows_how_to_split_segments():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("lande")], ctx))
    assert '{"form": "d", "gloss": "PST"}' in text and "one segment entry per morpheme" in text


def test_prompt_gives_feature_values_and_conventions():
    ctx, _ = context({})
    text = prompt(build_messages([InputWord("lande")], ctx))
    assert "Declension=Str" in text and "NMLZ" in text and "fixed stem meaning still" in text
