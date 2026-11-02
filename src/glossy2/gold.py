"""Human-glossed answer keys: gb4e parsing, Tina corrections and the dev/test split."""

import json
import random
import re
from pathlib import Path

from glossy2.models import GoldSentence, GoldToken, Segment

_EXAMPLE = re.compile(r"\\gll (.*?)\\\\\s*\n(.*?)\\\\\s*\n\s*\\glt (.*?)\n", re.S)
_SMALLCAPS = re.compile(r"\\textsc\{([^}]*)\}")
_TRAILING_PUNCT = re.compile(r"[.,;:!?\"'’”]+$")

# Sentence index where each passage of the Ohthere and Wulfstan text starts.
OHTHERE_PASSAGES = {0: "ohthere", 51: "wulfstan"}
SPLIT_SEED = 1729
DEV_PER_PASSAGE = {"ohthere": 11, "wulfstan": 4}


def normalise_gloss(raw: str) -> str:
    """Turn a LaTeX gloss into plain Leipzig text such as ``say-PST-IND.3SG``."""
    text = _SMALLCAPS.sub(lambda m: m[1].upper(), raw)
    text = text.replace("{", "").replace("}", "").replace("\\", "")
    text = text.replace(",", ".")
    text = re.sub(r"-{2,}", "-", text)
    text = _TRAILING_PUNCT.sub("", text)
    return comparative_to_cmp(text)


def comparative_to_cmp(gloss: str) -> str:
    """Bare ``COMP`` is a complementizer; attached to a stem it means comparative."""
    if gloss == "COMP":
        return gloss
    return re.sub(r"(?<![A-Z])COMP(?![A-Z])", "CMP", gloss)


def align_segments(form: str, gloss: str) -> list[Segment]:
    """Pair hyphen-separated parts, keeping the word whole if the counts differ."""
    forms = [part for part in form.split("-") if part]
    glosses = [part for part in gloss.split("-") if part]
    if len(forms) == len(glosses):
        return [Segment(f, g) for f, g in zip(forms, glosses)]
    return [Segment("".join(forms), gloss)]


def _strip_footnotes(text: str) -> str:
    while (start := text.find("\\footnote{")) != -1:
        depth, i = 0, start + len("\\footnote")
        while i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
            if depth == 0:
                break
        text = text[:start] + text[i:]
    return text


def _clean_translation(raw: str) -> str:
    text = _strip_footnotes(raw).strip()
    text = re.sub(r"\}\s*$", "", text).strip()
    return re.sub(r"\s+", " ", text.strip("`'\" "))


def _passages_for(path: Path) -> dict[int, str]:
    return OHTHERE_PASSAGES if "Ohthere" in path.name else {0: "main"}


def load_gold(tex_path: Path, corrections_path: Path | None = None) -> list[GoldSentence]:
    tex = Path(tex_path).read_text(encoding="utf-8")
    tex = tex[tex.index(r"\begin{document}") :]
    corrections = load_corrections(corrections_path) if corrections_path else {}
    starts = _passages_for(Path(tex_path))
    sentences = []
    passage = starts[0]
    for sid, match in enumerate(_EXAMPLE.finditer(tex)):
        passage = starts.get(sid, passage)
        forms, glosses = match[1].split(), match[2].split()
        if len(forms) != len(glosses):
            raise ValueError(f"sentence {sid}: {len(forms)} words but {len(glosses)} glosses")
        tokens = []
        for idx, (raw_form, raw_gloss) in enumerate(zip(forms, glosses)):
            found = _TRAILING_PUNCT.search(raw_form)
            punct = found[0] if found else ""
            form = raw_form[: len(raw_form) - len(punct)]
            fixed = corrections.get((sid, idx), {}).get("morphologicalGloss")
            gloss = normalise_gloss(str(fixed) if fixed else raw_gloss)
            tokens.append(GoldToken(form, punct, align_segments(form, gloss), gloss))
        sentences.append(GoldSentence(sid, passage, tokens, _clean_translation(match[3])))
    return sentences


def load_corrections(path: Path) -> dict[tuple[int, int], dict[str, object]]:
    corrections: dict[tuple[int, int], dict[str, object]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                corrections.setdefault((row["sentence"], row["token"]), {})[row["field"]] = row["value"]
    return corrections


def split_sentences(sentences: list[GoldSentence]) -> tuple[list[GoldSentence], list[GoldSentence]]:
    """Fixed dev and test sets, stratified by passage."""
    rng = random.Random(SPLIT_SEED)
    dev_ids: set[int] = set()
    for passage, size in DEV_PER_PASSAGE.items():
        ids = [s.id for s in sentences if s.passage == passage]
        dev_ids.update(rng.sample(ids, size))
    dev = [s for s in sentences if s.id in dev_ids]
    test = [s for s in sentences if s.id not in dev_ids]
    return dev, test
