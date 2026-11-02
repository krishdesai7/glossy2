"""Moonshot calls with a disk cache, so repeat runs are free and reproducible."""

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import openai

BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MODEL = "kimi-k3.1-pro"
MAX_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 16000
TIMEOUT_SECONDS = 180
# Reasoning costs about 10x the output tokens, too slow and expensive for a whole text.
REQUEST_OPTIONS = {"thinking": {"type": "disabled"}}
# USD per million tokens as (input, output, cached input), from Moonshot, 2026-11-01.
PRICES = {
    "kimi-k3.1-pro": (2.00, 10.00, 0.20),
    "kimi-k3.1-pro-highspeed": (4.00, 20.00, 0.20),
    "kimi-k3": (3.00, 15.00, 0.30),
    "kimi-k2.7-code": (0.95, 4.00, 0.19),
    "kimi-k2.7-code-highspeed": (1.90, 8.00, 0.38),
    "kimi-k2.6": (0.95, 4.00, 0.16),
}
_KEY_HELP = "Moonshot rejected or couldn't find the API key. Put it in .env as MOONSHOT_API_KEY=..."

_usage = [0, 0]
_usage_lock = threading.Lock()
_sleep = time.sleep


class LLMError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class CacheMiss(RuntimeError):
    """A cache-only run needed a response that isn't cached. Nothing was sent."""


class MissingKeyError(RuntimeError):
    def __init__(self):
        super().__init__(_KEY_HELP)


def current_model() -> str:
    return os.environ.get("MOONSHOT_MODEL", DEFAULT_MODEL)


def _read_key() -> str | None:
    if key := os.environ.get("MOONSHOT_API_KEY"):
        return key
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "MOONSHOT_API_KEY" and value.strip():
                return value.strip().strip("'\"")
    return None


def _make_client() -> openai.OpenAI:
    key = _read_key()
    if not key:
        raise MissingKeyError()
    return openai.OpenAI(api_key=key, base_url=BASE_URL, timeout=TIMEOUT_SECONDS, max_retries=0)


def _cache_path(cache_dir: Path, model: str, messages: list[dict]) -> Path:
    payload = json.dumps([model, REQUEST_OPTIONS, messages], ensure_ascii=False, sort_keys=True)
    return Path(cache_dir) / f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}.json"


def _write_cache(path: Path, parsed: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _attempt(client, model: str, messages: list[dict]) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=MAX_OUTPUT_TOKENS,
        extra_body=REQUEST_OPTIONS,
    )
    usage = response.usage
    if usage:
        with _usage_lock:
            _usage[0] += usage.prompt_tokens or 0
            _usage[1] += usage.completion_tokens or 0
    if not response.choices:
        raise LLMError("the response had no content")
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise LLMError("the response was cut off")
    try:
        parsed = json.loads(choice.message.content or "")
    except json.JSONDecodeError as error:
        raise LLMError("the response wasn't valid JSON") from error
    if not isinstance(parsed, dict):
        raise LLMError("the response wasn't a JSON object")
    return parsed


def forget_cached(messages: list[dict], *, cache_dir: Path = Path(".llm-cache")) -> None:
    _cache_path(cache_dir, current_model(), messages).unlink(missing_ok=True)


def complete_json(
    messages: list[dict], *, client=None, cache_dir: Path = Path(".llm-cache"), cache_only: bool = False
) -> dict:
    model = current_model()
    path = _cache_path(cache_dir, model, messages)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if cache_only:
        raise CacheMiss()
    client = client or _make_client()
    reason = "no attempts made"
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            _sleep(2**attempt)
        try:
            parsed = _attempt(client, model, messages)
        except (openai.AuthenticationError, openai.PermissionDeniedError):
            raise MissingKeyError() from None
        except openai.BadRequestError as error:
            raise LLMError(f"Moonshot refused the request: {error.message}") from None
        except openai.APIError as error:
            reason = f"{type(error).__name__} from Moonshot"
        except LLMError as error:
            reason = error.reason
        else:
            _write_cache(path, parsed)
            return parsed
    raise LLMError(reason)


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Full list price with no cached input. Unknown models give NaN."""
    if model not in PRICES:
        return float("nan")
    input_price, output_price, _ = PRICES[model]
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def usage_totals() -> tuple[int, int]:
    with _usage_lock:
        return _usage[0], _usage[1]
