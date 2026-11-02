"""Glosses seen before. Only human-approved ones ever reach the model, as a possibility.

Machine output is stored separately and never shown, so that one wrong gloss can't keep
confirming itself.
"""

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from glossy2.models import GoldSentence, WordAnalysis
from glossy2.normalize import normalize
from glossy2.tags import render_gloss


@dataclass
class MemoryEntry:
    form: str
    gloss: str
    lemma: str | None
    source: str
    tier: str


def _human_entries(sentences: list[GoldSentence], source: str) -> list[MemoryEntry]:
    return [
        MemoryEntry(token.form.replace("-", ""), token.gloss, None, source, "human")
        for sentence in sentences
        for token in sentence.tokens
        if any(character.isalpha() for character in token.form)
    ]


def _write(path: Path, entries: list[MemoryEntry]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(entry), ensure_ascii=False) for entry in entries]
    Path(path).write_text("".join(line + "\n" for line in lines), encoding="utf-8")


class Memory:
    def __init__(self, entries: list[MemoryEntry] | None = None):
        self._entries = entries or []

    @classmethod
    def load(cls, path: Path) -> "Memory":
        if not Path(path).exists():
            return cls()
        with Path(path).open(encoding="utf-8") as handle:
            return cls([MemoryEntry(**json.loads(line)) for line in handle if line.strip()])

    @classmethod
    def from_gold(cls, sentences: list[GoldSentence], source: str) -> "Memory":
        """In memory only, never saved. Used by evals."""
        return cls(_human_entries(sentences, source))

    def human(self, form: str) -> list[tuple[str, int, list[str]]]:
        """(gloss, count, sources) for a form, most frequent first."""
        wanted = normalize(form)
        counts: Counter = Counter()
        sources: dict[str, set[str]] = defaultdict(set)
        for entry in self._entries:
            if entry.tier == "human" and normalize(entry.form) == wanted:
                counts[entry.gloss] += 1
                sources[entry.gloss].add(entry.source)
        return [(gloss, count, sorted(sources[gloss])) for gloss, count in counts.most_common()]

    def add_human(self, sentences: list[GoldSentence], source: str, path: Path) -> None:
        """Replace anything from this source, so adding it twice doesn't double the counts."""
        kept = [e for e in self._entries if not (e.tier == "human" and e.source == source)]
        self._entries = kept + _human_entries(sentences, source)
        _write(path, self._entries)

    def record_machine(self, analyses: list[WordAnalysis], source: str, path: Path) -> None:
        new = [
            MemoryEntry(a.form.replace("-", ""), render_gloss(a), a.lemma, source, "machine")
            for a in analyses
            if not a.flags and any(character.isalpha() for character in a.form)
        ]
        if not new:
            return
        self._entries.extend(new)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a", encoding="utf-8") as handle:
            for entry in new:
                handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
