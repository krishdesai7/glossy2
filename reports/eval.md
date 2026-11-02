# Evaluation: Ohthere and Wulfstan

Split: `test`. 60 sentences. Model kimi-k3.1-pro, about $8.68 at list price, before any caching discount.

## Read this first

- **What was tuned on what.** The prompt was tuned on 15 sentences (`dev`), which also supply the model's worked examples. The numbers below come from text that was not used for either, unless this report says it is the `dev` report.
- **The model may remember this text.** Ohthere is famous, so the model may have seen it in training. Scores here may run higher than on text it has never seen.
- **YCOE's copy was removed.** YCOE's Orosius contains this passage, so that file was left out of the evidence.
- **What counts as right.** Words with nothing withheld aren't scored. A feature counts only where the human marked it, so these numbers show recall of what the human marked. An extra feature the human left unmarked is ignored rather than counted wrong. Per-feature and meaning scores really are limited to what was withheld. Whole-gloss scores compare the entire gloss, so a word with some features hinted can match partly because of those hints.
- **Lemma numbers are a small, harder-than-average sample.** They use only the human Tina corrections, which are mostly words the old engine got wrong.
- **Settings.** Model reasoning was turned off to keep cost and time down, and Moonshot doesn't allow a fixed temperature on this model. Cached responses make a rerun reproducible, but a rerun without the cache could differ slightly.
- **Sources.** York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE), used under its conditions for scholarly research. Dictionary data from Wiktionary (CC BY-SA) via wiktextract and kaikki.org.
- **Memory.** The worked-example sentences were also supplied as memory in runs marked `dev`. No scored sentence was in memory.

## Accuracy by hint level

| Hints | Memory | Words with grammar, same words at every level | Whole gloss exact, withheld only | Segmentation | Meaning exact | Meaning (any dictionary sense) | Lemma |
|---|---|---|---|---|---|---|---|
| none | dev | 71.1% (730/1027) | 75.3% (1077/1430) | 90.8% (1298/1430) | 83.7% (945/1129) | 87.1% (983/1129) | 100.0% (14/14) |
| half | dev | 74.5% (765/1027) | 77.2% (1076/1394) | 90.8% (1299/1430) | 83.2% (939/1129) | 86.7% (979/1129) | 100.0% (14/14) |
| stem | dev | 76.5% (786/1027) | 76.5% (786/1027) | 90.9% (1300/1430) | n/a | n/a | 100.0% (14/14) |
| stem+half | dev | 81.7% (839/1027) | 81.1% (715/882) | 91.4% (1307/1430) | n/a | n/a | 100.0% (14/14) |

Use the first accuracy column to compare hint levels, because it scores the same words each time. The second drops words with nothing withheld, so its word set changes per level and easy function words leave it at `stem`. In both, a word can match partly because of its hints, so don't read the rise across levels as pure gain.

0 token analyses failed outright (bad or missing model response). They count as wrong.

## Per feature

| Feature | none / memory dev | half / memory dev | stem / memory dev | stem+half / memory dev | YCOE most-common tag | CLTK Stanza |
|---|---|---|---|---|---|---|
| Aspect | 91.3% (21/23) | 88.2% (15/17) | 91.3% (21/23) | 82.4% (14/17) | n/a | n/a |
| Case | 93.4% (683/731) | 95.3% (341/358) | 94.1% (688/731) | 95.3% (341/358) | 52.5% (384/731) | 71.4% (522/731) |
| Declension | 86.0% (98/114) | 82.5% (47/57) | 86.0% (98/114) | 86.0% (49/57) | n/a | n/a |
| Definite | 96.7% (118/122) | 97.0% (64/66) | 95.1% (116/122) | 100.0% (66/66) | n/a | 0.0% (0/122) |
| Degree | 87.0% (20/23) | 93.8% (15/16) | 100.0% (23/23) | 100.0% (16/16) | 78.3% (18/23) | 34.8% (8/23) |
| Deixis | 52.6% (20/38) | 64.3% (9/14) | 47.4% (18/38) | 64.3% (9/14) | n/a | n/a |
| Derivation | 44.4% (4/9) | 50.0% (2/4) | 55.6% (5/9) | 50.0% (2/4) | n/a | n/a |
| Form | 70.2% (33/47) | 71.0% (22/31) | 68.1% (32/47) | 67.7% (21/31) | n/a | n/a |
| Gender | 91.4% (310/339) | 91.9% (158/172) | 89.4% (303/339) | 86.6% (149/172) | n/a | 56.9% (193/339) |
| Mood | 95.1% (173/182) | 93.7% (89/95) | 92.9% (169/182) | 95.8% (91/95) | 74.2% (135/182) | 83.0% (151/182) |
| Number | 97.2% (875/900) | 97.7% (474/485) | 97.1% (874/900) | 97.9% (475/485) | n/a | 76.7% (690/900) |
| PartType | 100.0% (18/18) | 100.0% (9/9) | 94.4% (17/18) | 100.0% (9/9) | n/a | n/a |
| Person | 98.7% (222/225) | 96.1% (98/102) | 98.2% (221/225) | 97.1% (99/102) | n/a | 73.3% (165/225) |
| Polarity | 100.0% (11/11) | 100.0% (8/8) | 100.0% (11/11) | 100.0% (8/8) | 45.5% (5/11) | 45.5% (5/11) |
| Prefix | 73.9% (17/23) | 90.0% (9/10) | 78.3% (18/23) | 80.0% (8/10) | n/a | n/a |
| PronType | 87.3% (144/165) | 93.4% (85/91) | 84.8% (140/165) | 92.3% (84/91) | n/a | 11.5% (19/165) |
| Tense | 97.5% (159/163) | 97.6% (83/85) | 98.8% (161/163) | 100.0% (85/85) | 85.3% (139/163) | 82.8% (135/163) |
| Thematic | 66.7% (6/9) | 75.0% (3/4) | 77.8% (7/9) | 50.0% (2/4) | n/a | n/a |
| VerbForm | 94.6% (35/37) | 94.4% (17/18) | 91.9% (34/37) | 94.4% (17/18) | 62.2% (23/37) | 35.1% (13/37) |
| Voice | 100.0% (1/1) | n/a | 100.0% (1/1) | n/a | n/a | 0.0% (0/1) |

