from pathlib import Path

import pytest

from glossy2.dictionary import Dictionary, build_index


@pytest.fixture(scope="module")
def dictionary(tmp_path_factory):
    path = tmp_path_factory.mktemp("dict") / "d.sqlite"
    build_index(Path("tests/fixtures/mini-kaikki.jsonl"), path)
    return Dictionary.open(path)


def test_inflected_form(dictionary):
    entries = dictionary.lookup("lande")
    assert {e.lemma for e in entries} == {"land"}
    assert ["dative", "singular"] in entries[0].form_tags


def test_lemma_form(dictionary):
    entry = dictionary.lookup("land")[0]
    assert entry.lemma == "land"
    assert "a country" in entry.senses


def test_url(dictionary):
    assert dictionary.lookup("land")[0].url == "https://en.wiktionary.org/wiki/land#Old_English"


def test_skips_template_rows(dictionary):
    assert dictionary.lookup("no-table-tags") == []
    assert dictionary.lookup("ang-decl-noun-a-n") == []


def test_form_of_sense_resolves_to_lemma(dictionary):
    entry = dictionary.lookup("sǣde")[0]
    assert entry.lemma == "secgan"
    assert entry.url == "https://en.wiktionary.org/wiki/secgan#Old_English"


def test_lookup_normalises(dictionary):
    assert dictionary.lookup("LANDES")[0].lemma == "land"
    assert dictionary.lookup("sæġde")[0].lemma == "secgan"


def test_has_lemma(dictionary):
    assert dictionary.has_lemma("land")
    assert dictionary.has_lemma("seċġan")
    assert not dictionary.has_lemma("gesceopan")
    assert not dictionary.has_lemma("lande")
