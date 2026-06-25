import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moderation import build_messages, evaluate_message, parse_decision  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """Captures the request payload and returns a canned completion."""

    def __init__(self, content):
        self._content = content
        self.last_payload = None

    async def post(self, url, json=None, headers=None, timeout=None):
        self.last_payload = json
        return _FakeResponse({"choices": [{"message": {"content": self._content}}]})


def test_build_messages_includes_no_think_and_rules():
    msgs = build_messages("RULE-X: no spam", "hi")
    assert msgs[0]["role"] == "system"
    assert "/no_think" in msgs[0]["content"]
    assert "RULE-X: no spam" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert "Conversation context before the message" in msgs[1]["content"]
    assert "(none)" in msgs[1]["content"]
    assert "Current message to judge" in msgs[1]["content"]
    assert "hi" in msgs[1]["content"]


def test_build_messages_includes_prior_context():
    msgs = build_messages("rules", "current", context_messages=["alice: first", "bob: second"])
    user_prompt = msgs[1]["content"]
    assert "alice: first" in user_prompt
    assert "bob: second" in user_prompt
    assert "current" in user_prompt


def test_evaluate_sends_max_tokens_and_context_in_payload():
    client = _FakeClient('{"out_of_line": true, "rule": "spam"}')
    decision = asyncio.run(
        evaluate_message(
            "buy now", "rules", client=client,
            base_url="https://x/v1", model="Qwen3.6-27B", api_key="k", max_tokens=777,
            context_messages=["alice: previous"],
        )
    )
    assert client.last_payload is not None
    assert client.last_payload["max_tokens"] == 777
    assert "alice: previous" in client.last_payload["messages"][1]["content"]
    assert "buy now" in client.last_payload["messages"][1]["content"]
    assert decision.out_of_line is True


def test_evaluate_fails_open_when_content_truncated_to_null():
    # Mirrors Qwen3 finish_reason="length": content is null -> unparseable -> fail open.
    client = _FakeClient(None)
    decision = asyncio.run(
        evaluate_message(
            "anything", "rules", client=client,
            base_url="https://x/v1", model="Qwen3.6-27B", api_key="k",
        )
    )
    assert decision.out_of_line is False and decision.error is True


def test_parses_clean_json_true():
    d = parse_decision('{"out_of_line": true, "rule": "1"}')
    assert d is not None and d.out_of_line is True and d.rule == "1"


def test_parses_clean_json_false():
    d = parse_decision('{"out_of_line": false, "rule": ""}')
    assert d is not None and d.out_of_line is False and d.rule == ""


def test_parses_fenced_json():
    raw = "Sure!\n```json\n{\"out_of_line\": true, \"rule\": \"spam\"}\n```"
    d = parse_decision(raw)
    assert d is not None and d.out_of_line is True and d.rule == "spam"


def test_parses_json_with_surrounding_prose():
    raw = 'Here is the result: {"out_of_line": true, "rule": "harassment"} done.'
    d = parse_decision(raw)
    assert d is not None and d.out_of_line is True and d.rule == "harassment"


def test_missing_rule_defaults_empty():
    d = parse_decision('{"out_of_line": true}')
    assert d is not None and d.out_of_line is True and d.rule == ""


def test_non_bool_out_of_line_rejected():
    # A stray string must not be coerced into a flag.
    assert parse_decision('{"out_of_line": "true"}') is None


def test_garbage_returns_none():
    assert parse_decision("not json at all") is None


def test_empty_and_none_return_none():
    assert parse_decision("") is None
    assert parse_decision(None) is None


def test_rule_coerced_to_string():
    d = parse_decision('{"out_of_line": true, "rule": 3}')
    assert d is not None and d.rule == "3"
