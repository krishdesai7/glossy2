import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from glossy2 import llm

MESSAGES = [{"role": "user", "content": "hello"}]


def reply(content='{"ok": true}', finish="stop"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


class FakeClient:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def status_error(kind, status, message="nope"):
    request = httpx.Request("POST", "https://api.moonshot.ai/v1/chat/completions")
    return kind(message, response=httpx.Response(status, request=request), body=None)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm, "_sleep", lambda seconds: None)


def test_cache_hit_no_second_call(tmp_path):
    client = FakeClient(reply())
    assert llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path) == {"ok": True}
    assert llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path) == {"ok": True}
    assert client.calls == 1


def test_key_includes_model(tmp_path, monkeypatch):
    client = FakeClient(reply())
    llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    monkeypatch.setenv("MOONSHOT_MODEL", "kimi-k3")
    llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    assert client.calls == 2


def test_failure_not_cached(tmp_path):
    bad = FakeClient(reply("not json"))
    with pytest.raises(llm.LLMError):
        llm.complete_json(MESSAGES, client=bad, cache_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []
    good = FakeClient(reply())
    assert llm.complete_json(MESSAGES, client=good, cache_dir=tmp_path) == {"ok": True}
    assert good.calls == 1


def test_retries_on_429(tmp_path):
    client = FakeClient(status_error(openai.RateLimitError, 429), reply())
    assert llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path) == {"ok": True}
    assert client.calls == 2


def test_gives_up(tmp_path):
    client = FakeClient(status_error(openai.RateLimitError, 429))
    with pytest.raises(llm.LLMError):
        llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    assert client.calls == 3


def test_truncated_is_error(tmp_path):
    client = FakeClient(reply('{"ok": true}', finish="length"))
    with pytest.raises(llm.LLMError):
        llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)


def test_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(llm.MissingKeyError) as error:
        llm.complete_json(MESSAGES, cache_dir=tmp_path)
    assert ".env" in str(error.value)


def test_key_never_in_error(tmp_path):
    secret = "sk-very-secret"
    client = FakeClient(status_error(openai.AuthenticationError, 401, f"bad key {secret}"))
    with pytest.raises(llm.MissingKeyError) as error:
        llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    assert secret not in str(error.value)
    assert client.calls == 1


def test_usage_counted(tmp_path):
    before = llm.usage_totals()
    client = FakeClient(reply())
    llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    llm.complete_json(MESSAGES, client=client, cache_dir=tmp_path)
    after = llm.usage_totals()
    assert (after[0] - before[0], after[1] - before[1]) == (10, 5)


def test_estimate_cost():
    assert llm.estimate_cost(1_000_000, 1_000_000, "kimi-k3.1-pro") == pytest.approx(12.0)
    assert llm.estimate_cost(1, 1, "unknown-model") != llm.estimate_cost(1, 1, "unknown-model")
