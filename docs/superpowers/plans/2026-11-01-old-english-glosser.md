# Old English Glosser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A CLI that completes Old English interlinear glosses from no input or partial input, flags what it can't support with evidence, and reports honest accuracy against human glosses.

**Architecture:** Each word gets candidates from YCOE (tags seen for the form) and Wiktionary (lemmas, senses, tagged inflection tables). An LLM picks an analysis per sentence with hints held fixed. Deterministic checks then enforce the hints, attach links only from dictionary entries, and raise flags. An eval harness hides parts of human glosses and scores the output.

**Tech Stack:** Python 3.15, uv, pytest, `openai` SDK against Moonshot, sqlite3 for the dictionary index, argparse. CLTK Stanza only as an optional baseline.

**Spec:** `docs/superpowers/specs/2026-11-01-old-english-glosser-design.md`

## Global Constraints

- Python via uv in this repo, Python 3.15, CLI only, runs on the user's Mac.
- Never commit `.env`, `corpus/ycoe-archive/`, the dictionary download, or `.llm-cache/`.
- Only per-word tag lists from YCOE go to the LLM, never running passages. The README acknowledges YCOE.
- Cite wiktextract and credit Wiktionary (CC BY-SA) in the README.
- Hints are never overridden. Conflicts are flagged, not resolved silently.
- Links are built only from dictionary entries. A lemma not in the dictionary gets no URL.
- Flags come from evidence, plus the model's own report only for `ambiguous`.
- Prompt tuning uses the `dev` split only. Worked examples come only from `dev`. `test` runs only to produce reported numbers.
- Nothing from the old Glossy JSON is an answer except fields changed by the six listed Tina commits. Machine-made data is never presented as human work.
- Moonshot only: base URL `https://api.moonshot.ai/v1`, key in `MOONSHOT_API_KEY`, default model `kimi-k3.1-pro`, overridable with `MOONSHOT_MODEL`. Never print the key.
- Remaining balance at planning time is about 14.84, and more can be bought on request. Print tokens and estimated cost before any full eval, and test with `--limit` first. Prices are in Task 6.
- Gloss memory: only human-approved entries reach the model, always as a labelled possibility rather than a fact. Machine output is stored but never shown to the model. `eval` never writes to memory, and memory used in an eval never contains the sentences being scored.

## Review Focus

1. Input spelled differently from the sources (no macrons, `ð` for `þ`, `y` for `ie`, capitals, `ġ`/`ċ`): lookup should still match where normalisation allows, and output keeps the user's spelling. Tests in Task 2.
2. Words in no source (names, Latin): flagged `unknown_form`, shown with the model's best reading, and never given a link. Tests in Task 7.
3. Model or network failure mid-batch (bad JSON, wrong word count, truncation, 429, timeout): that sentence is output with `analysis_failed`, the run continues, the failure isn't cached, and eval counts it wrong rather than dropping it. Tests in Tasks 6, 7 and 9.
4. Missing or rejected API key: a one-line message saying where to put it, no traceback, and no key in the output. Tests in Tasks 6 and 8.
5. Awkward hints (`lande[noun`, `lande[]`, `lande[noun],`, `[masc,neuter]`, `[to go]`, blank lines in a file): clear error naming the word for malformed input, and contradictory hints flagged rather than guessed at. Tests in Task 4.

---

## File Structure

```text
src/glossy2/
  models.py       shared dataclasses
  normalize.py    lookup normalisation
  gold.py         gb4e parsing; Tina corrections; dev/test split
  ycoe.py         form -> tag counts; YCOE tag -> features
  dictionary.py   kaikki download, sqlite index, lookup
  tags.py         human tags <-> UD-plus features; gloss rendering
  hints.py        input line parsing
  llm.py          Moonshot call, disk cache, retries, cost estimate
  memory.py       glosses seen before, with human and machine tiers
  analyze.py      prompt, LLM response handling
  checks.py       hint enforcement, flags, links
  render.py       terminal and gb4e output
  evaluate.py     hint generation, scoring
  baselines.py    YCOE majority, CLTK Stanza
  report.py       reports/eval.md
  cli.py          gloss, coverage, eval
scripts/extract_tina.py
corpus/ohthere/tina-corrections.jsonl
memory/ang.jsonl  committed, append-only; one file per language
tests/  (one test module per source module; tests/fixtures/ holds tiny samples)
```

Shared types, in `models.py`:

