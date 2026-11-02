"""Command line interface."""

import argparse
import json
import sys
from dataclasses import asdict
from collections import Counter
from pathlib import Path

from glossy2.analyze import Context, analyze_sentence, build_messages
from glossy2.baselines import BaselineUnavailable, cltk_analyses, ycoe_analyses
from glossy2.dictionary import Dictionary
from glossy2.evaluate import LEVELS, TokenScore, aggregate, make_inputs, run_level, score_sentence
from glossy2.gold import load_corrections, load_gold, split_sentences
from glossy2.hints import HintError, parse_line
from glossy2.llm import MissingKeyError, complete_json, current_model, estimate_cost, usage_totals
from glossy2.memory import Memory
from glossy2.models import GoldSentence
from glossy2.normalize import normalize
from glossy2.render import render_gb4e, render_text
from glossy2.report import memory_effect, render_report
from glossy2.ycoe import YcoeIndex

OHTHERE_TEX = Path("corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex")
TINA_CORRECTIONS = Path("corpus/ohthere/tina-corrections.jsonl")
YCOE_POS = Path("corpus/ycoe-archive/ycoe/pos")
# This YCOE file contains the Ohthere text, so it can't be used when testing on Ohthere.
OHTHERE_YCOE_FILE = "coorosiu.o2.pos"
MEMORY_PATH = Path("memory/ang.jsonl")
REPORTS_DIR = Path("reports")
OUTPUT_TOKENS_PER_WORD = 90
_complete = complete_json


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


def _eval_sources(exclude: set[str]) -> tuple[YcoeIndex, Dictionary]:
    return YcoeIndex.load(YCOE_POS, exclude=exclude), Dictionary.open()


def _eval_memory(name: str, dev: list[GoldSentence]) -> Memory | None:
    """Built for this run only and never saved."""
    if name == "none":
        return None
    if name == "dev":
        return Memory.from_gold(dev, "ohthere-dev")
    return Memory.from_gold(load_gold(OHTHERE_TEX, TINA_CORRECTIONS), "ohthere")


def _cltk_baseline(sentences, corrections, dictionary):
    try:
        scores = []
        for sentence in sentences:
            _, withheld = make_inputs(sentence, "none")
            scores += score_sentence(sentence, cltk_analyses(sentence), withheld, corrections, dictionary)
        return scores, None
    except BaselineUnavailable as error:
        return None, str(error)


def _estimate(sentences, levels, ctx) -> tuple[int, int]:
    prompt_tokens = completion_tokens = 0
    for sentence in sentences:
        words, _ = make_inputs(sentence, "none")
        characters = sum(len(m["content"]) for m in build_messages(words, ctx))
        prompt_tokens += characters // 4 * len(levels)
        completion_tokens += len(words) * OUTPUT_TOKENS_PER_WORD * len(levels)
    return prompt_tokens, completion_tokens


def _score_from_json(row: dict) -> TokenScore:
    return TokenScore(**row)


def _load_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs": {}, "baselines": {}, "notes": {}}


