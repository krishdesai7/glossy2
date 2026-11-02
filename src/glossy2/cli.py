"""Command line interface."""

import argparse
import sys
from collections import Counter
from pathlib import Path

from glossy2.dictionary import Dictionary
from glossy2.gold import load_gold
from glossy2.models import GoldSentence
from glossy2.normalize import normalize
from glossy2.ycoe import YcoeIndex

OHTHERE_TEX = Path("corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex")
TINA_CORRECTIONS = Path("corpus/ohthere/tina-corrections.jsonl")
YCOE_POS = Path("corpus/ycoe-archive/ycoe/pos")
# This YCOE file contains the Ohthere text, so it can't be used when testing on Ohthere.
OHTHERE_YCOE_FILE = "coorosiu.o2.pos"


def coverage_stats(sentences: list[GoldSentence], ycoe: YcoeIndex, dictionary: Dictionary) -> dict:
    forms = [token.form for sentence in sentences for token in sentence.tokens]
    stats = Counter(tokens=len(forms))
    missing: Counter = Counter()
    for form in forms:
        in_ycoe = bool(ycoe.tags(form))
        entries = dictionary.lookup(form)
        stats["in_ycoe"] += in_ycoe
        stats["in_dictionary"] += bool(entries)
        stats["one_lemma"] += len({entry.lemma for entry in entries}) == 1
        if not in_ycoe and not entries:
            stats["in_neither"] += 1
            missing[normalize(form)] += 1
    return {**stats, "in_neither": stats["in_neither"], "top_missing": missing.most_common(20)}


def _coverage(args: argparse.Namespace) -> int:
    sentences = load_gold(args.tex)
    ycoe = YcoeIndex.load(YCOE_POS, exclude={OHTHERE_YCOE_FILE})
    stats = coverage_stats(sentences, ycoe, Dictionary.open())
    total = stats["tokens"]
    for label, key in [
        ("In YCOE", "in_ycoe"),
        ("In the dictionary", "in_dictionary"),
        ("In neither", "in_neither"),
        ("Exactly one candidate lemma", "one_lemma"),
    ]:
        print(f"{label}: {stats[key]} of {total} tokens ({100 * stats[key] / total:.1f}%)")
    print("Most frequent forms in neither:", stats["top_missing"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="glossy2", description="Complete Old English glosses.")
    commands = parser.add_subparsers(dest="command", required=True)
    coverage = commands.add_parser("coverage", help="Check how many answer-key words the sources know.")
    coverage.add_argument("--tex", type=Path, default=OHTHERE_TEX)
    coverage.set_defaults(run=_coverage)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
