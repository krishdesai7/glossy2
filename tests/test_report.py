from glossy2.evaluate import TokenScore
from glossy2.report import memory_effect, render_report


def token(index, exact=True, flagged=False, gloss="land-DAT.SG"):
    return TokenScore(
        0, index, "lande", "land-DAT.SG", gloss, exact, exact, {"Case": exact}, exact, exact,
        None, flagged, False, ["ambiguous"] if flagged else [],
    )


RUN = {"level": "none", "memory": "none", "scores": [token(0), token(1, False, True, "x-ACC")], "effect": None}
BASELINE = [token(0)]


def report(**changes):
    values = dict(
        name="Ohthere", split="test", sentences=60, runs=[RUN], baselines={"YCOE most-common tag": BASELINE},
        baseline_notes={"CLTK Stanza": "not installed"}, cost_note="tokens: 10 in, 5 out",
    )
    return render_report(**{**values, **changes})


def test_report_sections():
    text = report()
    for heading in ["Accuracy by hint level", "Per feature", "Do flags mean anything", "Baselines", "Sample of real errors", "Read this first"]:
        assert heading in text


def test_report_caveats():
    text = report()
    assert "15 sentences" in text and "dev" in text
    assert "remember" in text
    assert "lemma" in text.lower() and "harder" in text
    assert "recall" in text or "what the human marked" in text
    assert "YCOE" in text and "York" in text
    assert "reasoning" in text


def test_baseline_has_no_exact_number():
    rows = [line for line in report().splitlines() if line.startswith("| YCOE most-common")]
    assert "n/a" in rows[0]


def test_baseline_note_shown():
    assert "not installed" in report()


def test_error_sample_fixed():
    assert report() == report()
    assert "x-ACC" in report() and "land-DAT.SG" in report()


def test_failed_sentences_reported():
    failed = TokenScore(0, 0, "x", "y", "???", False, False, {}, None, None, None, True, True, ["analysis_failed"])
    run = {"level": "none", "memory": "none", "scores": [failed], "effect": None}
    assert "1 token" in report(runs=[run]) and "failed" in report(runs=[run])


def test_memory_effect():
    from glossy2.memory import Memory
    from glossy2.models import GoldSentence, GoldToken, Segment

    gold = GoldSentence(0, "m", [GoldToken("lande", "", [Segment("lande", "wrong-GLOSS")], "wrong-GLOSS")], "")
    memory = Memory.from_gold([gold], "m")
    followed = token(0, False, gloss="wrong-GLOSS")
    resisted = token(1, True)
    elsewhere = TokenScore(0, 2, "zzz", "a", "a", True, True, {}, None, None, None, False, False, [])
    effect = memory_effect([followed, resisted, elsewhere], memory)
    assert effect == {"in_memory": (1, 2), "not_in_memory": (1, 1), "wrong_top": 2, "misled": 1}


def test_memory_section_shown():
    run = {**RUN, "memory": "dev", "effect": {"in_memory": (1, 2), "not_in_memory": (1, 1), "wrong_top": 2, "misled": 1}}
    text = report(runs=[run])
    assert "Memory" in text and "misled" in text


def test_same_words_column_shown():
    assert "same words at every level" in report()


def test_baseline_shows_na_for_features_it_cannot_produce():
    from glossy2.evaluate import TokenScore as T

    scores = [T(0, 0, "x", "y", "", None, False, {"Number": False, "Case": True}, None, None, False, False, False)]
    text = report(baselines={"YCOE most-common tag": scores})
    number = next(l for l in text.splitlines() if l.startswith("| Number "))
    case = next(l for l in text.splitlines() if l.startswith("| Case "))
    assert number.rstrip(" |").endswith("n/a") and "100.0%" in case
    row = next(l for l in text.splitlines() if l.startswith("| YCOE most-common"))
    assert "0.0%" not in row


def test_echoed_hint_wording_is_honest():
    text = report()
    assert "a hint echoed back can't raise a score" not in text
    assert "whole-gloss" in text.lower()


def test_memory_section_says_it_measures_no_gain():
    run = {**RUN, "memory": "dev", "effect": {"in_memory": (1, 2), "not_in_memory": (1, 1), "wrong_top": 2, "misled": 1}}
    text = report(runs=[run])
    assert "did earlier glosses help" not in text
    assert "not a measure of memory's effect" in text and "wasn't run" in text


def test_report_says_when_runs_used_memory():
    run = {**RUN, "memory": "dev", "effect": {"in_memory": (1, 2), "not_in_memory": (1, 1), "wrong_top": 2, "misled": 1}}
    assert "worked-example sentences were also supplied as memory" in report(runs=[run])


def test_report_states_share_of_errors_unflagged():
    assert "1 of the 1 wrong glosses" not in report()
    assert "0 of the 1 wrong glosses carried no flag" in report()
