# Evaluation: Ohthere and Wulfstan

Split: `dev`. 15 sentences. Model kimi-k3.1-pro, about $1.66 at list price.

## Read this first

- **What was tuned on what.** The prompt was tuned on 15 sentences (`dev`), which also supply the model's worked examples. The numbers below come from text that was not used for either, unless this report says it is the `dev` report.
- **The model may remember this text.** Ohthere is famous, so the model may have seen it in training. Scores here may run higher than on text it has never seen.
- **YCOE's copy was removed.** YCOE's Orosius contains this passage, so that file was left out of the evidence.
- **What counts as right.** Only what the hints withheld is scored, so a hint echoed back can't raise a score. A feature counts only where the human marked it, so these numbers show recall of what the human marked. An extra feature the human left unmarked is ignored rather than counted wrong.
- **Lemma numbers are a small, harder-than-average sample.** They use only the human Tina corrections, which are mostly words the old engine got wrong.
- **Settings.** Model reasoning was turned off to keep cost and time down, and Moonshot doesn't allow a fixed temperature on this model. Cached responses make a rerun reproducible, but a rerun without the cache could differ slightly.
- **Sources.** York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE), used under its conditions for scholarly research. Dictionary data from Wiktionary (CC BY-SA) via wiktextract and kaikki.org.

## Accuracy by hint level

| Hints | Memory | Words with grammar, same words at every level | Whole gloss exact, withheld only | Segmentation | Meaning exact | Meaning (any dictionary sense) | Lemma |
|---|---|---|---|---|---|---|---|
| none | none | 70.8% (138/195) | 75.5% (213/282) | 91.1% (257/282) | 85.4% (204/239) | 90.0% (215/239) | 71.4% (5/7) |
| half | none | 75.4% (147/195) | 78.0% (216/277) | 89.4% (252/282) | 85.8% (205/239) | 91.2% (218/239) | 71.4% (5/7) |
| stem | none | 76.9% (150/195) | 76.9% (150/195) | 90.1% (254/282) | n/a | n/a | 85.7% (6/7) |
| stem+half | none | 82.1% (160/195) | 84.0% (137/163) | 92.2% (260/282) | n/a | n/a | 71.4% (5/7) |

Use the first accuracy column to compare hint levels. It scores the same words each time, though at hint levels with features given, a word can match partly because its hints were given. The second column drops words with nothing withheld, so its word set changes per level and easy function words leave it at `stem`.

0 token analyses failed outright (bad or missing model response). They count as wrong.

## Per feature

| Feature | none / memory none | half / memory none | stem / memory none | stem+half / memory none | YCOE most-common tag | CLTK Stanza |
|---|---|---|---|---|---|---|
| Aspect | 87.5% (7/8) | 100.0% (4/4) | 87.5% (7/8) | 75.0% (3/4) | 0.0% (0/8) | 0.0% (0/8) |
| Case | 95.6% (129/135) | 97.2% (70/72) | 95.6% (129/135) | 98.6% (71/72) | 56.3% (76/135) | 82.2% (111/135) |
| Declension | 84.4% (27/32) | 91.7% (11/12) | 84.4% (27/32) | 100.0% (12/12) | 0.0% (0/32) | 0.0% (0/32) |
| Definite | 100.0% (21/21) | 100.0% (11/11) | 100.0% (21/21) | 100.0% (11/11) | 0.0% (0/21) | 0.0% (0/21) |
| Degree | 100.0% (8/8) | 100.0% (7/7) | 100.0% (8/8) | 100.0% (7/7) | 50.0% (4/8) | 87.5% (7/8) |
| Deixis | 0.0% (0/3) | 50.0% (1/2) | 0.0% (0/3) | 50.0% (1/2) | 0.0% (0/3) | 0.0% (0/3) |
| Derivation | 66.7% (2/3) | 0.0% (0/1) | 66.7% (2/3) | 0.0% (0/1) | 0.0% (0/3) | 0.0% (0/3) |
| Form | 63.6% (7/11) | 100.0% (5/5) | 45.5% (5/11) | 100.0% (5/5) | 0.0% (0/11) | 0.0% (0/11) |
| Gender | 92.9% (65/70) | 94.4% (34/36) | 92.9% (65/70) | 97.2% (35/36) | 0.0% (0/70) | 62.9% (44/70) |
| Mood | 91.2% (31/34) | 81.2% (13/16) | 88.2% (30/34) | 93.8% (15/16) | 76.5% (26/34) | 79.4% (27/34) |
| Number | 98.2% (166/169) | 100.0% (82/82) | 98.2% (166/169) | 100.0% (82/82) | 0.0% (0/169) | 86.4% (146/169) |
| PartType | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 0.0% (0/4) | 0.0% (0/4) |
| Person | 94.3% (33/35) | 94.4% (17/18) | 91.4% (32/35) | 94.4% (17/18) | 0.0% (0/35) | 74.3% (26/35) |
| Polarity | 100.0% (5/5) | 100.0% (2/2) | 100.0% (5/5) | 100.0% (2/2) | 80.0% (4/5) | 80.0% (4/5) |
| Prefix | 100.0% (4/4) | 100.0% (2/2) | 100.0% (4/4) | 100.0% (2/2) | 0.0% (0/4) | 0.0% (0/4) |
| PronType | 87.0% (20/23) | 88.9% (8/9) | 87.0% (20/23) | 88.9% (8/9) | 0.0% (0/23) | 4.3% (1/23) |
| Tense | 100.0% (27/27) | 100.0% (15/15) | 100.0% (27/27) | 100.0% (15/15) | 96.3% (26/27) | 85.2% (23/27) |
| Thematic | 100.0% (5/5) | 100.0% (1/1) | 80.0% (4/5) | 100.0% (1/1) | 0.0% (0/5) | 0.0% (0/5) |
| VerbForm | 88.9% (8/9) | 100.0% (5/5) | 88.9% (8/9) | 100.0% (5/5) | 44.4% (4/9) | 44.4% (4/9) |