def _save_results(path: Path, results: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")


def _print_summary(level: str, memory: str, scores: list[TokenScore]) -> None:
    s = aggregate(scores)
    show = lambda t: f"{100 * t[0] / t[1]:.1f}% ({t[0]}/{t[1]})" if t[1] else "n/a"
    print(
        f"hints={level} memory={memory}: exact {show(s.exact)}, segmentation {show(s.segmentation)}, "
        f"meaning {show(s.meaning_exact)} / any sense {show(s.meaning_sense)}, lemma {show(s.lemma)}, "
        f"unflagged {show(s.unflagged)}, flagged {show(s.flagged)}, failed {s.failed}"
    )


def _eval(args: argparse.Namespace) -> int:
    if args.gold and not args.name:
        print("--gold needs --name, which names the report.", file=sys.stderr)
        return 2
    ohthere = load_gold(OHTHERE_TEX, TINA_CORRECTIONS)
    dev, test = split_sentences(ohthere)
    if args.gold:
        sentences, corrections, split = load_gold(args.gold), {}, "test"
        exclude = set(args.exclude_ycoe)
        name, report_name = args.name, f"eval-{args.name}"
    else:
        split = args.split
        sentences = dev if split == "dev" else test
        corrections = load_corrections(TINA_CORRECTIONS)
        exclude = {OHTHERE_YCOE_FILE}
        name, report_name = "Ohthere and Wulfstan", "eval-dev" if split == "dev" else "eval"
        leaks = args.memory == "ohthere" or (args.memory == "dev" and split == "dev")
        if leaks:
            print(f"--memory {args.memory} would contain sentences being scored here.", file=sys.stderr)
            return 2
    levels = LEVELS if args.hints == "all" else [args.hints]
    selected = sentences[: args.limit] if args.limit else sentences
    ycoe, dictionary = _eval_sources(exclude)
    memory = _eval_memory(args.memory, dev)
    ctx = Context(ycoe, dictionary, dev, _complete, memory)
    prompt_tokens, completion_tokens = _estimate(selected, levels, ctx)
    cost = estimate_cost(prompt_tokens, completion_tokens, current_model())
    print(
        f"{len(selected)} sentences, {len(levels)} hint level(s), {current_model()}: about {prompt_tokens} input "
        f"tokens and {completion_tokens} output tokens, roughly ${cost:.2f} before caching."
    )
    trial = args.limit and split == "dev" and not args.gold
    if not args.yes and not trial:
        if input("Go ahead? [y/N] ").strip().lower() != "y":
            print("Stopped. Nothing was sent.")
            return 0
    before = usage_totals()
    new_runs = []
    try:
        for level in levels:
            scores = run_level(selected, level, ctx, corrections)
            _print_summary(level, args.memory, scores)
            effect = memory_effect(scores, memory) if memory else None
            new_runs.append((level, scores, effect))
    except MissingKeyError as error:
        print(error, file=sys.stderr)
        return 2
    used = usage_totals()
    spent_in, spent_out = used[0] - before[0], used[1] - before[1]
    spent = estimate_cost(spent_in, spent_out, current_model())
    print(f"This run used {spent_in} input and {spent_out} output tokens, at most ${spent:.2f}.")
    if args.limit:
        return 0
    json_path = REPORTS_DIR / f"{report_name}.json"
    results = _load_results(json_path)
    for level, scores, effect in new_runs:
        results["runs"][f"{level}|{args.memory}"] = {
            "level": level, "memory": args.memory, "effect": effect, "scores": [asdict(s) for s in scores],
        }
    results["spent"] = results.get("spent", 0) + (spent if spent == spent else 0)
    if "YCOE most-common tag" not in results["baselines"]:
        rows = []
        for sentence in sentences:
            _, withheld = make_inputs(sentence, "none")
            rows += score_sentence(sentence, ycoe_analyses(sentence, ycoe), withheld, corrections, dictionary)
        results["baselines"]["YCOE most-common tag"] = [asdict(s) for s in rows]
    if "CLTK Stanza" not in results["baselines"]:
        rows, note = _cltk_baseline(sentences, corrections, dictionary)
        if rows is None:
            results["notes"]["CLTK Stanza"] = note
        else:
            results["baselines"]["CLTK Stanza"] = [asdict(s) for s in rows]
            results["notes"].pop("CLTK Stanza", None)
    _save_results(json_path, results)
    runs = [
        {**run, "scores": [_score_from_json(row) for row in run["scores"]]}
        for run in sorted(results["runs"].values(), key=lambda r: (LEVELS.index(r["level"]), r["memory"]))
    ]
    baselines = {key: [_score_from_json(row) for row in rows] for key, rows in results["baselines"].items()}
    text = render_report(
        name=name, split=split, sentences=len(sentences), runs=runs, baselines=baselines,
        baseline_notes=results["notes"], cost_note=f"Model {current_model()}, about ${results['spent']:.2f} at list price",
    )
    (REPORTS_DIR / f"{report_name}.md").write_text(text, encoding="utf-8")
    print(f"Report: {REPORTS_DIR / f'{report_name}.md'}")
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

    evaluate = commands.add_parser("eval", help="Score the tool against human glosses.")
    evaluate.add_argument("--hints", choices=[*LEVELS, "all"], required=True)
    evaluate.add_argument("--split", choices=["dev", "test"], default="dev")
    evaluate.add_argument("--limit", type=int, help="Try this many sentences. Writes no report.")
    evaluate.add_argument("--yes", action="store_true", help="Don't ask before spending.")
    evaluate.add_argument("--gold", type=Path, help="Score a different human-glossed gb4e file.")
    evaluate.add_argument("--name", help="Name of the --gold text, used for its report.")
    evaluate.add_argument("--exclude-ycoe", action="append", default=[], metavar="FILE")
    evaluate.add_argument("--memory", choices=["none", "dev", "ohthere"], default="none")
    evaluate.set_defaults(run=_eval)

    args = parser.parse_args(argv)
    if args.command == "gloss" and not args.text and not args.file:
        gloss.error("give a sentence or --file")
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
