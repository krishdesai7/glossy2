# Evaluation: Ohthere and Wulfstan

Split: `dev`. 15 sentences. Model kimi-k3.1-pro, about $1.67 at list price.

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
| none | none | 47.7% (93/195) | 59.6% (168/282) | 70.2% (198/282) | 84.5% (202/239) | 90.8% (217/239) | 71.4% (5/7) |
| half | none | 56.4% (110/195) | 65.0% (180/277) | 74.1% (209/282) | 84.1% (201/239) | 90.4% (216/239) | 71.4% (5/7) |
| stem | none | 60.5% (118/195) | 60.5% (118/195) | 77.7% (219/282) | n/a | n/a | 85.7% (6/7) |
| stem+half | none | 61.0% (119/195) | 64.4% (105/163) | 74.8% (211/282) | n/a | n/a | 85.7% (6/7) |

Use the first accuracy column to compare hint levels. It scores the same words each time, though at hint levels with features given, a word can match partly because its hints were given. The second column drops words with nothing withheld, so its word set changes per level and easy function words leave it at `stem`.

0 token analyses failed outright (bad or missing model response). They count as wrong.

## Per feature

| Feature | none / memory none | half / memory none | stem / memory none | stem+half / memory none | YCOE most-common tag | CLTK Stanza |
|---|---|---|---|---|---|---|
| Aspect | 87.5% (7/8) | 100.0% (4/4) | 87.5% (7/8) | 100.0% (4/4) | 0.0% (0/8) | 0.0% (0/8) |
| Case | 94.8% (128/135) | 98.6% (71/72) | 94.1% (127/135) | 97.2% (70/72) | 56.3% (76/135) | 82.2% (111/135) |
| Declension | 87.5% (28/32) | 100.0% (12/12) | 93.8% (30/32) | 91.7% (11/12) | 0.0% (0/32) | 0.0% (0/32) |
| Definite | 95.2% (20/21) | 100.0% (11/11) | 100.0% (21/21) | 100.0% (11/11) | 0.0% (0/21) | 0.0% (0/21) |
| Degree | 100.0% (8/8) | 100.0% (7/7) | 100.0% (8/8) | 100.0% (7/7) | 50.0% (4/8) | 87.5% (7/8) |
| Deixis | 0.0% (0/3) | 50.0% (1/2) | 0.0% (0/3) | 50.0% (1/2) | 0.0% (0/3) | 0.0% (0/3) |
| Derivation | 66.7% (2/3) | 0.0% (0/1) | 66.7% (2/3) | 0.0% (0/1) | 0.0% (0/3) | 0.0% (0/3) |
| Form | 63.6% (7/11) | 80.0% (4/5) | 54.5% (6/11) | 100.0% (5/5) | 0.0% (0/11) | 0.0% (0/11) |
| Gender | 85.7% (60/70) | 83.3% (30/36) | 87.1% (61/70) | 97.2% (35/36) | 0.0% (0/70) | 62.9% (44/70) |
| Mood | 88.2% (30/34) | 93.8% (15/16) | 88.2% (30/34) | 81.2% (13/16) | 76.5% (26/34) | 79.4% (27/34) |
| Number | 97.6% (165/169) | 100.0% (82/82) | 98.2% (166/169) | 100.0% (82/82) | 0.0% (0/169) | 86.4% (146/169) |
| PartType | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | 0.0% (0/4) | 0.0% (0/4) |
| Person | 100.0% (35/35) | 94.4% (17/18) | 91.4% (32/35) | 94.4% (17/18) | 0.0% (0/35) | 74.3% (26/35) |
| Polarity | 100.0% (5/5) | 100.0% (2/2) | 100.0% (5/5) | 100.0% (2/2) | 80.0% (4/5) | 80.0% (4/5) |
| Prefix | 100.0% (4/4) | 100.0% (2/2) | 100.0% (4/4) | 100.0% (2/2) | 0.0% (0/4) | 0.0% (0/4) |
| PronType | 82.6% (19/23) | 88.9% (8/9) | 87.0% (20/23) | 88.9% (8/9) | 0.0% (0/23) | 4.3% (1/23) |
| Tense | 100.0% (27/27) | 100.0% (15/15) | 100.0% (27/27) | 100.0% (15/15) | 96.3% (26/27) | 85.2% (23/27) |
| Thematic | 80.0% (4/5) | 100.0% (1/1) | 100.0% (5/5) | 100.0% (1/1) | 0.0% (0/5) | 0.0% (0/5) |
| VerbForm | 88.9% (8/9) | 100.0% (5/5) | 88.9% (8/9) | 100.0% (5/5) | 44.4% (4/9) | 44.4% (4/9) |

## Do flags mean anything?

Flags only earn trust if unflagged words are clearly more accurate.

| Hints | Memory | Unflagged, exact | Flagged, exact |
|---|---|---|---|
| none | none | 62.1% (157/253) | 37.9% (11/29) |
| half | none | 67.6% (171/253) | 37.5% (9/24) |
| stem | none | 63.4% (111/175) | 35.0% (7/20) |
| stem+half | none | 66.0% (97/147) | 50.0% (8/16) |

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
| sǣ-d-e | say-PST-IND.3SG | say.PST.IND.3SG |
| eal | all.NOM.SG.N | all.NOM.SG.N.STR |
| fēaw-um | few-DAT.PL.STR | few.DAT.PL.STR |
| wol-d-e | want-PST-SJV.SG | want.PST.IND.3SG? |
| long-e | long-ADV | long.ADV |
| norþ-ryht-e | north-right-ADV | north.right.ADV? |
| wēstenn-e | wasteland-DAT.SG | waste.DAT.SG |
| ðæt | DET.DEF.NOM.SG.N | COMP |
| eall | all.NOM.SG.N | all.NOM.SG.N.STR |
| ōðre | other-NOM.PL.M.STR | other.NOM.PL.STR |
| hwal-as | whale-NOM.PL | whale.NOM.PL? |
| bi-ð | be.HAB-IND.3SG | be.HAB.IND.3SG |
| Þæt | DET.DEF.DAT.SG.N | DET.DEF.NOM.SG.N |
| dēor-a | animal-GEN.PL | wild.animal.GEN.PL |
| sċip-rāp-um | ship-rope-DAT.PL | ship.rope.DAT.PL |
| sēol-es | seal-GEN.SG | seal.GEN.SG |
| sǣ-d-e | say-PST-IND.3SG | say.PST.IND.3SG |
| wǣr-e | be.PST-SJV.SG | be.PST.SJV.SG |
| ēaste-weard | east-ward | east.ward |
| midde-weard | middle-ward | middle-ward.NOM.SG.N.STR |
| wīc-o-d-e | camp-THM-PST-IND.3SG | camp-PST-SJV.SG? |
| hæf-d-e | have-PST-IND.3SG | have-PST-SJV.SG? |
| hwīl-e | time-ACC.SG | while-ACC.SG |
| Wīsl-e-mūð-an | Vistula-NOM.SG-river.mouth-ACC.SG | Vistula.mouth.ACC.SG? |
| n-ǣniġ | NEG-any.NOM.SG.N.STR | no.NOM.SG.N.STR |
