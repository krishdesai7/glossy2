import pytest

from glossy2.hints import HintError, parse_line


def test_plain():
    assert [w.form for w in parse_line("Hē cwæð þæt")] == ["Hē", "cwæð", "þæt"]


def test_punct():
    word = parse_line("lande,")[0]
    assert (word.form, word.punct) == ("lande", ",")


def test_labels():
    word = parse_line("lande[noun,neuter]")[0]
    assert word.hint_upos == "NOUN" and word.hint_feats == {"Gender": "Neut"}


def test_labels_any_case_and_short_forms():
    word = parse_line("lande[NOUN,N,dat,Sg]")[0]
    assert word.hint_feats == {"Gender": "Neut", "Case": "Dat", "Number": "Sing"}


def test_stem():
    assert parse_line("hlāford-e[lord]")[0].hint_stem == "lord"


def test_multiword_stem():
    assert parse_line("gān[to go]")[0].hint_stem == "to go"


def test_label_and_stem():
    word = parse_line("lande[land,dat]")[0]
    assert word.hint_stem == "land" and word.hint_feats == {"Case": "Dat"}


def test_segmentation_fixed():
    assert parse_line("sǣ-d-e")[0].segments == ["sǣ", "d", "e"]
    assert parse_line("sǣ-d-e")[0].form == "sǣ-d-e"
    assert parse_line("sǣde")[0].segments is None


def test_punct_after_hint():
    word = parse_line("lande[noun],")[0]
    assert (word.form, word.punct, word.hint_upos) == ("lande", ",", "NOUN")


def test_unbalanced():
    with pytest.raises(HintError) as error:
        parse_line("on lande[noun")
    assert error.value.word == "lande"


def test_empty_hint():
    with pytest.raises(HintError) as error:
        parse_line("lande[]")
    assert error.value.word == "lande"


def test_two_stems():
    with pytest.raises(HintError) as error:
        parse_line("lande[land,earth]")
    assert error.value.word == "lande"


def test_contradiction_kept():
    word = parse_line("x[masc,neuter]")[0]
    assert word.hint_feats["Gender"] in {"Masc", "Neut"}
    assert word.hint_conflicts == ["Gender: Masc or Neut"]


def test_two_parts_of_speech_is_a_conflict():
    assert parse_line("x[noun,verb]")[0].hint_conflicts == ["part of speech: NOUN or VERB"]


def test_blank_line():
    assert parse_line("   ") == []


def test_space_before_hint_is_an_error():
    with pytest.raises(HintError) as error:
        parse_line("lande [noun]")
    assert "[noun]" in error.value.word


def test_second_bracket_is_an_error():
    with pytest.raises(HintError):
        parse_line("lande[noun][neuter]")


def test_text_after_hint_is_an_error():
    with pytest.raises(HintError) as error:
        parse_line("lande[noun]extra")
    assert error.value.word == "lande"


@pytest.mark.parametrize("label,short", [("strong", "str"), ("first", "1"), ("present", "prs"), ("name", "propn"), ("past", "pst")])
def test_labels_that_are_also_meanings_must_be_spelled_out(label, short):
    with pytest.raises(HintError) as error:
        parse_line(f"word[{label}]")
    assert short in error.value.reason and f"={label}" in error.value.reason


def test_equals_forces_a_stem_meaning():
    word = parse_line("strang-e[=strong]")[0]
    assert word.hint_stem == "strong" and not word.hint_feats


def test_empty_equals_is_an_error():
    with pytest.raises(HintError):
        parse_line("lande[=]")


def test_leading_punctuation_is_separated():
    word = parse_line('"Hē,')[0]
    assert (word.lead, word.form, word.punct) == ('"', "Hē", ",")


def test_middle_dots_are_separated():
    word = parse_line("·lande·")[0]
    assert (word.lead, word.form, word.punct) == ("·", "lande", "·")


def test_punctuation_alone_stays_a_token():
    assert parse_line("( lande")[0].form == "("