```python
@dataclass class Segment: form: str; gloss: str
@dataclass class Flag: code: str; detail: str
# code in: unknown_form, tag_unseen, lemma_not_in_dictionary, hint_conflict,
#          segments_mismatch, ambiguous, analysis_failed
@dataclass class InputWord:
    form: str; punct: str; segments: list[str] | None
    hint_feats: dict[str, str]; hint_upos: str | None; hint_stem: str | None
@dataclass class WordAnalysis:
    form: str; punct: str; segments: list[Segment]; lemma: str | None
    upos: str | None; feats: dict[str, str]; meaning: str | None
    wiktionary_url: str | None; flags: list[Flag]
@dataclass class GoldToken: form: str; punct: str; segments: list[Segment]; gloss: str
@dataclass class GoldSentence: id: int; passage: str; tokens: list[GoldToken]; translation: str
```

## Tasks

### Task 1: Project setup and the answer key

**Files:**

- Modify: `pyproject.toml`, `.gitignore`, `README.md`
- Create: `src/glossy2/models.py`, `src/glossy2/gold.py`, `scripts/extract_tina.py`, `corpus/ohthere/tina-corrections.jsonl`
- Test: `tests/test_gold.py`

**Interfaces:**

- Produces: `load_gold(tex_path: Path, corrections_path: Path | None = None) -> list[GoldSentence]`, `split_sentences(sentences: list[GoldSentence]) -> tuple[list[GoldSentence], list[GoldSentence]]` (dev, test), `load_corrections(path: Path) -> dict[tuple[int, int], dict[str, object]]` keyed by (sentence id, token index), the models above.

- [ ] **Step 1: Commit the existing state.** Move `cltk[stanza]` to an optional `baseline` extra, add `openai` as a dependency and `pytest` to a `dev` group, add `.llm-cache/` and `data/` to `.gitignore`, and run `uv sync --group dev`. Confirm `git status` doesn't list `.env` or `corpus/ycoe-archive`. Commit on `main` as `chore: initial project with hand-glossed corpus and design`. Create branch `poc`.
- [ ] **Step 2: Write failing tests in `tests/test_gold.py`:**

```python
def test_counts(): # 75 sentences, 1716 tokens, every token aligned
def test_first_token():
    t = gold[0].tokens[0]; assert (t.form, t.gloss) == ("Ōhthere", "Ohthere.NOM")
def test_segments_align():
    t = token("sǣ-d-e")
    assert [(s.form, s.gloss) for s in t.segments] == [("sǣ","say"),("d","PST"),("e","IND.3SG")]
def test_unsegmented_keeps_whole_gloss():
    t = token("cwæð"); assert t.segments == [Segment("cwæð", "say.PST.IND.3SG")]
def test_punct_separated(): # hlāford-e, -> form "hlāford-e", punct ","
def test_comparative_normalised(): # a suffix "comp" becomes CMP; a standalone \textsc{comp} stays COMP
def test_quirks_parse(): # have--prs.ind.pl and dat,pl parse without crashing, no empty segments
def test_translation_keeps_text_drops_footnote(): # no "\\footnote" in any translation
def test_passages(): # gold[50].passage == "ohthere"; gold[51].passage == "wulfstan"
def test_split_fixed(): # 15 dev, 60 test, disjoint, both passages in both, same result on repeat
def test_tina_applied(): # the word lemmatised wrongly as westanwindesan has lemma "westanwind" in corrections
```

- [ ] **Step 3: Run `uv run pytest tests/test_gold.py -v`.** Expected: FAIL, import error.
- [ ] **Step 4: Implement `gold.py`.** Parse only after `\begin{document}`. If a word has fewer hyphen segments than its gloss, or more, keep the whole word as one segment and whole gloss, rather than guess the alignment. Split the dev set with `random.Random(1729)`, stratified by passage, keeping 11 Ohthere and 4 Wulfstan sentences.
- [ ] **Step 5: Implement and run `scripts/extract_tina.py`.** Take the `../glossy` repo path as an argument. For commits `d1ef57a ea2abff f5a7dcf 72dcd3c db12d79 17db08c`, compare each with its parent and keep changes to `lemma`, `partOfSpeech`, `wiktionaryUrl`, non-empty `features` values and `morphologicalGloss`. Ignore `review`, `definition`, `sourceGlossTex` and metadata. Write the final value per (sentence, token, field) as JSONL, with the commit hash. Print counts. Expected: about 21 lemmas, 30 parts of speech, 32 URLs, 50 feature values and 9 glosses. If they differ a lot, stop and report.
- [ ] **Step 6: Run the tests.** Expected: PASS.
- [ ] **Step 7: Commit** as `feat: parse the human-glossed answer key and Tina corrections`.

### Task 2: Sources, and the go/no-go coverage check

**Files:**

