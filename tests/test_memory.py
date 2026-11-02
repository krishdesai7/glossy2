from glossy2.analyze import Context, build_messages
from glossy2.memory import Memory
from glossy2.models import Flag, GoldSentence, GoldToken, InputWord, Segment, WordAnalysis
from tests.fakes import FakeDictionary, FakeYcoe


def gold(*pairs):
    tokens = [GoldToken(form, "", [Segment(form, gloss)], gloss) for form, gloss in pairs]
    return GoldSentence(0, "main", tokens, "")


def machine(form="lande", gloss="land-DAT.SG", flags=()):
    return WordAnalysis(form, segments=[Segment(form, gloss)], lemma="land", flags=list(flags))


def test_counts_readings():
    memory = Memory.from_gold([gold(("þæt", "COMP"), ("þæt", "COMP"), ("þæt", "DET.DEF.NOM.SG.N"))], "ohthere")
    assert memory.human("þæt") == [("COMP", 2, ["ohthere"]), ("DET.DEF.NOM.SG.N", 1, ["ohthere"])]


def test_normalised_lookup():
    memory = Memory.from_gold([gold(("ġehālgod", "hallow.PTCP"))], "x")
    assert memory.human("gehalgod") == [("hallow.PTCP", 1, ["x"])]


def test_machine_not_returned(tmp_path):
    path = tmp_path / "m.jsonl"
    memory = Memory.load(path)
    memory.record_machine([machine()], "run", path)
    assert memory.human("lande") == []
    assert Memory.load(path).human("lande") == []
    assert path.read_text().count('"machine"') == 1


def test_record_skips_flagged(tmp_path):
    path = tmp_path / "m.jsonl"
    memory = Memory.load(path)
    memory.record_machine([machine(flags=[Flag("ambiguous", "?")]), machine(flags=[Flag("analysis_failed", "?")])], "run", path)
    assert not path.exists() or path.read_text() == ""


def test_add_human_twice_same_source(tmp_path):
    path = tmp_path / "m.jsonl"
    memory = Memory.load(path)
    memory.add_human([gold(("land", "land"))], "ohthere", path)
    memory.add_human([gold(("land", "land"))], "ohthere", path)
    assert memory.human("land") == [("land", 1, ["ohthere"])]
    assert Memory.load(path).human("land") == [("land", 1, ["ohthere"])]


def test_add_human_keeps_machine_entries(tmp_path):
    path = tmp_path / "m.jsonl"
    memory = Memory.load(path)
    memory.record_machine([machine()], "run", path)
    memory.add_human([gold(("land", "land"))], "ohthere", path)
    assert path.read_text().count('"machine"') == 1


def test_persist_roundtrip(tmp_path):
    path = tmp_path / "m.jsonl"
    Memory.load(path).add_human([gold(("land", "land"))], "a", path)
    Memory.load(path).add_human([gold(("land", "earth"))], "b", path)
    assert {r[0] for r in Memory.load(path).human("land")} == {"land", "earth"}


def context(memory):
    return Context(ycoe=FakeYcoe(), dictionary=FakeDictionary(), examples=[], memory=memory)


def text(memory, form="gehalgod"):
    return "\n".join(m["content"] for m in build_messages([InputWord(form)], context(memory)))


def test_prompt_shows_human_memory():
    prompt = text(Memory.from_gold([gold(("gehalgod", "hallow.PTCP"))], "ohthere"))
    assert "hallow.PTCP x1 (ohthere)" in prompt
    assert "earlier human glosses, may not apply here" in prompt


def test_prompt_caps_readings_at_five():
    pairs = [("x", f"gloss{i}") for i in range(9)]
    prompt = text(Memory.from_gold([gold(*pairs)], "s"), "x")
    assert sum(f"gloss{i} x1" in prompt for i in range(9)) == 5


def test_prompt_no_machine_memory(tmp_path):
    path = tmp_path / "m.jsonl"
    memory = Memory.load(path)
    memory.record_machine([machine("gehalgod", "wrong.GLOSS")], "run", path)
    assert "wrong.GLOSS" not in text(memory)


def test_prompt_no_memory():
    assert "earlier human glosses" not in text(None)


def test_memory_in_user_message_after_shared_prefix():
    memory = Memory.from_gold([gold(("gehalgod", "hallow.PTCP"))], "s")
    assert "hallow.PTCP" not in build_messages([InputWord("gehalgod")], context(memory))[0]["content"]


def test_memory_not_used_as_hint():
    from glossy2.analyze import analyze_sentence

    memory = Memory.from_gold([gold(("lande", "wrong-ACC.PL"))], "s")
    response = {"words": [{"index": 0, "segments": [{"form": "land", "gloss": "land"}, {"form": "e", "gloss": "DAT.SG"}], "lemma": "land", "upos": "NOUN", "feats": {"Case": "Dat"}, "meaning": "land"}]}
    ctx = Context(FakeYcoe({"lande": {"N^D": 1}}), FakeDictionary(), [], lambda messages: response, memory)
    result = analyze_sentence([InputWord("lande")], ctx)[0]
    assert result.segments[1].gloss == "DAT.SG"
    assert "hint_conflict" not in [f.code for f in result.flags]
