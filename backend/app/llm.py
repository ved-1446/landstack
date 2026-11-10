"""The one place that talks to the LLM (OpenRouter's OpenAI-style chat API).

Everything else calls `complete(messages)`, so tests replace that one function and never touch the network.

- OPENROUTER_API_KEY and OPENROUTER_MODEL come from the environment or .env. The server starts fine without them;
  `complete` then raises LLMOff and the callers show a friendly "AI is off" message or a code-written fallback.
- Free models often answer 429 (busy) or time out. That is a NORMAL case: one retry after a short wait, then LLMBusy
  (the UI says "AI is busy, try again"). Nothing here ever crashes a request.
- The key is sent only in the Authorization header. It is never logged and never put in an error message.
- Whatever is sent here leaves this machine for a third-party service, so callers send as little as they can:
  the explainer sends finding types, numbers and the band; the guide sends the question and public source text.
"""
import logging
import time

import httpx

from . import config
from .db import read_env

log = logging.getLogger("landstack.llm")


class LLMProblem(Exception):
    """Base class. `status` is what the API and the UI show: off, busy or failed."""
    status = "failed"


class LLMOff(LLMProblem):
    status = "off"          # no key or no model in .env


class LLMBusy(LLMProblem):
    status = "busy"         # 429, a server error or a timeout, even after one retry


class LLMFailed(LLMProblem):
    status = "failed"       # a bad key, a bad answer or any other problem


def settings():
    """(api_key, model, base_url); an empty key or model means the AI is off."""
    env = read_env()
    return (env.get("OPENROUTER_API_KEY", "").strip(), env.get("OPENROUTER_MODEL", "").strip(),
            (env.get("OPENROUTER_BASE_URL", "") or config.OPENROUTER_BASE_URL).strip().rstrip("/"))


def is_on():
    key, model, _ = settings()
    return bool(key and model)


def _post(url, headers, payload, timeout):
    """The ONLY network call in the whole AI feature. Tests replace this (or `complete`)."""
    return httpx.post(url, headers=headers, json=payload, timeout=timeout)


def complete(messages, *, max_tokens=500, temperature=0.2):
    """Send chat messages [{"role", "content"}] and return the model's text. Raises LLMOff, LLMBusy or LLMFailed."""
    key, model, base_url = settings()
    if not key or not model:
        raise LLMOff("OPENROUTER_API_KEY or OPENROUTER_MODEL is not set")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "LandStack"}
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}

    last = "no answer"
    for attempt in range(2):                      # the first try, plus ONE retry
        if attempt:
            time.sleep(config.LLM_RETRY_WAIT_S)
        try:
            response = _post(f"{base_url}/chat/completions", headers, payload, config.LLM_TIMEOUT_S)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last = f"network problem ({type(exc).__name__})"
            log.warning("LLM call failed: %s", last)
            continue
        status = response.status_code
        if status == 429 or status >= 500:
            last = f"HTTP {status}"
            log.warning("LLM busy: %s", last)
            continue
        if status in (401, 403):
            raise LLMFailed("the AI service refused the key")            # no retry: it will not get better
        if status >= 400:
            raise LLMFailed(f"HTTP {status}")
        try:
            text = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMFailed("the AI service sent an answer this server could not read") from None
        if not isinstance(text, str) or not text.strip():
            raise LLMFailed("the AI service sent an empty answer")
        return text.strip()
    raise LLMBusy(f"the AI service is busy ({last})")