- Create: `src/glossy2/normalize.py`, `src/glossy2/ycoe.py`, `src/glossy2/dictionary.py`, `src/glossy2/cli.py`
- Test: `tests/test_normalize.py`, `tests/test_ycoe.py`, `tests/test_dictionary.py`, with `tests/fixtures/mini.pos` and `tests/fixtures/mini-kaikki.jsonl`

**Interfaces:**

- Consumes: `load_gold`.
- Produces:
    - `normalize(form: str) -> str`
    - `YcoeIndex.load(pos_dir: Path, exclude: set[str] = frozenset()) -> YcoeIndex`; `.tags(form: str) -> Counter[str]`
    - `ycoe_features(tag: str) -> tuple[str | None, dict[str, str]]` (UPOS, features)
    - `Dictionary.open(path: Path = Path("data/dictionary.sqlite")) -> Dictionary`; `.lookup(form: str) -> list[Entry]`; `.has_lemma(lemma: str) -> bool`
    - `Entry(lemma: str, pos: str, senses: list[str], url: str, form_tags: list[list[str]])`
    - CLI `glossy2 coverage [--tex PATH]`

- [ ] **Step 1: Write failing tests:**

```python
def test_normalize():
    assert normalize("Ðǣm") == normalize("þam") == normalize("+t+am")
    assert normalize("ġēar") == normalize("gear"); assert normalize("ċirre") == normalize("cirre")
def test_normalize_y_i_kept_apart(): assert normalize("hyra") != normalize("hira")
def test_ycoe_counts(): # mini.pos: tags("lande") == Counter({"N^D": 2}); ID and CODE tokens ignored
def test_ycoe_exclude(): # exclude={"mini.pos"} gives empty tags
def test_ycoe_features():
    assert ycoe_features("N^D") == ("NOUN", {"Case": "Dat"})
    assert ycoe_features("VBDI") == ("VERB", {"Tense": "Past", "Mood": "Ind"})
    assert ycoe_features("BEPS") == ("AUX", {"Tense": "Pres", "Mood": "Sub"})
    assert ycoe_features("UNKNOWN") == (None, {})
def test_dictionary_inflected_form(): # "lande" finds lemma "land" with dative singular tags
def test_dictionary_lemma_form(): # "land" finds itself, senses non-empty
def test_dictionary_url(): # URL is https://en.wiktionary.org/wiki/land#Old_English
def test_dictionary_skips_template_rows(): # forms with "table-tags" or "inflection-template" aren't indexed
def test_form_of_sense_resolves_to_lemma(): # an entry with only form_of senses reports the target lemma
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** YCOE reads files as latin-1. Download `https://kaikki.org/dictionary/Old%20English/kaikki.org-dictionary-OldEnglish.jsonl` once to `data/` if missing. The page marks it deprecated, so if the download fails, say so and point to the kaikki.org page. Build `data/dictionary.sqlite` indexed on normalised form. Build URLs with the entry's `word` field stripped of macrons and dots, the same way Wiktionary titles its pages, percent-encoded with `#Old_English`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Implement `glossy2 coverage`.** With `coorosiu.o2.pos` excluded, it prints: % of tokens and distinct forms found in YCOE, % in the dictionary, % in neither, % with exactly one candidate lemma, and the 20 most frequent forms in neither. Forms are stripped of hyphens first.
- [ ] **Step 6: Run `uv run glossy2 coverage`. This is the design's go/no-go.** If over 50% of tokens have no dictionary lemma, stop and report to the user. Do not start Task 3. Otherwise record the numbers in the commit message.
- [ ] **Step 7: Commit** as `feat: add YCOE and Wiktionary lookup with coverage check`.

### Task 3: Tags and gloss rendering

**Files:**

- Create: `src/glossy2/tags.py`
- Test: `tests/test_tags.py`

**Interfaces:**

- Produces: `parse_gloss(gloss: str) -> tuple[str, dict[str, str]]` (lexical stem, features), `render_gloss(analysis: WordAnalysis) -> str`, `HUMAN_TO_FEATS: dict[str, dict[str, str]]`.

- [ ] **Step 1: Write failing tests:**

