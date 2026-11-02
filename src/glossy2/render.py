"""Terminal and gb4e output."""

import os
import re
import shutil
import unicodedata

from glossy2.models import WordAnalysis
from glossy2.tags import HUMAN_TO_FEATS, render_gloss

_LATEX_SPECIAL = re.compile(r"([&%$#_{}])")


def display_width(text: str) -> int:
    return sum(1 for c in unicodedata.normalize("NFC", text) if not unicodedata.combining(c))


def _pad(text: str, width: int) -> str:
    return text + " " * (width - display_width(text))


def _display_form(analysis: WordAnalysis) -> str:
    joined = "-".join(s.form for s in analysis.segments) if analysis.segments else analysis.form
    return analysis.lead + joined + analysis.punct


def _width() -> int:
    if columns := os.environ.get("COLUMNS"):
        return int(columns)
    return shutil.get_terminal_size((100, 24)).columns


def _aligned_lines(analyses: list[WordAnalysis]) -> list[str]:
    """Pairs of Old English and gloss lines, wrapped by whole word blocks."""
    limit = _width()
    lines: list[str] = []
    top, bottom, used = [], [], 0
    for analysis in analyses:
        form, gloss = _display_form(analysis), render_gloss(analysis)
        width = max(display_width(form), display_width(gloss)) + 1
        if top and used + width > limit:
            lines += ["".join(top).rstrip(), "".join(bottom).rstrip()]
            top, bottom, used = [], [], 0
        top.append(_pad(form, width))
        bottom.append(_pad(gloss, width))
        used += width
    if top:
        lines += ["".join(top).rstrip(), "".join(bottom).rstrip()]
    return lines


def render_text(analyses: list[WordAnalysis]) -> str:
    sections = ["\n".join(_aligned_lines(analyses))]
    flags = [f"  {a.form}: {flag.detail}" for a in analyses for flag in a.flags]
    if flags:
        sections.append("Flagged (check these):\n" + "\n".join(flags))
    rows = [
        (a.form, a.lemma or "-", a.upos or "-", a.wiktionary_url or "-")
        for a in analyses
        if any(c.isalpha() for c in a.form)
    ]
    widths = [max(display_width(row[i]) for row in rows) for i in range(3)] if rows else [0, 0, 0]
    table = [
        "  ".join(_pad(cell, width) for cell, width in zip(row[:3], widths)) + "  " + row[3]
        for row in rows
    ]
    sections.append("\n".join(table))
    return "\n\n".join(sections)


def _escape(text: str) -> str:
    return _LATEX_SPECIAL.sub(r"\\\1", text)


def _gloss_to_tex(gloss: str) -> str:
    marker = "?" if gloss.endswith("?") and gloss != "???" else ""
    body = gloss[: -len(marker)] if marker else gloss
    parts = []
    for part in body.split("-"):
        pieces = part.split(".")
        tex = []
        run: list[str] = []
        for piece in pieces:
            if piece in HUMAN_TO_FEATS:
                run.append(piece.lower())
                continue
            if run:
                tex.append(f"\\textsc{{{'.'.join(run)}}}")
                run = []
            tex.append(_escape(piece))
        if run:
            tex.append(f"\\textsc{{{'.'.join(run)}}}")
        parts.append(".".join(tex))
    tex = "-".join(parts) + marker
    # gb4e aligns on spaces, so a gloss of several words has to stay one group.
    return f"{{{tex}}}" if " " in body else tex


def render_gb4e(analyses: list[WordAnalysis], translation: str = "") -> str:
    forms = " ".join(_escape(_display_form(a)) for a in analyses)
    glosses = " ".join(_gloss_to_tex(render_gloss(a)) for a in analyses)
    translated = f"`{_escape(translation)}'" if translation else "{}"
    return f"\\ex{{\\gll {forms}\\\\\n{glosses}\\\\\n\\glt {translated}}}"
