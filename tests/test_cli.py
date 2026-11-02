import pytest

from glossy2 import cli
from glossy2.analyze import Context
from glossy2.llm import LLMError, MissingKeyError
from tests.fakes import FakeDictionary, FakeYcoe


def reply(*forms):
    return {"words": [
        {"index": i, "segments": [{"form": f, "gloss": "thing"}], "lemma": None, "upos": "NOUN", "feats": {}, "meaning": "thing"}
        for i, f in enumerate(forms)
    ]}


@pytest.fixture
def run(monkeypatch, tmp_path):
    state = {"responses": [], "calls": 0, "memory": tmp_path / "m.jsonl"}

    def complete(messages):
        state["calls"] += 1
        outcome = state["responses"].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(cli, "MEMORY_PATH", state["memory"])
    monkeypatch.setattr(cli, "_gloss_context", lambda memory: Context(FakeYcoe({"land": {"N^N": 1}}), FakeDictionary(), [], complete, memory))
    return state


def test_gloss(run, capsys):
    run["responses"] = [reply("land")]
    assert cli.main(["gloss", "land"]) == 0
    assert "thing" in capsys.readouterr().out


def test_gb4e_format(run, capsys):
    run["responses"] = [reply("land")]
    assert cli.main(["gloss", "land", "--format", "gb4e"]) == 0
    assert "\\gll" in capsys.readouterr().out


def test_cli_missing_key(run, capsys):
    run["responses"] = [MissingKeyError()]
    assert cli.main(["gloss", "land"]) == 2
    captured = capsys.readouterr()
    assert ".env" in captured.err and "Traceback" not in captured.err
    assert len(captured.err.strip().splitlines()) == 1


def test_cli_bad_hint(run, capsys):
    assert cli.main(["gloss", "on lande[noun"]) == 2
    assert "lande" in capsys.readouterr().err
    assert run["calls"] == 0


def test_cli_file_bad_hint_stops_before_any_call(run, capsys, tmp_path):
    path = tmp_path / "s.txt"
    path.write_text("land\nlande[\n", encoding="utf-8")
    assert cli.main(["gloss", "--file", str(path)]) == 2
    assert run["calls"] == 0


def test_cli_file_blank_lines(run, capsys, tmp_path):
    path = tmp_path / "s.txt"
    path.write_text("land\n\n   \nland\n", encoding="utf-8")
    run["responses"] = [LLMError("timed out"), reply("land")]
    assert cli.main(["gloss", "--file", str(path)]) == 0
    out = capsys.readouterr().out
    assert "timed out" in out and "thing" in out


def test_cli_missing_file(run, capsys, tmp_path):
    assert cli.main(["gloss", "--file", str(tmp_path / "none.txt")]) == 2
    assert "none.txt" in capsys.readouterr().err


def test_cli_no_args(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main([])
    assert error.value.code == 2
    assert "usage" in capsys.readouterr().err


def test_cli_gloss_no_text(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["gloss"])
    assert error.value.code == 2


def test_cli_remember(run, capsys, tmp_path):
    source = tmp_path / "text.tex"
    source.write_text("\\begin{document}\n\\ex{\\gll land-e þæt\\\\\nland-\\textsc{dat.sg} \\textsc{comp}\\\\\n\\glt `x'}\n", encoding="utf-8")
    assert cli.main(["remember", str(source), "--name", "demo"]) == 0
    assert "2 tokens" in capsys.readouterr().out
    assert '"human"' in run["memory"].read_text(encoding="utf-8")


def test_cli_records_machine_output(run):
    run["responses"] = [reply("land")]
    cli.main(["gloss", "land"])
    assert '"machine"' in run["memory"].read_text(encoding="utf-8")


def test_cli_no_record(run):
    run["responses"] = [reply("land")]
    cli.main(["gloss", "land", "--no-record"])
    assert not run["memory"].exists()
