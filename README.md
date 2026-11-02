# glossy2

A proof of concept for completing Old English interlinear glosses. Give it a sentence with no gloss, or with hints for some words, and it returns the finished gloss with anything it can't support flagged.

It isn't a product. It exists to show what a well-designed glosser could do, and to measure that against human glosses. See `reports/eval.md`.

## How it works

1. For each word, it looks up the readings YCOE has recorded for that spelling, and the Wiktionary entries for it.
2. A model chooses an analysis in the context of the sentence, treating your hints as fixed.
3. Plain code then checks the result: hints win, links come only from real dictionary entries, and anything unsupported gets a flag and a reason.

## Setup

You need [uv](https://docs.astral.sh/uv/) and a Moonshot API key.

```shell
uv sync --group dev
echo 'MOONSHOT_API_KEY=your-key-here' > .env
```

YCOE isn't in this repository, because its licence bans redistribution. Unzip your own copy so that `corpus/ycoe-archive/ycoe/pos/*.pos` exists. The Wiktionary data, about 134 MB, downloads on first use into `data/`.

To include the CLTK baseline in evaluations, also run `uv sync --group dev --extra baseline`.

## Commands

```shell
glossy2 gloss "Hē cwæð þæt hē būde on þǣm lande."
glossy2 gloss --file sentences.txt --format gb4e
glossy2 remember approved-text.tex --name my-text
glossy2 eval --hints none --limit 3
glossy2 coverage
```

Run them with `uv run` in front, such as `uv run glossy2 gloss "..."`, from the repository root.

### Hints

Put hints in brackets straight after a word, separated by commas. Grammar labels become fixed features, and anything else is the stem meaning. A hyphen in a word fixes how it splits.

```text
Hē cwæð þæt hē būde on þǣm lande[noun,neuter].
Hē sǣ-d-e his hlāford-e[lord].
```

Labels include `noun`, `verb`, `adj`, `neuter`, `dat`, `sg`, `pst`, `sjv` and `str`. A few English words could be either grammar or a meaning, such as `strong`, `first` and `present`. The tool won't guess: write `str` for the label or `=strong` for the meaning. A gloss ending in `?` was flagged, and the reason is listed beneath the sentence.

### Flags

| Flag | Meaning |
|---|---|
| `unknown_form` | The spelling isn't in YCOE or the dictionary |
| `tag_unseen` | YCOE has never recorded this spelling with this reading |
| `lemma_not_in_dictionary` | The lemma has no dictionary entry, so there's no link |
| `hint_conflict` | Your hint disagrees with the model's preferred reading, or with another hint. Your hint is kept |
| `segments_mismatch` | The model's morphemes didn't rejoin to the word |
| `ambiguous` | The model reports that the sentence doesn't settle the reading |
| `analysis_failed` | The model gave no usable answer for this sentence |

No flag doesn't mean correct: see the flag section of the report for how often unflagged words are wrong.

### Memory

`glossy2 remember` adds a human-approved `gb4e` file to `memory/ang.jsonl`. When a remembered spelling appears again, the model is told how it was glossed before, as a possible reading only.

`glossy2 gloss` also records its unflagged output there, marked as machine output, unless you pass `--no-record`. Machine output is never shown to the model, so that a wrong gloss can't keep confirming itself.

### Evaluating

`glossy2 eval` hides parts of a human gloss and scores what comes back. It shows an estimate and asks before spending, except on a trial of up to 3 tuning sentences at one hint level. Responses are cached in `.llm-cache/`, so repeat runs are free. `--cache-only` guarantees no paid calls: it stops rather than pay for a response that isn't cached. Use it to regenerate a report.

To test a new human-glossed `gb4e` file, use `glossy2 eval --hints all --gold path/to/text.tex --name text`.

## Credits

- **Ohthere and Wulfstan:** translated and glossed by Tyler Lemon. See `corpus/README.md` for what's included and why.
- **YCOE:** Taylor, Warner, Pintzuk and Beths, *The York-Toronto-Helsinki Parsed Corpus of Old English Prose*. Used under its conditions for private scholarly research. It isn't redistributed here and can't be used commercially.
- **Dictionary:** data from [Wiktionary](https://en.wiktionary.org/) (CC BY-SA), extracted by [wiktextract](https://github.com/tatuylonen/wiktextract) (Ylonen, LREC 2022) and distributed by [kaikki.org](https://kaikki.org/).
- **Baseline:** [CLTK](https://docs.cltk.org) with Stanza.