```python
def test_parse():
    assert parse_gloss("say-PST-IND.3SG") == ("say", {"Tense":"Past","Mood":"Ind","Person":"3","Number":"Sing"})
    assert parse_gloss("DET.DEF.DAT.SG.N")[1] == {"PronType":"Det","Definite":"Def","Case":"Dat","Number":"Sing","Gender":"Neut"}
    assert parse_gloss("north-man-GEN.PL") == ("north-man", {"Case":"Gen","Number":"Plur"})
    assert parse_gloss("find.out-THM-INF") == ("find.out", {"Thematic":"Yes","VerbForm":"Inf"})
    assert parse_gloss("be.allowed-PRS")[0] == "be.allowed"
def test_extensions(): # HAB, THM, AGT, NMLZ, PFX, COMP, NEG all map to named features
def test_every_gold_tag_known(): # every uppercase tag in the answer key is in HUMAN_TO_FEATS
def test_render_roundtrip(): # the rendered gloss from Segment glosses equals "say-PST-IND.3SG"
def test_render_marks_flagged(): # a flagged word's gloss ends with "?"
def test_render_failed(): # analysis_failed renders as "???", not an empty string
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Lexical text is any lowercase part, including dotted stems like `find.out`. Bundles like `3SG` expand to Person and Number. Custom keys: `Aspect=Hab`, `Thematic=Yes`, `Derivation=Agt|Nmlz`, `Prefix=Yes`, `PartType=Comp`, `Polarity=Neg`.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: map human gloss tags to features`.

### Task 4: Hint parsing

**Files:**

- Create: `src/glossy2/hints.py`
- Test: `tests/test_hints.py`

**Interfaces:**

- Consumes: `InputWord`.
- Produces: `parse_line(line: str) -> list[InputWord]`, `HintError(word: str, reason: str)`, `HINT_LABELS: dict[str, tuple[str, str]]`.

- [ ] **Step 1: Write failing tests:**

```python
def test_plain(): assert [w.form for w in parse_line("Hē cwæð þæt")] == ["Hē","cwæð","þæt"]
def test_punct(): w = parse_line("lande,")[0]; assert (w.form, w.punct) == ("lande", ",")
def test_labels():
    w = parse_line("lande[noun,neuter]")[0]
    assert w.hint_upos == "NOUN" and w.hint_feats == {"Gender":"Neut"}
def test_stem(): assert parse_line("hlāford-e[lord]")[0].hint_stem == "lord"
def test_multiword_stem(): assert parse_line("gān[to go]")[0].hint_stem == "to go"
def test_label_and_stem(): w = parse_line("lande[land,dat]")[0]; assert w.hint_stem == "land" and w.hint_feats == {"Case":"Dat"}
def test_segmentation_fixed(): assert parse_line("sǣ-d-e")[0].segments == ["sǣ","d","e"]
def test_punct_after_hint(): w = parse_line("lande[noun],")[0]; assert w.punct == ","
def test_unbalanced(): # "lande[noun" raises HintError naming "lande"
def test_empty_hint(): # "lande[]" raises HintError naming "lande"
def test_two_stems(): # "lande[land,earth]" raises HintError: only one stem meaning allowed
def test_contradiction_kept(): # "x[masc,neuter]" gives hint_feats with both, in `hint_conflicts`, for checks to flag
def test_blank_line(): assert parse_line("   ") == []
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Labels are case-insensitive and include full names and tag forms (`neuter`, `neut`, `n`, `dat`, `dative`, `sg`, `past`, `pst`, ...). Add `hint_conflicts: list[str]` to `InputWord` in `models.py`. Split on whitespace outside brackets.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: parse per-word hints`.

### Task 5: Checks

**Files:**

- Create: `src/glossy2/checks.py`
- Test: `tests/test_checks.py`

**Interfaces:**

- Consumes: `InputWord`, `WordAnalysis`, `YcoeIndex`, `ycoe_features`, `Dictionary`.
- Produces: `apply_checks(word: InputWord, proposed: WordAnalysis, ycoe: YcoeIndex, dictionary: Dictionary) -> WordAnalysis`; `segments_rejoin(form: str, segments: list[Segment]) -> bool`.

- [ ] **Step 1: Write failing tests** using fake lookups:

```python
def test_hint_wins_and_flags(): # hint Gender=Neut, model Gender=Masc -> feats Neut, hint_conflict flag naming both
def test_hint_upos_wins(): # hint NOUN, model VERB -> NOUN and flagged
def test_hint_stem_wins(): # hint "lord", model "master" -> stem segment gloss "lord", meaning "lord", and no flag: synonyms aren't conflicts
def test_contradictory_hints_flagged(): # hint_conflicts non-empty -> hint_conflict flag
def test_unknown_form(): # in neither source -> unknown_form, URL None
def test_tag_unseen(): # YCOE has only N^D, model says Case=Acc -> tag_unseen
def test_tag_compatible_no_flag(): # YCOE has N^D, model says NOUN Case=Dat Number=Sing Gender=Neut -> no flag: extras aren't conflicts
def test_lemma_not_in_dictionary(): # "gesceopan" -> lemma_not_in_dictionary, URL None, lemma kept and shown
def test_url_from_entry_only(): # a model-supplied URL is ignored; url comes from Entry
def test_url_macrons_case(): # model lemma "land" and entry "land" match after normalising
def test_rejoin(): assert segments_rejoin("sǣde", [Segment("sǣ","say"),Segment("d","PST"),Segment("e","IND.3SG")])
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Compatibility: a word is fine if some YCOE tag seen for its form agrees on UPOS and on every feature that tag states. Treat YCOE `N`/`NR`/`Q` families with a small UPOS-equivalence table, so `Q^A` and `DET` don't falsely conflict. No YCOE tags for a form that the dictionary knows isn't `unknown_form`, and isn't `tag_unseen` either.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: enforce hints and raise evidence-based flags`.

