"""The evaluation report, written for someone who glosses rather than codes."""

import random

from glossy2.evaluate import Tally, TokenScore, aggregate
from glossy2.memory import Memory
from glossy2.normalize import normalize

ERROR_SAMPLE_SIZE = 25
_CAVEATS = """## Read this first

- **What was tuned on what.** The prompt was tuned on 15 sentences (`dev`), which also supply the model's worked examples. The numbers below come from text that was not used for either, unless this report says it is the `dev` report.
- **The model may remember this text.** Ohthere is famous, so the model may have seen it in training. Scores here may run higher than on text it has never seen.
- **YCOE's copy was removed.** YCOE's Orosius contains this passage, so that file was left out of the evidence.
- **What counts as right.** Only what the hints withheld is scored, so a hint echoed back can't raise a score. A feature counts only where the human marked it, so these numbers show recall of what the human marked. An extra feature the human left unmarked is ignored rather than counted wrong.
- **Lemma numbers are a small, harder-than-average sample.** They use only the human Tina corrections, which are mostly words the old engine got wrong.
- **Settings.** Model reasoning was turned off to keep cost and time down, and Moonshot doesn't allow a fixed temperature on this model. Cached responses make a rerun reproducible, but a rerun without the cache could differ slightly.
- **Sources.** York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE), used under its conditions for scholarly research. Dictionary data from Wiktionary (CC BY-SA) via wiktextract and kaikki.org.
"""


def _percent(tally: Tally) -> str:
    right, total = tally
    return f"{100 * right / total:.1f}% ({right}/{total})" if total else "n/a"


def memory_effect(scores: list[TokenScore], memory: Memory) -> dict:
    in_memory, not_in_memory = [], []
    wrong_top = misled = 0
    for score in scores:
        readings = memory.human(score.form.replace("-", ""))
        if not readings:
            not_in_memory.append(score.exact)
            continue
        in_memory.append(score.exact)
        top = readings[0][0]
        if top != score.gold_gloss:
            wrong_top += 1
            misled += score.predicted_gloss.rstrip("?") == top
    tally = lambda values: (sum(v for v in values if v), sum(v is not None for v in values))
    return {
        "in_memory": tally(in_memory), "not_in_memory": tally(not_in_memory),
        "wrong_top": wrong_top, "misled": misled,
    }


def _accuracy_table(runs: list[dict]) -> list[str]:
    lines = [
        "| Hints | Memory | Whole gloss exact | Segmentation | Meaning exact | Meaning (any dictionary sense) | Lemma |",
        "|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        s = aggregate(run["scores"])
        lines.append(
            f"| {run['level']} | {run['memory']} | {_percent(s.exact)} | {_percent(s.segmentation)} | "
            f"{_percent(s.meaning_exact)} | {_percent(s.meaning_sense)} | {_percent(s.lemma)} |"
        )
    return lines


def _feature_table(runs: list[dict], baselines: dict[str, list[TokenScore]]) -> list[str]:
    columns = [(f"{run['level']} / memory {run['memory']}", aggregate(run["scores"])) for run in runs]
    columns += [(name, aggregate(scores)) for name, scores in baselines.items()]
    keys = sorted({key for _, s in columns for key in s.features})
    lines = ["| Feature | " + " | ".join(name for name, _ in columns) + " |", "|---" * (len(columns) + 1) + "|"]
    for key in keys:
        cells = [_percent(s.features.get(key, (0, 0))) for _, s in columns]
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    return lines


def _flag_table(runs: list[dict]) -> list[str]:
    lines = ["| Hints | Memory | Unflagged, exact | Flagged, exact |", "|---|---|---|---|"]
    for run in runs:
        s = aggregate(run["scores"])
        lines.append(f"| {run['level']} | {run['memory']} | {_percent(s.unflagged)} | {_percent(s.flagged)} |")
    return lines


def _baseline_table(baselines: dict[str, list[TokenScore]], notes: dict[str, str]) -> list[str]:
    lines = ["| Baseline | Whole gloss exact | Segmentation | Lemma |", "|---|---|---|---|"]
    for name, scores in baselines.items():
        lines.append(f"| {name} | n/a | n/a | {_percent(aggregate(scores).lemma)} |")
    lines.append("")
    lines.append("Neither baseline produces glosses or morpheme splits. Compare them on the features above.")
    lines.extend(f"\n{name}: {note}." for name, note in notes.items())
    return lines


def _memory_section(runs: list[dict]) -> list[str]:
    rows = [run for run in runs if run.get("effect")]
    if not rows:
        return []
    lines = [
        "## Memory: did earlier glosses help?", "",
        "Accuracy on words already in memory against words that aren't. The last column is the cost: where the remembered reading was wrong for this word, how often the model repeated it.", "",
        "| Hints | Memory | In memory, exact | Not in memory, exact | Wrong remembered reading | Model misled |",
        "|---|---|---|---|---|---|",
    ]
    for run in rows:
        e = run["effect"]
        lines.append(
            f"| {run['level']} | {run['memory']} | {_percent(tuple(e['in_memory']))} | "
            f"{_percent(tuple(e['not_in_memory']))} | {e['wrong_top']} | {e['misled']} |"
        )
    return lines + [""]


def _error_sample(runs: list[dict]) -> list[str]:
    errors = [score for score in runs[0]["scores"] if score.exact is False]
    sample = random.Random(1729).sample(errors, min(ERROR_SAMPLE_SIZE, len(errors)))
    lines = [
        f"From the `{runs[0]['level']}` run. A `?` on a gloss means the tool flagged it.", "",
        "| Word | Human gloss | Tool's gloss |", "|---|---|---|",
    ]
    lines += [f"| {s.form} | {s.gold_gloss} | {s.predicted_gloss} |" for s in sorted(sample, key=lambda s: (s.sentence, s.token))]
    return lines


def render_report(*, name, split, sentences, runs, baselines, baseline_notes, cost_note) -> str:
    failed = sum(aggregate(run["scores"]).failed for run in runs)
    parts = [f"# Evaluation: {name}", "", f"Split: `{split}`. {sentences} sentences. {cost_note}.", ""]
    parts += [_CAVEATS, "## Accuracy by hint level", "", *_accuracy_table(runs), ""]
    parts += [f"{failed} token analyses failed outright (bad or missing model response). They count as wrong.", ""]
    parts += ["## Per feature", "", *_feature_table(runs, baselines), ""]
    parts += ["## Do flags mean anything?", "", "Flags only earn trust if unflagged words are clearly more accurate.", "", *_flag_table(runs), ""]
    parts += _memory_section(runs)
    parts += ["## Baselines", "", *_baseline_table(baselines, baseline_notes), ""]
    parts += ["## Sample of real errors", "", *_error_sample(runs), ""]
    return "\n".join(parts)
