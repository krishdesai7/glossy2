# Old English glosser: proof-of-concept design

## Intent

Glossy is a website whose "automatic glossing" is hand-written lookup tables and suffix rules. Unknown
words become confident nouns, with Wiktionary links nobody checked.

This project is a small demo of what a well-designed glosser could
be. It is not a product. It should change his view of what is possible, and give him
evidence that he, as a domain expert, can judge. A website could come later and is
treated as decoration.

## What it does

A command-line tool takes Old English sentences with no gloss or a partial gloss, and
returns the completed interlinear gloss. Partial means per-word and can be half-done:
"noun, neuter" or a stem meaning like `lord`, with the tool filling in the rest.

## Goals

1. Complete glosses from no input or partial input, in a format the friend can read
   at a glance, such as `sǣ-d-e` / `say-PST-IND.3SG`.
2. Treat hints as fixed facts. The tool never overrides them. If a hint conflicts
   with what the tool thinks is possible, it says so.
3. Mark what it is unsure of, with a reason, instead of guessing confidently.
4. Only show Wiktionary links for entries known to exist.
5. Report honest accuracy against his own work, including how accuracy changes with
   more hints.

## Non-goals

- Website, editor, drafts, PDF or CMS.
- Anything from the old Glossy codebase other than the data listed below.
- Verse-specific handling, dialect analysis or manuscript variants.
- Comparing LLM providers. Moonshot is used unless results force a rethink.
- Polish beyond what the demo needs: packaging, configuration systems, plugins.

## Anti-goals: a failure even if it runs

- Wrong answers with no flag. This was the old engine's worst fault.
- Silently changing a hint.
- An invented lemma or a link to a page that doesn't exist.
- Inflated scores from testing on data the tool has already seen.
- Presenting agent-written or generated data human work.

## Data

All paths are relative to the repo root.

**`corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex`** is human work and the main
answer key: 75 sentences, 1,716 tokens, 636 of them hyphenated, in `gb4e` format, with
translations and 341 distinct lexical glosses. It contains no lemmas or
parts of speech. Tags used include `SG PL NOM ACC GEN DAT INS M F N 3SG 3PL 1PL PRS PST
IND SJV INF DEF DEM DIST PROX INDF DET REL STR WK CMP COMP SUP ADV ADJ PFX PART NEG HAB
THM AGT NMLZ PASS`. Note that `COMP` means complementizer and `CMP` means comparative,
though older glosses use `comp` for comparative. Known quirks are one `have--prs.ind.pl`
and one `dat,pl`.

**The TinaCMS corrections** are also human work, and they are
reliable. They live in the git history of the sibling repo `../glossy`, in
`content/texts/ohthere.json`, commits `d1ef57a ea2abff f5a7dcf 72dcd3c db12d79 17db08c`.
Compare each commit with its parent and keep only the fields it changed: about 21
lemmas, 30 parts of speech, 32 URLs, 50 feature values and 9 glosses. Ignore churn
such as an empty `features` becoming missing, and bulk `review/notes` changes. The
rest of that JSON is lemmatizer output and must never be used as an answer. Extract
the corrections once into a committed file, `corpus/ohthere/tina-corrections.jsonl`.

**`corpus/ycoe-archive/ycoe/pos/*.pos`** is YCOE, already unzipped: 1.45M tokens and
about 85,000 forms, tagged for part of speech, case (`N^D`) and verb mood or tense
(`VBDI`). It has no lemmas, meanings, number or gender. It writes `+t +d +a` for
`þ ð æ` and has no macrons. Its licence allows private scholarly research only, bans
redistribution and requires acknowledgement. So it stays git-ignored, the README
acknowledges it, and only per-word tag lists go to the LLM, never running passages.

**Dictionary:** Wiktionary's Old English data via kaikki.org (wiktextract), about
66,000 word forms in a 134 MB JSONL file. The page marks that file as deprecated, so
find its current replacement at build time. Git-ignore the download. Cite wiktextract
and credit Wiktionary (CC BY-SA).

## How it works

```text
input sentence + hints
   -> normalise spelling for lookup
   -> candidates: YCOE tags seen for this form; dictionary entries for this form
   -> LLM chooses in sentence context, hints fixed, returns segments, gloss, lemma
   -> checks: hints kept? segments rejoin to the word? lemma in dictionary?
              tag among those YCOE has seen?
   -> interlinear gloss with flags and reasons
```

**Lookup normalisation:** map YCOE's `+` codes, merge `þ/ð`, strip macrons and dots,
and fold case. This is for matching only. Output keeps the user's spelling.

**Word record:** each word holds `form`, `segments` (each with `form` and `gloss`),
`lemma`, `upos`, `feats`, `meaning`, `wiktionary_url` and `flags`. `feats` uses
Universal Dependencies names, plus extensions for what UD can't express (`HAB`, `THM`,
`AGT`, `NMLZ`, `PFX`). The extensions matter: UD alone can't regenerate his glosses.
`feats` holds the full analysis, while the printed gloss marks only what he'd normally
mark, learned from the worked examples, so output can match his gloss exactly.

**Build order:** before any LLM work, run the dictionary lookup and flag rules over the
Ohthere forms and report the coverage and flag rate. If most words would be flagged, or
the dictionary can't supply lemmas, stop and rethink that part rather than building on it.