### Task 6: Moonshot client

**Files:**

- Create: `src/glossy2/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**

- Produces: `complete_json(messages: list[dict], *, client=None, cache_dir: Path = Path(".llm-cache")) -> dict`; `LLMError(reason: str)`; `MissingKeyError`; `estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float`; `usage_totals() -> tuple[int, int]`.

- [ ] **Step 1: Write failing tests** with a fake client:

```python
def test_cache_hit_no_second_call(tmp_path): # same messages twice -> fake called once
def test_key_includes_model(tmp_path): # a different model misses the cache
def test_failure_not_cached(tmp_path): # invalid JSON, then valid -> second run calls again and succeeds
def test_retries_on_429(tmp_path): # 429 then OK -> returns, called twice, no real sleep in tests
def test_gives_up(tmp_path): # three failures -> LLMError
def test_truncated_is_error(tmp_path): # finish_reason "length" -> LLMError, not parsed
def test_missing_key(monkeypatch, tmp_path): # no key -> MissingKeyError whose message mentions .env
def test_key_never_in_error(monkeypatch, tmp_path): # auth failure -> MissingKeyError; str(err) has no key
def test_usage_counted(tmp_path): # usage totals increase only on real calls
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Use the `openai` SDK with `base_url="https://api.moonshot.ai/v1"`, temperature 0 and JSON response format. Read `.env` from the repo root without adding a dependency unless needed. Up to 3 attempts with backoff. Put prices in a dict dated 2026-11-01, in USD per million tokens as input, output, cached input: `kimi-k3.1-pro` 2.00, 10.00, 0.20; `kimi-k3.1-pro-highspeed` 4.00, 20.00, 0.20; `kimi-k3` 3.00, 15.00, 0.30; `kimi-k2.7-code` 0.95, 4.00, 0.19; `kimi-k2.7-code-highspeed` 1.90, 8.00, 0.38; `kimi-k2.6` 0.95, 4.00, 0.16. Estimates assume no cached input, so they run high. Unknown models give `nan`, shown as "unknown". Don't use the Batch API.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Smoke test** with one real call asking for `{"ok": true}`. Expected: parsed dict, and a cache file created. Check that `.llm-cache/` is ignored.
- [ ] **Step 6: Commit** as `feat: add cached Moonshot client`.

### Task 7: Analyser

**Files:**

- Create: `src/glossy2/analyze.py`
- Test: `tests/test_analyze.py`

**Interfaces:**

- Consumes: `complete_json`, `apply_checks`, `segments_rejoin`, `split_sentences`, lookups.
- Produces: `analyze_sentence(words: list[InputWord], ctx: Context) -> list[WordAnalysis]`; `Context(ycoe, dictionary, examples: list[GoldSentence], complete=complete_json)`; `build_messages(words, ctx) -> list[dict]`.

- [ ] **Step 1: Write failing tests** with a fake `complete`:

```python
def test_prompt_has_candidates(): # YCOE tags and dictionary lemmas per word appear in the prompt
def test_prompt_has_hints_as_fixed(): # hints and fixed segments appear, marked as not to be changed
def test_prompt_uses_only_given_examples(): # worked examples are from ctx.examples; a test sentence never appears
def test_prompt_no_ycoe_passages(): # only form-plus-tag-count data from YCOE appears
def test_prompt_allows_unknown(): # the prompt tells the model to report ambiguity instead of forcing a guess
def test_good_response(): # returns one WordAnalysis per word, in order, with spelling as typed
def test_wrong_word_count_retries_once(): # bad count then good -> OK, two calls
def test_wrong_word_count_twice(): # -> every word has analysis_failed, no exception
def test_llm_error(): # LLMError -> every word has analysis_failed, no exception
def test_bad_segments_retry_then_flag(): # non-rejoining twice -> segments_mismatch, whole word as one segment
def test_fixed_segments_kept(): # input sǣ-d-e keeps those three forms even if the model differs, and flags it
def test_model_ambiguous_flag(): # model reports ambiguous -> ambiguous flag with its reason
def test_unknown_word_no_link(): # a word in no source -> unknown_form and no URL
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Request per word: `index, segments[{form, gloss}], lemma, upos, feats, meaning, ambiguous, ambiguity_reason`. State the tag vocabulary from `HUMAN_TO_FEATS` and include worked examples so the model learns which features are normally left unmarked. Retries for count or segments change the prompt by adding the error, so the cache doesn't return the same bad answer. `ctx.examples` for `gloss` and `eval` is the 15 `dev` sentences.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: analyse sentences with candidates and fixed hints`.

