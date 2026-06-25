import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from formatting import (  # noqa: E402
    EMBED_DESCRIPTION_LIMIT,
    build_flag_description,
    flag_line,
)

RULES_URL = "https://example.com/rules"
PR_URL = "https://example.com/pr"


def test_flag_line_has_exact_wording_and_links():
    line = flag_line(RULES_URL, PR_URL)
    assert line == (
        f"This message does not align with our [community rules]({RULES_URL}). "
        f"If you think this was flagged mistakenly, please submit a [PR here]({PR_URL})"
    )


def test_short_message_quoted_in_full():
    desc = build_flag_description("hello world", RULES_URL, PR_URL)
    assert "> hello world" in desc
    assert f"[community rules]({RULES_URL})" in desc
    assert f"[PR here]({PR_URL})" in desc
    assert "…" not in desc


def test_multiline_message_each_line_quoted():
    desc = build_flag_description("line one\nline two", RULES_URL, PR_URL)
    assert "> line one" in desc
    assert "> line two" in desc


def test_empty_message_does_not_crash():
    desc = build_flag_description("", RULES_URL, PR_URL)
    assert flag_line(RULES_URL, PR_URL) in desc


def test_long_message_truncated_within_limit():
    content = "x" * 10000
    desc = build_flag_description(content, RULES_URL, PR_URL)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "…" in desc
    # The fixed flag text must always survive truncation.
    assert f"[PR here]({PR_URL})" in desc


def test_message_exactly_at_boundary_not_truncated():
    # Build content whose full description is exactly the limit.
    probe = build_flag_description("", RULES_URL, PR_URL)
    overhead = len(probe)  # ">" + "\n\n" + flag, for empty content
    # quote of N 'a' chars (single line) adds "> " + N to replace the lone ">".
    fill = EMBED_DESCRIPTION_LIMIT - overhead - len("> ") + len(">")
    content = "a" * fill
    desc = build_flag_description(content, RULES_URL, PR_URL)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "…" not in desc