**Flags are based on evidence, not on the model's own confidence**, which is a poor
guide. A word is flagged, with its reason, when:

- the form isn't in YCOE or the dictionary,
- the chosen tag isn't one YCOE has seen for that form,
- the lemma isn't in the dictionary,
- a hint conflicts with the model's preferred analysis,
- segments don't rejoin to the original word after one retry,
- the form is ambiguous and the sentence doesn't settle it, by the model's own report.

A flagged word's URL is omitted when its lemma isn't in the dictionary. Links are
built only from dictionary entries.

**LLM:** Moonshot, through its OpenAI-compatible API, with the key in `.env` as
`MOONSHOT_API_KEY`. Don't use CLTK's LLM backend: it has no Moonshot option, calls the
OpenAI Responses API, and its prompt forbids leaving fields blank. Keep the provider
behind one small function so it can be swapped. Cache every response on disk by prompt
hash, so repeat runs are free and reproducible. Use the smallest amount of sentence
context that works, sentence at a time.

**CLTK** is a comparison baseline only, through its Stanza backend.

## Command line

```shell
glossy2 gloss "Hē cwæð þæt hē būde on þǣm lande."
glossy2 gloss --file sentences.txt
glossy2 eval --hints none|half|stem|stem+half [--split dev|test] [--limit N]
```

Hints go in brackets straight after a word, comma-separated. Known labels such as
`noun`, `neuter` and `dat` become features. Anything else is the stem meaning. A hyphen
in the word fixes the segmentation:

```text
Hē cwæð þæt hē būde on þǣm lande[noun,neuter] ...
Hē sǣ-d-e his hlāford-e[lord] ...
```

Output shows the aligned Old English and gloss lines, the flags with reasons, then a
per-word table with lemma and link. `--format gb4e` prints LaTeX he can paste.

## Evaluation

`glossy2 eval` is the part that makes the demo persuasive.

- **Answer key:** `.tex`, with Tina gloss corrections applied.
- **No leakage:** exclude `coorosiu.o2.pos` from YCOE during eval, because it contains
  the Ohthere text. Say in the report that the model may also remember this famous text
  from training, so these scores may run high on unseen text.
- **Dev and test split:** fix 15 of the 75 sentences as `dev`, chosen once with a fixed
  seed, for tuning the prompt and supplying worked examples of his conventions. The
  other 60 are `test`, and are only run to produce reported numbers. Examples shown to
  the model come only from `dev`, and the report says so. Keep Ohthere's two passages
  represented in both.
- **Hint levels:** all hints come from human glosses, so nothing machine-made is fed in as
  fact. `none`; `half` (a random half of each word's marked features, fixed seed);
  `stem` (stem meaning given, grammar withheld); `stem+half`. Part-of-speech hints work
  in `gloss`, but aren't an eval level: his `.tex` has no parts of speech, and only about
  30 of his Tina edits do.
- **What counts as right:** score only what the hints withheld, so hints echoed back
  can't raise a score. A feature is scored only where he marked it, in his gloss or his
  Tina corrections. An extra feature he didn't mark, such as gender on `land-DAT.SG`, is
  ignored rather than counted wrong, and the report says that this measures recall of
  what he marked.
- **Scores, each split by hint level:** exact match to his whole gloss, which is the
  number users will care about most; segmentation; each grammatical feature; lexical meaning,
  as exact match and as match against any dictionary sense, since `say` versus `speak`
  isn't really an error; lemma, on Tina corrections only, which is a small sample
  and must be labelled so.
- **Flag quality:** accuracy on flagged versus unflagged words. Flags only earn trust if
  unflagged words are clearly more accurate.
- **Baselines:** CLTK Stanza, on the features and lemmas it produces; most-common YCOE
  tag per form. The old lemmatizer goes in as a baseline only if it's cheap to run,
  noting that its tables were built around this same text.

Output is a markdown report at `reports/eval.md`, including a sample of real errors for
users to read. No accuracy target is set in advance: an honest number is the deliverable.

## Constraints

- Python via uv, in this repo. Requires Python 3.15, as already set up.
- CLI only, and it has to run on the user's Mac.
- Demo-sized LLM spend: Moonshot credits are already paid for. Print the token count
  and an estimated cost before a full eval, and test with `--limit` first.
- Never commit the API key, YCOE or the dictionary download.

## Decisions

**Krish's:** command-line only; no gloss or partial per-word input; agreed evidence-based
flags, hints as fixed facts and tool-side segmentation; using his friend's format isn't
required if another makes life easier; Moonshot first; friend's Tina edits are reliable.

**Claude's, to check:** UD names plus extensions internally, with his Leipzig format as
output; the bracket hint syntax; the four hint levels, with no part-of-speech level; the
15/60 dev and test split, with his dev sentences used as examples; scoring only withheld
features he marked; CLTK as a baseline rather than a foundation; excluding all of
`coorosiu.o2` in eval; flags from evidence rather than model confidence; Wiktionary via
kaikki as the dictionary, with an early coverage check.

## Left to the builder

Module layout, CLI library, test approach, prompt wording, JSON schema for the LLM, the
Moonshot model, batching and retries, the mapping table between his tags and UD, how
`dat,pl` and similar quirks are parsed, and moving heavy CLTK dependencies into an
optional group.