### Task 7a: Gloss memory

Remembers glosses seen before, so a later text can use them as a possible reading. Machine output is kept apart: if it reached the model, one wrong gloss could keep confirming itself, which is the old engine's failure in a new form.

**Files:**
- Create: `src/glossy2/memory.py`, `memory/ang.jsonl`
- Modify: `src/glossy2/analyze.py`
- Test: `tests/test_memory.py`, `tests/test_analyze.py`

**Interfaces:**
- Consumes: `GoldSentence`, `normalize`, `WordAnalysis`.
- Produces: `MemoryEntry(form: str, gloss: str, lemma: str | None, source: str, tier: str)` (tier `human` or `machine`); `Memory.load(path: Path) -> Memory`; `Memory.from_gold(sentences: list[GoldSentence], source: str) -> Memory` (in memory only, never saved); `.human(form: str) -> list[tuple[str, int, list[str]]]` (gloss, count, sources, most frequent first); `.add_human(sentences, source, path)`; `.record_machine(analyses, source, path)`. `Context` gains `memory: Memory | None`.

- [ ] **Step 1: Write failing tests:**

```python
def test_counts_readings(): # two "þæt" as COMP and one as DET.DEF.NOM.SG.N -> ordered with counts
def test_normalised_lookup(): # glosses from "ġehālgod" are found by "gehalgod"
def test_machine_not_returned(): # record_machine, then human(form) == []
def test_record_skips_flagged(): # flagged and analysis_failed words aren't recorded
def test_add_human_twice_same_source(): # re-adding a source replaces it, so counts don't double
def test_persist_roundtrip(tmp_path): # entries survive load
def test_prompt_shows_human_memory(): # the prompt lists the gloss, count and source, worded as possibly not applying here
def test_prompt_no_machine_memory(): # a machine entry never appears in the prompt
def test_prompt_no_memory(): # memory None -> prompt has no memory section, and still works
def test_memory_not_used_as_hint(): # the model's differing analysis is kept, with no hint_conflict flag
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Append-only JSONL, one object per token occurrence. Keep the prompt's memory section after the shared prefix of examples, so Moonshot's prefix caching still applies. Cap at the 5 most frequent readings per form.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: add gloss memory with human and machine tiers`.

### Task 8: `glossy2 gloss`

**Files:**

- Create: `src/glossy2/render.py`
- Modify: `src/glossy2/cli.py`, `src/glossy2/__init__.py`
- Test: `tests/test_render.py`, `tests/test_cli.py`

**Interfaces:**

- Consumes: `parse_line`, `analyze_sentence`, `render_gloss`.
- Produces: `render_text(analyses: list[WordAnalysis]) -> str`, `render_gb4e(analyses: list[WordAnalysis], translation: str = "") -> str`, CLI `glossy2 gloss TEXT | --file PATH [--format text|gb4e] [--no-record]` and `glossy2 remember PATH --name NAME` (loads a human-approved `gb4e` file into `memory/ang.jsonl` as tier `human`). `gloss` loads that memory, and records unflagged output as tier `machine` unless `--no-record`.

- [ ] **Step 1: Write failing tests:**

