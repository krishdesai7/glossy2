"""Command line interface."""

import argparse
import sys
from collections import Counter
from pathlib import Path

from glossy2.analyze import Context, analyze_sentence
from glossy2.dictionary import Dictionary
from glossy2.gold import load_gold, split_sentences
from glossy2.hints import HintError, parse_line
from glossy2.llm import MissingKeyError
from glossy2.memory import Memory
from glossy2.models import GoldSentence
from glossy2.normalize import normalize
from glossy2.render import render_gb4e, render_text
from glossy2.ycoe import YcoeIndex

OHTHERE_TEX = Path("corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex")
TINA_CORRECTIONS = Path("corpus/ohthere/tina-corrections.jsonl")
YCOE_POS = Path("corpus/ycoe-archive/ycoe/pos")
# This YCOE file contains the Ohthere text, so it can't be used when testing on Ohthere.
OHTHERE_YCOE_FILE = "coorosiu.o2.pos"
MEMORY_PATH = Path("memory/ang.jsonl")


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


def _gloss_context(memory: Memory) -> Context:
    dev, _ = split_sentences(load_gold(OHTHERE_TEX, TINA_CORRECTIONS))
    return Context(YcoeIndex.load(YCOE_POS), Dictionary.open(), dev, memory=memory)


def _read_lines(args: argparse.Namespace) -> list[str]:
    return args.file.read_text(encoding="utf-8").splitlines() if args.file else [args.text]


def _gloss(args: argparse.Namespace) -> int:
    try:
        sentences = [words for line in _read_lines(args) if (words := parse_line(line))]
    except HintError as error:
        print(f"Couldn't read the hint on {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Couldn't read {args.file}: {error.strerror}", file=sys.stderr)
        return 2
    memory = Memory.load(MEMORY_PATH)
    ctx = _gloss_context(memory)
    render = render_gb4e if args.format == "gb4e" else render_text
    try:
        for index, words in enumerate(sentences):
            analyses = analyze_sentence(words, ctx)
            if index:
                print()
            print(render(analyses))
            if not args.no_record:
                memory.record_machine(analyses, "gloss", MEMORY_PATH)
    except MissingKeyError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


def _remember(args: argparse.Namespace) -> int:
    corrections = TINA_CORRECTIONS if args.path == OHTHERE_TEX else None
    sentences = load_gold(args.path, corrections)
    Memory.load(MEMORY_PATH).add_human(sentences, args.name, MEMORY_PATH)
    tokens = [token.form for sentence in sentences for token in sentence.tokens]
    print(f"Remembered {len(tokens)} tokens ({len({normalize(f) for f in tokens})} forms) from {args.name}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="glossy2", description="Complete Old English glosses.")
    commands = parser.add_subparsers(dest="command", required=True)
    coverage = commands.add_parser("coverage", help="Check how many answer-key words the sources know.")
    coverage.add_argument("--tex", type=Path, default=OHTHERE_TEX)
    coverage.set_defaults(run=_coverage)

    gloss = commands.add_parser("gloss", help="Complete the gloss for one or more sentences.")
    gloss.add_argument("text", nargs="?", help="A sentence, optionally with hints like lande[noun,neuter].")
    gloss.add_argument("--file", type=Path, help="Read one sentence per line from a file.")
    gloss.add_argument("--format", choices=["text", "gb4e"], default="text")
    gloss.add_argument("--no-record", action="store_true", help="Don't store this output in memory.")
    gloss.set_defaults(run=_gloss)

    remember = commands.add_parser("remember", help="Add a human-approved gb4e file to memory.")
    remember.add_argument("path", type=Path)
    remember.add_argument("--name", required=True, help="Name of this source.")
    remember.set_defaults(run=_remember)

    args = parser.parse_args(argv)
    if args.command == "gloss" and not args.text and not args.file:
        gloss.error("give a sentence or --file")
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
