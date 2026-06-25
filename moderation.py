"""BlueClaw (OpenAI-compatible) moderation decision: prompt + robust JSON parsing.

Structured-output / JSON mode is NOT assumed. We ask the model for strict JSON and
parse defensively (direct parse, fenced block, first object). Any API or parse error
fails open (treated as not out of line) so the bot never spams or blocks on errors.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """/no_think
You are a Discord community moderation classifier.

You are given the community rules and a single user message. Decide whether the
message violates the rules. Do not deliberate or explain your reasoning.

Respond with ONLY a single JSON object and nothing else. No prose, no code fences.
Schema:
{{"out_of_line": <true|false>, "rule": "<short id or phrase of the violated rule, or empty>"}}

Set "out_of_line" to true only if the message clearly violates a rule. When unsure,
set it to false.

Community rules:
---
{rules}
---"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Decision:
    out_of_line: bool
    rule: str = ""
    error: bool = False


def build_messages(rules: str, content: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(rules=rules)},
        {"role": "user", "content": content},
    ]


def _json_candidates(raw: str):
    raw = raw.strip()
    if raw:
        yield raw
    for match in _FENCE_RE.findall(raw):
        yield match.strip()
    obj = _OBJECT_RE.search(raw)
    if obj:
        yield obj.group(0)


def parse_decision(raw: str | None) -> Decision | None:
    """Parse the model output into a Decision, or None if unparseable.

    Returns None (rather than guessing) so the caller can fail open explicitly.
    """
    if not raw:
        return None
    for candidate in _json_candidates(raw):
        try:
            obj = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict) and isinstance(obj.get("out_of_line"), bool):
            rule = obj.get("rule", "")
            return Decision(out_of_line=obj["out_of_line"], rule=str(rule) if rule else "")
    return None


async def evaluate_message(
    content: str,
    rules: str,
    *,
    client: "httpx.AsyncClient",
    base_url: str,
    model: str,
    api_key: str,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> Decision:
    """Ask BlueClaw whether ``content`` is out of line. Fails open on any error.

    ``max_tokens`` must leave room for Qwen3's reasoning tokens; too small a budget
    truncates the response (finish_reason="length", content=null) before any JSON is
    emitted. The prompt also requests ``/no_think`` to keep responses short and cheap.
    """
    payload = {
        "model": model,
        "messages": build_messages(rules, content),
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - fail open, never leak the key
        logger.warning("moderation API call failed (%s); failing open", type(exc).__name__)
        return Decision(out_of_line=False, error=True)

    decision = parse_decision(raw)
    if decision is None:
        logger.warning(
            "could not parse moderation response; failing open. raw=%r",
            (raw or "")[:200],
        )
        return Decision(out_of_line=False, error=True)
    return decision
