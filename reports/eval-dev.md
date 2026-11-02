# Evaluation: Ohthere and Wulfstan

Split: `dev`. 15 sentences. Model kimi-k3.1-pro, about $1.54 at list price.

## Read this first

- **What was tuned on what.** The prompt was tuned on 15 sentences (`dev`), which also supply the model's worked examples. The numbers below come from text that was not used for either, unless this report says it is the `dev` report.
- **The model may remember this text.** Ohthere is famous, so the model may have seen it in training. Scores here may run higher than on text it has never seen.
- **YCOE's copy was removed.** YCOE's Orosius contains this passage, so that file was left out of the evidence.
- **What counts as right.** Only what the hints withheld is scored, so a hint echoed back can't raise a score. A feature counts only where the human marked it, so these numbers show recall of what the human marked. An extra feature the human left unmarked is ignored rather than counted wrong.
- **Lemma numbers are a small, harder-than-average sample.** They use only the human Tina corrections, which are mostly words the old engine got wrong.
- **Settings.** Model reasoning was turned off to keep cost and time down, and Moonshot doesn't allow a fixed temperature on this model. Cached responses make a rerun reproducible, but a rerun without the cache could differ slightly.
- **Sources.** York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE), used under its conditions for scholarly research. Dictionary data from Wiktionary (CC BY-SA) via wiktextract and kaikki.org.

## Accuracy by hint level

| Hints | Memory | Whole gloss exact | Segmentation | Meaning exact | Meaning (any dictionary sense) | Lemma |
|---|---|---|---|---|---|---|
| none | none | 70.9% (200/282) | 72.3% (204/282) | 84.1% (201/239) | 88.7% (212/239) | 85.7% (6/7) |
| half | none | 74.4% (206/277) | 78.4% (221/282) | 85.4% (204/239) | 89.5% (214/239) | 71.4% (5/7) |
| stem | none | 51.8% (101/195) | 70.2% (198/282) | n/a | n/a | 85.7% (6/7) |
| stem+half | none | 71.2% (116/163) | 80.9% (228/282) | n/a | n/a | 85.7% (6/7) |

0 token analyses failed outright (bad or missing model response). They count as wrong.

## Per feature

| Feature | none / memory none | half / memory none | stem / memory none | stem+half / memory none | YCOE most-common tag | CLTK Stanza |
|---|---|---|---|---|---|---|
| Aspect | 87.5% (7/8) | 100.0% (4/4) | 87.5% (7/8) | 75.0% (3/4) | 0.0% (0/8) | 0.0% (0/8) |
| Case | 94.8% (128/135) | 98.6% (71/72) | 95.6% (129/135) | 98.6% (71/72) | 56.3% (76/135) | 82.2% (111/135) |
| Declension | 9.4% (3/32) | 50.0% (6/12) | 21.9% (7/32) | 58.3% (7/12) | 0.0% (0/32) | 0.0% (0/32) |
| Definite | 85.7% (18/21) | 100.0% (11/11) | 90.5% (19/21) | 100.0% (11/11) | 0.0% (0/21) | 0.0% (0/21) |
| Degree | 100.0% (8/8) | 100.0% (7/7) | 100.0% (8/8) | 100.0% (7/7) | 50.0% (4/8) | 87.5% (7/8) |
| Deixis | 0.0% (0/3) | 50.0% (1/2) | 0.0% (0/3) | 0.0% (0/2) | 0.0% (0/3) | 0.0% (0/3) |
| Derivation | 33.3% (1/3) | 100.0% (1/1) | 33.3% (1/3) | 0.0% (0/1) | 0.0% (0/3) | 0.0% (0/3) |
| Form | 90.9% (10/11) | 100.0% (5/5) | 36.4% (4/11) | 100.0% (5/5) | 0.0% (0/11) | 0.0% (0/11) |
| Gender | 94.3% (66/70) | 100.0% (36/36) | 88.6% (62/70) | 97.2% (35/36) | 0.0% (0/70) | 62.9% (44/70) |
| Mood | 88.2% (30/34) | 87.5% (14/16) | 88.2% (30/34) | 81.2% (13/16) | 76.5% (26/34) | 79.4% (27/34) |
| Number | 97.6% (165/169) | 100.0% (82/82) | 98.2% (166/169) | 100.0% (82/82) | 0.0% (0/169) | 86.4% (146/169) |
| PartType | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 0.0% (0/4) | 0.0% (0/4) |
| Person | 91.4% (32/35) | 100.0% (18/18) | 91.4% (32/35) | 100.0% (18/18) | 0.0% (0/35) | 74.3% (26/35) |
| Polarity | 100.0% (5/5) | 100.0% (2/2) | 100.0% (5/5) | 100.0% (2/2) | 80.0% (4/5) | 80.0% (4/5) |
| Prefix | 0.0% (0/4) | 0.0% (0/2) | 0.0% (0/4) | 0.0% (0/2) | 0.0% (0/4) | 0.0% (0/4) |
| PronType | 4.3% (1/23) | 55.6% (5/9) | 4.3% (1/23) | 55.6% (5/9) | 0.0% (0/23) | 4.3% (1/23) |
| Tense | 100.0% (27/27) | 100.0% (15/15) | 100.0% (27/27) | 100.0% (15/15) | 96.3% (26/27) | 85.2% (23/27) |
| Thematic | 60.0% (3/5) | 0.0% (0/1) | 20.0% (1/5) | 0.0% (0/1) | 0.0% (0/5) | 0.0% (0/5) |
| VerbForm | 88.9% (8/9) | 100.0% (5/5) | 88.9% (8/9) | 100.0% (5/5) | 44.4% (4/9) | 44.4% (4/9) |