## Do flags mean anything?

Flags only earn trust if unflagged words are clearly more accurate.

| Hints | Memory | Unflagged, exact | Flagged, exact |
|---|---|---|---|
| none | dev | 78.4% (1007/1284) | 47.9% (70/146) |
| half | dev | 80.1% (1005/1254) | 50.7% (71/140) |
| stem | dev | 78.1% (714/914) | 63.7% (72/113) |
| stem+half | dev | 82.7% (640/774) | 69.4% (75/108) |

At `none`, 277 of the 353 wrong glosses carried no flag.
At `half`, 249 of the 318 wrong glosses carried no flag.
At `stem`, 200 of the 241 wrong glosses carried no flag.
At `stem+half`, 134 of the 167 wrong glosses carried no flag.

No flag doesn't mean correct. Some of these are convention differences rather than wrong analyses, which the error sample below shows.

## Words in memory against words not in memory

This is not a measure of memory's effect. Words in memory are mostly frequent function words, which are easier anyway, and the comparison run with no memory wasn't run. The last column does show a real cost: where the remembered reading was wrong for this word, how often the model repeated it.

| Hints | Memory | In memory, exact | Not in memory, exact | Wrong remembered reading | Model misled |
|---|---|---|---|---|---|
| none | dev | 91.0% (689/757) | 57.7% (388/673) | 186 | 16 |
| half | dev | 93.0% (679/730) | 59.8% (397/664) | 186 | 8 |
| stem | dev | 89.1% (400/449) | 66.8% (386/578) | 186 | 12 |
| stem+half | dev | 92.8% (360/388) | 71.9% (355/494) | 186 | 9 |

## Baselines

| Baseline | Whole gloss exact | Segmentation | Lemma |
|---|---|---|---|
| YCOE most-common tag | n/a | n/a | n/a |
| CLTK Stanza | n/a | n/a | 42.9% (6/14) |

Neither baseline produces glosses or morpheme splits. Compare them on the features above, where `n/a` means the baseline can't produce that feature at all.

## Sample of real errors

From the `none` run. A `?` on a gloss means the tool flagged it.

| Word | Human gloss | Tool's gloss |
|---|---|---|
| norþ-weard-um | north-ward-DAT.SG.N.STR | north-ward-DAT.SG? |
| norþ-an | north-from | from.the.north |
| n-ān | NEG-one.ACC.SG.N | no.ACC.SG.N.STR |
| ðā | DEM.DIST.NOM.PL | DET.DEF.NOM.PL |
| lȳtl-e | little-ACC.SG.M.WK | little-ACC.SG.N.WK |
| hys | 3SG.M.GEN | 3SG.M.POSS |
| ett-an | graze-INF | graze.INF |
| bū-d-e | dwell-PST-IND.3SG | dwell-PST-SJV.SG? |
| ān | one.NOM.SG.M | one.NOM.SG.M.STR |
| on | in | on |
| twēġen | two.ACC.M | two.ACC.PL.M |
| þǣm | DEM.DIST.DAT.PL | DET.DEF.DAT.PL |
| yrn-ende | run-PART.PRS | run-PART-NOM.SG.N.WK |
| land-e | land.DAT.SG | land-DAT.SG |
| Wīsl-e | Vistula-DAT.SG | Vistula-NOM.SG |
| Ilfing | Elbląg.NOM.SG | Ilfing.ACC.SG? |
| eorð-an | ground-DAT.SG | earth-DAT.SG |
| hyra | 3PL.GEN | 3PL.POSS |
| his | 3SG.M.GEN | 3SG.M.POSS |
| ā-lē-d | out-lay-PART.NOM.SG.N.STR | PFX-lay-PART.NOM.SG.N.STR |
| un-ġe-fōg-e | un-PFX-joining-ADV | un-moderation-ADV? |
| eall | all.NOM.PL.N | all.NOM.SG.N.STR |
| for-bærn-ed | for-burn-PART.NOM.SG.M.STR | burn.up.PART.NOM.SG.M.STR |
| mǣġð | power.NOM.SG | tribe.NOM.SG |
| sam | same | whether |
