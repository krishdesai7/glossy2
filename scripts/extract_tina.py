"""Extract the human TinaCMS corrections from the old Glossy repo's git history.

Usage: uv run python scripts/extract_tina.py ../glossy

Only fields changed by the listed commits are kept. Everything else in that JSON is
lemmatizer output and must not be treated as an answer.
"""

import collections
import json
import subprocess
import sys
from pathlib import Path

COMMITS = ["d1ef57a", "ea2abff", "f5a7dcf", "72dcd3c", "db12d79", "17db08c"]
JSON_PATH = "content/texts/ohthere.json"
OUTPUT = Path("corpus/ohthere/tina-corrections.jsonl")
ANALYSIS_FIELDS = ["lemma", "partOfSpeech", "wiktionaryUrl"]


def load(repo: str, commit: str) -> dict:
    shown = subprocess.run(
        ["git", "-C", repo, "show", f"{commit}:{JSON_PATH}"], capture_output=True, check=True
    )
    return json.loads(shown.stdout.decode("utf-8"))


def word_fields(word: dict) -> dict[str, object]:
    analysis = word.get("analysis") or {}
    fields: dict[str, object] = {"morphologicalGloss": word.get("morphologicalGloss")}
    fields.update({name: analysis.get(name) for name in ANALYSIS_FIELDS})
    for name, value in (analysis.get("features") or {}).items():
        if value not in (None, ""):
            fields[f"features.{name}"] = value
    return fields


def main(repo: str) -> None:
    final: dict[tuple[int, int, str], dict[str, object]] = {}
    for commit in COMMITS:
        before, after = load(repo, f"{commit}~1"), load(repo, commit)
        for sid, (old, new) in enumerate(zip(before["sentences"], after["sentences"])):
            for idx, (old_word, new_word) in enumerate(zip(old["words"], new["words"])):
                old_fields, new_fields = word_fields(old_word), word_fields(new_word)
                for name, value in new_fields.items():
                    if value not in (None, "") and old_fields.get(name) != value:
                        final[(sid, idx, name)] = {
                            "sentence": sid,
                            "token": idx,
                            "form": new_word.get("originalWord"),
                            "field": name,
                            "value": value,
                            "commit": commit,
                        }
    with OUTPUT.open("w", encoding="utf-8") as handle:
        for key in sorted(final):
            handle.write(json.dumps(final[key], ensure_ascii=False) + "\n")
    kinds = collections.Counter(k[2].split(".")[0] for k in final)
    print(f"{len(final)} corrections written to {OUTPUT}: {dict(kinds)}")


if __name__ == "__main__":
    main(sys.argv[1])