```python
def test_columns_align(): # with Old English of varying width and macrons, each gloss starts under its word
def test_flags_listed(): # output has "word: reason" lines beneath the gloss
def test_table_has_lemma_and_link(): # a word without a URL shows "-", not an invented link
def test_gb4e(): # \gll ... \\ newline gloss \\ ; tags in \textsc{}; LaTeX specials escaped; flagged words marked
def test_gb4e_blank_translation(): # \glt is present and empty, so the block still compiles
def test_cli_missing_key(capsys): # exit 2, one-line .env message, no traceback
def test_cli_bad_hint(capsys): # exit 2, message names the word, no traceback, no LLM call
def test_cli_file_blank_lines(): # blank lines are skipped, and a failed sentence doesn't stop the rest
def test_cli_no_args(capsys): # usage shown, exit 2
def test_cli_remember(tmp_path): # adds human entries, and prints how many tokens and forms
def test_cli_no_record(tmp_path): # --no-record leaves the memory file unchanged
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Measure width after Unicode normalisation (NFC, ignoring combining marks), so columns line up. Wrap long sentences to the terminal width by whole word blocks.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Run the real thing:** `uv run glossy2 gloss "Fæder ure þu þe eart on heofonum si þin nama gehalgod"`, then the same with `eart[verb]`. Expected: `eart` is a form of _wesan_/_bēon_, `þu` is a pronoun, and anything unsupported is flagged. Paste the output in the commit message. Then `--format gb4e` compiled with `xelatex` against the header of the human `.tex`. Expected: no errors.
- [ ] **Step 6: Commit** as `feat: add gloss command`.

### Task 9: Scoring

**Files:**

- Create: `src/glossy2/evaluate.py`
- Test: `tests/test_evaluate.py`

**Interfaces:**

- Consumes: `GoldSentence`, `parse_gloss`, `load_corrections`, `analyze_sentence`.
- Produces: `make_inputs(sentence: GoldSentence, level: str, seed: int = 1729) -> tuple[list[InputWord], list[Withheld]]`; `Withheld(stem: bool, feats: set[str])`; `score_sentence(gold, analyses, withheld, corrections, dictionary) -> list[TokenScore]`; `aggregate(scores: list[TokenScore]) -> Scores`.

- [ ] **Step 1: Write failing tests:**

```python
def test_inputs_have_no_hyphens(): # at every level, input forms are unsegmented and segments is None
def test_level_none(): # no hints; everything withheld
def test_level_stem(): # hint_stem given, no feats; withheld.stem False
def test_level_half_repeatable(): # about half the features, same selection on repeat
def test_level_stem_half(): # both
def test_only_withheld_scored(): # a correct hinted feature adds nothing to a feature's total
def test_unmarked_extra_ignored(): # predicted Gender on land-DAT.SG is neither right nor wrong
def test_tina_feature_scored(): # gender from corrections counts even if the gloss omits it
def test_exact_gloss(): # say-PST-IND.3SG exact is right; a "?" flag mark is ignored when comparing
def test_exact_excludes_nothing_withheld(): # a token with nothing withheld isn't in the exact-gloss total
def test_meaning_exact_and_sense(): # "speak" vs gold "say" is wrong on exact; right on sense when a dictionary sense has "say"
def test_lemma_only_on_corrections(): # lemma total equals the tokens with a lemma correction
def test_failed_counts_wrong(): # analysis_failed tokens stay in every denominator
def test_flag_quality(): # accuracy computed separately for flagged and unflagged, with counts
def test_segmentation(): # sǣ/d/e vs sǣd/e is wrong; comparison uses forms only
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Use `random.Random(f"{seed}:{sentence.id}:{token_index}")` per token, so selection is independent of run order. Function words with no lexical stem have nothing for a `stem` hint to give.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: score analyses against human glosses`.

### Task 10: `glossy2 eval`, baselines and report

**Files:**

- Create: `src/glossy2/baselines.py`, `src/glossy2/report.py`
- Modify: `src/glossy2/cli.py`
- Test: `tests/test_baselines.py`, `tests/test_report.py`, `tests/test_cli_eval.py`

**Interfaces:**

- Consumes: all of Task 9, `split_sentences`, `estimate_cost`, `usage_totals`.
- Produces: `glossy2 eval --hints LEVEL|all [--split dev|test] [--limit N] [--yes] [--gold PATH --name NAME] [--exclude-ycoe FILE ...] [--memory none|dev|ohthere]`; `ycoe_majority(form, ycoe) -> dict[str, str]`; `cltk_analyses(sentence) -> list[WordAnalysis]`; `write_report(results, path)`.

- [ ] **Step 1: Write failing tests:**

```python
def test_default_excludes_orosius(): # the Ohthere eval builds YcoeIndex with exclude={"coorosiu.o2.pos"}
def test_full_run_asks_first(): # without --limit or --yes: shows tokens and cost, stops on "n", makes no calls
def test_limit_skips_prompt(): # --limit 2 proceeds without asking
def test_default_split_dev(): # no --split runs dev, so test is never run by accident
def test_test_split_needs_yes(): # --split test without --yes asks first
def test_gold_path_all_test(): # --gold treats all sentences as test; examples are still Ohthere dev
def test_majority(): # most common tag's features; unknown form gives {}
def test_baseline_only_scores_what_it_has(): # no exact-gloss number for a baseline: "n/a" rather than 0
def test_eval_never_writes_memory(tmp_path): # memory/ang.jsonl is byte-identical after an eval
def test_memory_excludes_scored(): # --memory dev on the test split: no scored sentence is in memory
def test_memory_rejects_leak(): # --memory ohthere with the Ohthere test split exits 2
def test_memory_effect(): # for runs with memory: accuracy on forms in memory vs not; and where memory's top
                          # reading was wrong, how often the model repeated it (the anchoring cost)
