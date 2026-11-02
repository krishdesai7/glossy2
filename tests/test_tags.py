import re
from pathlib import Path

from glossy2.gold import load_gold
from glossy2.models import Flag, Segment, WordAnalysis
from glossy2.tags import HUMAN_TO_FEATS, parse_gloss, render_gloss


def test_parse():
    assert parse_gloss("say-PST-IND.3SG") == ("say", {"Tense": "Past", "Mood": "Ind", "Person": "3", "Number": "Sing"})
    assert parse_gloss("DET.DEF.DAT.SG.N")[1] == {
        "PronType": "Det", "Definite": "Def", "Case": "Dat", "Number": "Sing", "Gender": "Neut",
    }
    assert parse_gloss("north-man-GEN.PL") == ("north-man", {"Case": "Gen", "Number": "Plur"})
    assert parse_gloss("find.out-THM-INF") == ("find.out", {"Thematic": "Yes", "VerbForm": "Inf"})
    assert parse_gloss("be.allowed-PRS")[0] == "be.allowed"


def test_function_word_has_no_stem():
    assert parse_gloss("3SG.M.GEN")[0] == ""


def test_extensions():
    for tag, key in [
        ("HAB", "Aspect"), ("THM", "Thematic"), ("AGT", "Derivation"), ("NMLZ", "Derivation"),
        ("PFX", "Prefix"), ("COMP", "PartType"), ("NEG", "Polarity"),
    ]:
        assert key in HUMAN_TO_FEATS[tag]


def test_every_gold_tag_known():
    for sentence in load_gold(Path("corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex")):
        for token in sentence.tokens:
            for piece in re.split(r"[-.]", token.gloss):
                if piece.isascii() and piece.upper() == piece and any(c.isalpha() for c in piece):
                    assert piece in HUMAN_TO_FEATS, (token.form, token.gloss)


def analysis(flags=()):
    segments = [Segment("sǣ", "say"), Segment("d", "PST"), Segment("e", "IND.3SG")]
    return WordAnalysis("sǣde", segments=segments, flags=list(flags))


def test_render_roundtrip():
    assert render_gloss(analysis()) == "say-PST-IND.3SG"


def test_render_marks_flagged():
    assert render_gloss(analysis([Flag("ambiguous", "could be either")])).endswith("?")


def test_render_failed():
    word = WordAnalysis("sǣde", flags=[Flag("analysis_failed", "no response")])
    assert render_gloss(word) == "???"
