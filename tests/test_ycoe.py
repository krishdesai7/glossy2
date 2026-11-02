from collections import Counter
from pathlib import Path

from glossy2.ycoe import YcoeIndex, ycoe_features

FIXTURES = Path("tests/fixtures")


def test_counts():
    index = YcoeIndex.load(FIXTURES)
    assert index.tags("lande") == Counter({"N^D": 2})
    assert index.tags("þæm") == Counter({"D^D": 2})


def test_id_and_code_and_punct_ignored():
    index = YcoeIndex.load(FIXTURES)
    assert not index.tags("mini,1")
    assert not index.tags(".")
    assert not index.tags("<T1>")


def test_exclude():
    assert not YcoeIndex.load(FIXTURES, exclude={"mini.pos"}).tags("lande")


def test_features():
    assert ycoe_features("N^D") == ("NOUN", {"Case": "Dat"})
    assert ycoe_features("VBDI") == ("VERB", {"Tense": "Past", "Mood": "Ind"})
    assert ycoe_features("BEPS") == ("AUX", {"Tense": "Pres", "Mood": "Sub"})
    assert ycoe_features("UNKNOWN") == (None, {})


def test_features_compound_and_adverb_suffixes():
    assert ycoe_features("RP+VBDI") == ("VERB", {"Tense": "Past", "Mood": "Ind"})
    assert ycoe_features("ADV^T") == ("ADV", {})
    assert ycoe_features("PRO$^N") == ("PRON", {"Poss": "Yes", "Case": "Nom"})
    assert ycoe_features("VB") == ("VERB", {"VerbForm": "Inf"})
    assert ycoe_features("VBN") == ("VERB", {"VerbForm": "Part", "Tense": "Past"})


def test_missing_folder_is_an_error(tmp_path):
    import pytest

    from glossy2.ycoe import YcoeMissing

    with pytest.raises(YcoeMissing):
        YcoeIndex.load(tmp_path)


def test_excluding_a_file_that_does_not_exist_is_an_error():
    import pytest

    from glossy2.ycoe import YcoeMissing

    with pytest.raises(YcoeMissing):
        YcoeIndex.load(FIXTURES, exclude={"typo.pos"})
