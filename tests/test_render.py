from glossy2.models import Flag, Segment, WordAnalysis
from glossy2.render import display_width, render_gb4e, render_text


def word(form, gloss, flags=(), lemma="land", url="https://en.wiktionary.org/wiki/land#Old_English", punct=""):
    return WordAnalysis(form, punct, [Segment(form, gloss)], lemma, "NOUN", {}, None, url, list(flags))


def test_columns_align():
    lines = render_text([word("a\u0304a\u0304", "long-gloss"), word("b", "c")]).splitlines()
    assert display_width(lines[0].split("b")[0]) == lines[1].index("c")


def test_long_sentence_wraps(monkeypatch):
    monkeypatch.setenv("COLUMNS", "30")
    text = render_text([word(f"word{i}", f"gloss{i}") for i in range(12)]).split("\n\n")[0]
    assert all(len(line) <= 30 for line in text.splitlines())
    assert "word11" in text


def test_flags_listed():
    text = render_text([word("x", "y", [Flag("unknown_form", "x isn't known")])])
    assert "x: x isn't known" in text


def test_table_has_lemma_and_link():
    text = render_text([word("a", "b"), word("c", "d", lemma=None, url=None)])
    assert "https://en.wiktionary.org/wiki/land#Old_English" in text
    assert text.splitlines()[-1].split()[-1] == "-"


def test_segments_shown_with_hyphens():
    analysis = WordAnalysis("sǣde", "", [Segment("sǣ", "say"), Segment("de", "PST")])
    assert "sǣ-de" in render_text([analysis]).splitlines()[0]


def test_gb4e():
    analysis = WordAnalysis("sǣde", ",", [Segment("sǣ", "say"), Segment("de", "PST.3SG")])
    text = render_gb4e([analysis], "He said")
    assert "\\gll sǣ-de,\\\\" in text
    assert "say-\\textsc{pst.3sg}\\\\" in text
    assert "\\glt `He said'" in text


def test_gb4e_escapes():
    text = render_gb4e([word("a&b", "x_y")])
    assert "a\\&b" in text and "x\\_y" in text


def test_gb4e_flagged_marked():
    assert "y?" in render_gb4e([word("x", "y", [Flag("ambiguous", "?")])])


def test_gb4e_blank_translation():
    assert "\\glt ``" not in render_gb4e([word("x", "y")])
    assert "\\glt" in render_gb4e([word("x", "y")])


def test_gb4e_multiword_gloss_is_one_group():
    assert "{to go.\\textsc{inf}}" in render_gb4e([word("gān", "to go.INF")])


def test_lead_is_displayed():
    analysis = WordAnalysis("Hē", ",", [Segment("Hē", "3SG")], lead='"')
    assert render_text([analysis]).splitlines()[0].startswith('"Hē,')
    assert '"Hē,' in render_gb4e([analysis])


def test_stem_replaced_segment_leaves_no_double_hyphen():
    analysis = WordAnalysis("for", "", [Segment("f", "burn"), Segment("or", ""), Segment("x", "PART")])
    assert "burn-PART" in render_text([analysis])