def test_report_sections(): # hint table, per-feature table, flag quality, baselines, error sample, caveats
def test_report_caveats(): # says dev tuned; model may remember Ohthere; lemma sample is small and biased;
                           # scoring is recall of what was marked; YCOE acknowledged
def test_error_sample_fixed(): # the same seed gives the same sample, with gold and predicted side by side
def test_failed_sentences_reported(): # the count of analysis_failed tokens is shown
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Run sentences in a thread pool of 4. Estimate cost from a dry prompt build, at about 4 characters a token, with the completion estimated from word count. `cltk_analyses` is imported lazily and reports "not installed" if the `baseline` extra is absent. Lemma caveat wording must say the Tina lemma set is tokens the old engine got wrong, so it's a harder-than-average sample. Skip the old lemmatizer baseline: those corrections would score it near 0 by construction, and its tables were built around this text, so the number says nothing fair.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** as `feat: add eval command, baselines and report`.

### Task 11: Tune on dev, then run the test set once

**Files:**

- Modify: `src/glossy2/analyze.py`, `README.md`
- Create: `reports/eval.md`

- [ ] **Step 1: Run `uv run glossy2 eval --hints none --split dev --limit 3`.** Expected: real scores and a cost line. Read the sentences' output by eye.
- [ ] **Step 2: Tune the prompt on dev.** Run all levels on `dev`. Fix systematic errors in the prompt, tag mapping or checks. At most 3 rounds, and record each round's dev exact-gloss score in the commit message. Stop and report if tuning spend passes $5.00. If the test run's estimate then exceeds the remaining balance, ask the user to top up rather than cutting the run down.
- [ ] **Step 3: Check flag rate on dev.** If over 60% of tokens are flagged, or flagged words aren't clearly less accurate, fix the flag rules on dev before going further.
- [ ] **Step 4: Commit the frozen prompt** as `chore: freeze prompt after dev tuning`.
- [ ] **Step 5: Install the baseline** with `uv sync --extra baseline` and run `uv run glossy2 eval --hints all --split test --memory dev --yes`, then `uv run glossy2 eval --hints none --split test --memory none --yes` to measure memory's effect. Expected: `reports/eval.md`, with all sections. Do not change the prompt after this. If a real bug appears, fix it, say so in the report, and keep the first run's numbers beside the new ones.
- [ ] **Step 6: Write the README:** what it is, setup, `.env`, the three commands, hint syntax, flags, how to read the report, YCOE acknowledgement and licence limits, and the Wiktionary and wiktextract credits.
- [ ] **Step 7: Run `uv run pytest -v` and `git status`.** Expected: all pass, and no `.env`, YCOE or `data/` in the status.
- [ ] **Step 8: Commit** as `docs: add evaluation report and README`.

### Task 12: Unseen-text test (needs the new human gloss)

Do this when the file arrives. Don't wait for it to finish Task 11. The design calls Ohthere scores possibly high because the model may remember the text, and this is the check on that.

**Files:**

- Create: `corpus/<name>/` (the file as received, unedited), `reports/eval-<name>.md`
- Modify: `corpus/README.md`, `src/glossy2/gold.py` if needed
- Test: `tests/test_gold.py`

**Interfaces:**

- Consumes: `load_gold`, `glossy2 eval --gold PATH --name NAME --exclude-ycoe FILE`.

- [ ] **Step 1: Check the format.** If it's `gb4e` and loads with `load_gold`, continue. If it's anything else, ask the user before writing a parser, and don't reformat it by hand.
- [ ] **Step 2: Write a test** pinning its sentence count, token count and first token, and that every token aligns. List tags missing from `HUMAN_TO_FEATS`, and add them with a test. Don't guess at any tag's meaning: ask the user.
- [ ] **Step 3: Check overlap with YCOE:** find any `.pos` file sharing a run of 5 or more normalised words with the text, and pass those files to `--exclude-ycoe`. Name them in the report.
- [ ] **Step 4: Run** `uv run glossy2 eval --hints all --gold corpus/<name>/<file> --name <name> --memory ohthere --yes`, then the same with `--hints none --memory none`, with the prompt unchanged from Task 11. All of Ohthere as memory against a new text is the realistic test of whether memory pays off. Expected: `reports/eval-<name>.md`. Add a short comparison with `reports/eval.md`, and state its sample size.
- [ ] **Step 5: Record the text in `corpus/README.md`,** with who glossed it and when. Then run `uv run glossy2 remember corpus/ohthere/Voyages_of_Ohthere_Wulfstan.tex --name ohthere` and the same for the new text, so real use starts with all human work in memory.
- [ ] **Step 6: Commit** as `feat: evaluate on unseen human-glossed text`.