## Do flags mean anything?

Flags only earn trust if unflagged words are clearly more accurate.

| Hints | Memory | Unflagged, exact | Flagged, exact |
|---|---|---|---|
| none | none | 73.7% (191/259) | 39.1% (9/23) |
| half | none | 76.1% (194/255) | 54.5% (12/22) |
| stem | none | 55.1% (97/176) | 21.1% (4/19) |
| stem+half | none | 74.5% (111/149) | 35.7% (5/14) |

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
| þēah | though | however.ADV |
| styċċe-mǣl-um | piece-meal-DAT.PL | piecemeal.ADV |
| hunt-oð-e | hunt-NMLZ-DAT.SG | hunting-DAT.SG |
| þǣm | DEM.DIST.DAT.SG.N | DET.DEF.DAT.SG.M |
| un-friþ-e | un-peace-DAT.SG | NEG-peace-DAT.SG |
| ðæt | DET.DEF.NOM.SG.N | COMP |
| ōþr-e | other-ACC.SG.F.STR | other-DAT.SG.F.WK |
| Norð-mann-a | north-man-GEN.PL | Norseman-GEN.PL |
| wǣr-e | be.PST-SJV.SG | be.PST.SJV.SG |
| symle | always | always.ADV |
| Ēaste-werd | east-ward | eastward.ADV? |
| syx-tiġ | six-ty | sixty |
| hwēne | a.little | a.little.ADV |
| brǣd-r-e | broad-CMP-NOM.SG.N.WK | broad-CMP.NOM.SG.N.STR? |
| midde-weard | middle-ward | midward.ADV? |
| brād-r-e | broad-CMP-NOM.SG.N.WK | broad-CMP.NOM.SG.N.STR |
| cwæð | say.PST.IND.3SG | say-PST.IND.3SG |
| ǣlċ-e | every-INS.SG.M.STR | each-DAT.SG.M.STR |
| seġl-i-an | sail-THM-INF | sail-INF |
| on | in | on |
| stēor-bord | steering-board.ACC.SG | steer-board.ACC.SG |
| Wīsl-e-mūð-an | Vistula-NOM.SG-river.mouth-ACC.SG | Vistula-mouth-ACC.SG |
| lī-ð | lie-PRS.IND.3SG | lie.PRS.IND.3SG |
| lī-ð | lie-PRS.IND.3SG | lie.PRS.IND.3SG |
| mȳr-an | mare-GEN.SG | mare-GEN.PL |
