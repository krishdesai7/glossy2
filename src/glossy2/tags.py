"""The human gloss tags and their Universal Dependencies equivalents.

UD can't express everything in these glosses, so a few extra feature names are used:
Thematic, Derivation, Prefix, PartType, Deixis, Declension, Form.
"""

from glossy2.models import WordAnalysis

HUMAN_TO_FEATS: dict[str, dict[str, str]] = {
    "SG": {"Number": "Sing"}, "PL": {"Number": "Plur"},
    "NOM": {"Case": "Nom"}, "ACC": {"Case": "Acc"}, "GEN": {"Case": "Gen"},
    "DAT": {"Case": "Dat"}, "INS": {"Case": "Ins"}, "VOC": {"Case": "Voc"},
    "M": {"Gender": "Masc"}, "F": {"Gender": "Fem"}, "N": {"Gender": "Neut"},
    "1": {"Person": "1"}, "2": {"Person": "2"}, "3": {"Person": "3"},
    "1SG": {"Person": "1", "Number": "Sing"}, "2SG": {"Person": "2", "Number": "Sing"},
    "3SG": {"Person": "3", "Number": "Sing"}, "1PL": {"Person": "1", "Number": "Plur"},
    "2PL": {"Person": "2", "Number": "Plur"}, "3PL": {"Person": "3", "Number": "Plur"},
    "PRS": {"Tense": "Pres"}, "PST": {"Tense": "Past"},
    "IND": {"Mood": "Ind"}, "SJV": {"Mood": "Sub"}, "IMP": {"Mood": "Imp"},
    "INF": {"VerbForm": "Inf"}, "PART": {"VerbForm": "Part"}, "PASS": {"Voice": "Pass"},
    "DET": {"PronType": "Det"}, "DEM": {"PronType": "Dem"}, "REL": {"PronType": "Rel"},
    "DEF": {"Definite": "Def"}, "INDF": {"Definite": "Ind"},
    "DIST": {"Deixis": "Dist"}, "PROX": {"Deixis": "Prox"},
    "STR": {"Declension": "Str"}, "WK": {"Declension": "Wk"},
    "CMP": {"Degree": "Cmp"}, "SUP": {"Degree": "Sup"},
    "COMP": {"PartType": "Comp"}, "NEG": {"Polarity": "Neg"},
    "ADV": {"Form": "Adv"}, "ADJ": {"Form": "Adj"},
    "HAB": {"Aspect": "Hab"}, "THM": {"Thematic": "Yes"}, "PFX": {"Prefix": "Yes"},
    "AGT": {"Derivation": "Agt"}, "NMLZ": {"Derivation": "Nmlz"},
}


def parse_gloss(gloss: str) -> tuple[str, dict[str, str]]:
    """Split a gloss into its lexical stem and its grammatical features."""
    feats: dict[str, str] = {}
    stems: list[str] = []
    for part in gloss.rstrip("?").split("-"):
        lexical = []
        for piece in part.split("."):
            if piece in HUMAN_TO_FEATS:
                feats.update(HUMAN_TO_FEATS[piece])
            elif piece:
                lexical.append(piece)
        if lexical:
            stems.append(".".join(lexical))
    return "-".join(stems), feats


def render_gloss(analysis: WordAnalysis) -> str:
    codes = {flag.code for flag in analysis.flags}
    if "analysis_failed" in codes:
        return "???"
    text = "-".join(segment.gloss for segment in analysis.segments)
    return f"{text}?" if codes else text
