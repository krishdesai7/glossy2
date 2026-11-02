import re

import pytest

from glossy2 import cli
from glossy2.analyze import Context
from tests.fakes import FakeDictionary, FakeYcoe


def echo(messages):
    state_words = re.findall(r"^\d+\. (.+)$", messages[-1]["content"], re.M)
    return {"words": [
        {"index": i, "segments": [{"form": w, "gloss": "thing"}], "lemma": None, "upos": "NOUN", "feats": {}, "meaning": "thing"}
        for i, w in enumerate(state_words)
    ]}


@pytest.fixture
def harness(monkeypatch, tmp_path):
    state = {"calls": 0, "exclude": None, "contexts": []}

    def complete(messages):
        state["calls"] += 1
        return echo(messages)

    def sources(exclude):
        state["exclude"] = exclude
        return FakeYcoe(), FakeDictionary()

    monkeypatch.setattr(cli, "_eval_sources", sources)
    monkeypatch.setattr(cli, "_complete", complete)
    monkeypatch.setattr(cli, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(cli, "MEMORY_PATH", tmp_path / "memory.jsonl")
    monkeypatch.setattr(cli, "_cltk_baseline", lambda sentences, corrections, dictionary: (None, "not installed"))
    return state


def test_default_excludes_orosius(harness):
    assert cli.main(["eval", "--hints", "none", "--limit", "1"]) == 0
    assert harness["exclude"] == {"coorosiu.o2.pos"}


def test_full_run_asks_first(harness, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert cli.main(["eval", "--hints", "none"]) == 0
    assert harness["calls"] == 0
    out = capsys.readouterr().out
    assert "tokens" in out and "$" in out


def test_limit_skips_prompt(harness, monkeypatch):
    def boom(prompt):
        raise AssertionError("should not ask")

    monkeypatch.setattr("builtins.input", boom)
    assert cli.main(["eval", "--hints", "none", "--limit", "2"]) == 0
    assert harness["calls"] == 2


def test_limit_writes_no_report(harness, tmp_path):
    cli.main(["eval", "--hints", "none", "--limit", "1"])
    assert not (tmp_path / "reports").exists()


def test_default_split_dev(harness):
    cli.main(["eval", "--hints", "none", "--yes"])
    assert harness["calls"] == 15


def test_dev_report_kept_apart(harness, tmp_path):
    cli.main(["eval", "--hints", "none", "--yes"])
    assert (tmp_path / "reports" / "eval-dev.md").exists()
    assert not (tmp_path / "reports" / "eval.md").exists()


def test_test_split_needs_yes(harness, monkeypatch):
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "n")
    assert cli.main(["eval", "--hints", "none", "--split", "test", "--limit", "1"]) == 0
    assert asked and harness["calls"] == 0


def test_runs_accumulate_in_one_report(harness, tmp_path):
    cli.main(["eval", "--hints", "none", "--split", "test", "--limit", "1", "--yes"])
    cli.main(["eval", "--hints", "stem", "--split", "test", "--yes"])
    cli.main(["eval", "--hints", "none", "--split", "test", "--yes"])
    text = (tmp_path / "reports" / "eval.md").read_text(encoding="utf-8")
    assert "| none |" in text and "| stem |" in text


def test_all_levels(harness):
    cli.main(["eval", "--hints", "all", "--yes"])
    assert harness["calls"] == 60


def test_gold_path_all_test(harness, tmp_path):
    source = tmp_path / "new.tex"
    source.write_text("\\begin{document}\n\\ex{\\gll land-e\\\\\nland-\\textsc{dat.sg}\\\\\n\\glt `x'}\n", encoding="utf-8")
    assert cli.main(["eval", "--hints", "none", "--gold", str(source), "--name", "new", "--yes"]) == 0
    assert harness["calls"] == 1
    assert (tmp_path / "reports" / "eval-new.md").exists()


def test_gold_needs_name(harness, tmp_path, capsys):
    source = tmp_path / "new.tex"
    source.write_text("\\begin{document}\n", encoding="utf-8")
    assert cli.main(["eval", "--hints", "none", "--gold", str(source)]) == 2


def test_gold_exclude_passed(harness, tmp_path):
    source = tmp_path / "new.tex"
    source.write_text("\\begin{document}\n\\ex{\\gll land-e\\\\\nland-\\textsc{dat.sg}\\\\\n\\glt `x'}\n", encoding="utf-8")
    cli.main(["eval", "--hints", "none", "--gold", str(source), "--name", "new", "--exclude-ycoe", "a.pos", "--yes"])
    assert harness["exclude"] == {"a.pos"}


def test_eval_never_writes_memory(harness, tmp_path):
    path = tmp_path / "memory.jsonl"
    path.write_text('{"form":"x","gloss":"y","lemma":null,"source":"s","tier":"human"}\n', encoding="utf-8")
    before = path.read_bytes()
    cli.main(["eval", "--hints", "none", "--limit", "1", "--memory", "dev", "--split", "test", "--yes"])
    assert path.read_bytes() == before


def test_memory_rejects_dev_on_dev(harness, capsys):
    assert cli.main(["eval", "--hints", "none", "--memory", "dev", "--yes"]) == 2
    assert "memory" in capsys.readouterr().err


def test_memory_rejects_leak(harness, capsys):
    assert cli.main(["eval", "--hints", "none", "--split", "test", "--memory", "ohthere", "--yes"]) == 2
    assert harness["calls"] == 0


def test_memory_excludes_scored(harness, monkeypatch):
    captured = {}
    original = cli._eval_memory

    def spy(name, dev):
        captured["memory"] = original(name, dev)
        return captured["memory"]

    monkeypatch.setattr(cli, "_eval_memory", spy)
    cli.main(["eval", "--hints", "none", "--split", "test", "--memory", "dev", "--limit", "1", "--yes"])
    from glossy2.gold import load_gold, split_sentences

    dev, test = split_sentences(load_gold(cli.OHTHERE_TEX, cli.TINA_CORRECTIONS))
    forms = {t.form for s in dev for t in s.tokens}
    only_in_test = next(t for s in test for t in s.tokens if t.form not in forms and "-" not in t.form and t.form.isalpha())
    assert captured["memory"].human(only_in_test.form) == []


def test_missing_key_clean_exit(harness, monkeypatch, capsys):
    from glossy2.llm import MissingKeyError

    def complete(messages):
        raise MissingKeyError()

    monkeypatch.setattr(cli, "_complete", complete)
    assert cli.main(["eval", "--hints", "none", "--limit", "1"]) == 2
    assert ".env" in capsys.readouterr().err
