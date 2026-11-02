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
- **What counts as right.** Words with nothing withheld aren't scored. A feature counts only where the human marked it, so these numbers show recall of what the human marked. An extra feature the human left unmarked is ignored rather than counted wrong. Per-feature and meaning scores really are limited to what was withheld. Whole-gloss scores compare the entire gloss, so a word with some features hinted can match partly because of those hints.
- **Lemma numbers are a small, harder-than-average sample.** They use only the human Tina corrections, which are mostly words the old engine got wrong.
- **Settings.** Model reasoning was turned off to keep cost and time down, and Moonshot doesn't allow a fixed temperature on this model. Cached responses make a rerun reproducible, but a rerun without the cache could differ slightly.
- **Sources.** York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE), used under its conditions for scholarly research. Dictionary data from Wiktionary (CC BY-SA) via wiktextract and kaikki.org.
"""


# Features each baseline can produce at all. Anything else is "n/a", not a failure.
_BASELINE_FEATURES = {
    "YCOE most-common tag": {"Case", "Mood", "Tense", "VerbForm", "Degree", "Polarity"},
    "CLTK Stanza": {"Case", "Number", "Gender", "Person", "Tense", "Mood", "VerbForm", "Degree", "Polarity", "PronType", "Definite", "Voice"},
}
_NO_LEMMA_BASELINES = {"YCOE most-common tag"}


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
        "| Hints | Memory | Words with grammar, same words at every level | Whole gloss exact, withheld only | Segmentation | Meaning exact | Meaning (any dictionary sense) | Lemma |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        s = aggregate(run["scores"])
        lines.append(
            f"| {run['level']} | {run['memory']} | {_percent(s.exact_with_grammar)} | {_percent(s.exact)} | {_percent(s.segmentation)} | "
            f"{_percent(s.meaning_exact)} | {_percent(s.meaning_sense)} | {_percent(s.lemma)} |"
        )
    return lines


def _feature_table(runs: list[dict], baselines: dict[str, list[TokenScore]]) -> list[str]:
    columns = [(f"{run['level']} / memory {run['memory']}", aggregate(run["scores"]), None) for run in runs]
    columns += [(name, aggregate(scores), _BASELINE_FEATURES.get(name)) for name, scores in baselines.items()]
    keys = sorted({key for _, s, _ in columns for key in s.features})
    lines = ["| Feature | " + " | ".join(name for name, _, _ in columns) + " |", "|---" * (len(columns) + 1) + "|"]
    for key in keys:
        cells = [
            "n/a" if produces is not None and key not in produces else _percent(s.features.get(key, (0, 0)))
            for _, s, produces in columns
        ]
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
        lemma = "n/a" if name in _NO_LEMMA_BASELINES else _percent(aggregate(scores).lemma)
        lines.append(f"| {name} | n/a | n/a | {lemma} |")
    lines.append("")
    lines.append("Neither baseline produces glosses or morpheme splits. Compare them on the features above, where `n/a` means the baseline can't produce that feature at all.")
    lines.extend(f"\n{name}: {note}." for name, note in notes.items())
    return lines


def _memory_section(runs: list[dict]) -> list[str]:
    rows = [run for run in runs if run.get("effect")]
    if not rows:
        return []
    lines = [
        "## Words in memory against words not in memory", "",
        "This is not a measure of memory's effect. Words in memory are mostly frequent function words, which are easier anyway, and the comparison run with no memory wasn't run. The last column does show a real cost: where the remembered reading was wrong for this word, how often the model repeated it.", "",
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


def _unflagged_errors(runs: list[dict]) -> list[str]:
    lines = []
    for run in runs:
        wrong = [score for score in run["scores"] if score.exact is False]
        unflagged = sum(not score.flagged for score in wrong)
        lines.append(f"At `{run['level']}`, {unflagged} of the {len(wrong)} wrong glosses carried no flag.")
    return lines + ["", "No flag doesn't mean correct. Some of these are convention differences rather than wrong analyses, which the error sample below shows.", ""]


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
    caveats = _CAVEATS
    if any(run["memory"] != "none" for run in runs):
        caveats += "- **Memory.** The worked-example sentences were also supplied as memory in runs marked `dev`. No scored sentence was in memory.\n"
    parts += [caveats, "## Accuracy by hint level", "", *_accuracy_table(runs), ""]
    parts += ["Use the first accuracy column to compare hint levels, because it scores the same words each time. The second drops words with nothing withheld, so its word set changes per level and easy function words leave it at `stem`. In both, a word can match partly because of its hints, so don't read the rise across levels as pure gain.", ""]
    parts += [f"{failed} token analyses failed outright (bad or missing model response). They count as wrong.", ""]
    parts += ["## Per feature", "", *_feature_table(runs, baselines), ""]
    parts += ["## Do flags mean anything?", "", "Flags only earn trust if unflagged words are clearly more accurate.", "", *_flag_table(runs), ""]
    parts += _unflagged_errors(runs)
    parts += _memory_section(runs)
    parts += ["## Baselines", "", *_baseline_table(baselines, baseline_notes), ""]
    parts += ["## Sample of real errors", "", *_error_sample(runs), ""]
    return "\n".join(parts)