## Do flags mean anything?

Flags only earn trust if unflagged words are clearly more accurate.

| Hints | Memory | Unflagged, exact | Flagged, exact |
|---|---|---|---|
| none | none | 77.3% (198/256) | 57.7% (15/26) |
| half | none | 80.0% (200/250) | 59.3% (16/27) |
| stem | none | 78.8% (134/170) | 64.0% (16/25) |
| stem+half | none | 87.2% (129/148) | 53.3% (8/15) |

## Baselines

| Baseline | Whole gloss exact | Segmentation | Lemma |
|---|---|---|---|
| YCOE most-common tag | n/a | n/a | 0.0% (0/7) |
| CLTK Stanza | n/a | n/a | 71.4% (5/7) |

Neither baseline produces glosses or morpheme splits. Compare them on the features above.

## Sample of real errors

From the `none` run. A `?` on a gloss means the tool flagged it.

| Word | Human gloss | Tool's gloss |
|---|---|---|
| þēah | though | however |
| wēst-e | waste-NOM.SG.N.STR | waste.NOM.SG.N.STR |
| hunt-oð-e | hunt-NMLZ-DAT.SG | hunting-DAT.SG |
| ċirr-e | occasion-DAT.SG | time-DAT.SG |
| fand-i-an | find.out-THM-INF | explore-THM-INF |
| norþ-ryht-e | north-right-ADV | north-straight? |
| on | in | into |
| forþ | forth.ADV | forth |
| eall | all.NOM.SG.N | all.NOM.SG.N.STR |
| ōþr-e | other-ACC.SG.F.STR | other-DAT.SG.F.WK |
| ōðre | other-NOM.PL.M.STR | other-NOM.PL.STR |
| Þæt | DET.DEF.DAT.SG.N | DET.DEF.NOM.SG.N |
| ġe-worh-t | PFX-make-PART.NOM.SG.N.STR | PFX-make.PART |
| bȳ-n-e | dwell-PART-NOM.SG.N.WK | inhabited-NOM.SG.N.STR |
| brǣd-r-e | broad-CMP-NOM.SG.N.WK | broad.CMP-NOM.SG.N-WK? |
| hæf-d-e | have-PST-IND.3SG | have-PST-SJV.SG? |
| Wīsl-e-mūð-an | Vistula-NOM.SG-river.mouth-ACC.SG | Vistula-mouth-ACC.SG? |
| Wīsl-e | Vistula-NOM.SG | Vistula.NOM.SG |
| lī-ð | lie-PRS.IND.3SG | lie.PRS.IND.3SG |
| Ēst-mer-e | Est-lake-NOM.SG | Est-lake.NOM.SG? |
| hūru | indeed | at.least |
| myċel | large.NOM.SG.N.STR | much.NOM.SG.N.STR |
| rīċ-ost-an | rich-SUP-NOM.PL.WK | powerful-SUP-NOM.PL.WK? |
| un-spēd-ig-an | un-wealth-ADJ-NOM.PL.WK | un-wealthy-NOM.PL.WK? |
| þēow-an | servant-NOM.PL | slave-NOM.PL |
