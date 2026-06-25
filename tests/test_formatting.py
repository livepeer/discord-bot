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


def test_flag_line_with_mention_tags_author_first():
    mention = "<@123456789>"
    line = flag_line(RULES_URL, PR_URL, mention)
    # The mention leads the warning: "@X This message does not align …".
    assert line.startswith(f"{mention} This message does not align")
    assert f"[community rules]({RULES_URL})" in line
    assert f"[PR here]({PR_URL})" in line


def test_flag_line_without_mention_unchanged():
    # Omitting the mention must preserve the original fixed wording exactly.
    assert flag_line(RULES_URL, PR_URL) == flag_line(RULES_URL, PR_URL, "")


def test_build_flag_description_includes_mention():
    mention = "<@987654321>"
    desc = build_flag_description("hello world", RULES_URL, PR_URL, mention=mention)
    assert mention in desc
    assert "> hello world" in desc
    # The mention introduces the flag text, not the quoted message.
    assert f"{mention} This message does not align" in desc


def test_long_message_with_mention_truncated_within_limit():
    mention = "<@111222333>"
    desc = build_flag_description("x" * 10000, RULES_URL, PR_URL, mention=mention)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "…" in desc
    # Both the mention and the fixed flag text survive truncation.
    assert mention in desc
    assert f"[PR here]({PR_URL})" in desc


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


def test_truncation_keeps_offending_text_not_at_beginning():
    # The violation sits in the middle of a very long message; the rule hint names it.
    offense = "BUYNOWSPAMLINK"
    content = "a" * 6000 + offense + "b" * 6000
    desc = build_flag_description(content, RULES_URL, PR_URL, rule=offense)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    # The offending text survives even though it is not at the start.
    assert offense in desc
    # A leading ellipsis shows content was dropped *before* the offending part.
    assert desc.index("…") < desc.index(offense)
    # The fixed flag text and links must always survive truncation.
    assert f"[PR here]({PR_URL})" in desc
    assert f"[community rules]({RULES_URL})" in desc


def test_truncation_uses_distinctive_word_from_rule_phrase():
    # The rule hint is a phrase that does not appear verbatim, but one of its
    # distinctive words ("advertising") does appear in the offending message.
    content = "x" * 6000 + " check my advertising channel " + "y" * 6000
    desc = build_flag_description(
        content, RULES_URL, PR_URL, rule="No self-promotion or advertising allowed"
    )
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "advertising" in desc
    assert desc.index("…") < desc.index("advertising")


def test_truncation_without_rule_falls_back_to_beginning():
    # With no usable hint we keep the start of the message (legacy behaviour).
    content = "START" + "z" * 10000
    desc = build_flag_description(content, RULES_URL, PR_URL)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "> START" in desc
    assert "…" in desc
    assert f"[PR here]({PR_URL})" in desc


def test_truncation_with_unmatched_rule_falls_back_to_beginning():
    # A rule hint that matches nothing in the content must not break truncation.
    content = "HEAD" + "q" * 10000
    desc = build_flag_description(
        content, RULES_URL, PR_URL, rule="rule-id-that-is-absent"
    )
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert "> HEAD" in desc
    assert f"[PR here]({PR_URL})" in desc


def test_offending_window_preserved_with_mention():
    mention = "<@555666777>"
    offense = "FORBIDDENPHRASE"
    content = "m" * 6000 + offense + "n" * 6000
    desc = build_flag_description(
        content, RULES_URL, PR_URL, mention=mention, rule=offense
    )
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert offense in desc
    # Both the mention and the fixed flag text survive alongside the offending text.
    assert mention in desc
    assert f"[PR here]({PR_URL})" in desc


def test_offense_at_start_has_no_leading_ellipsis():
    # When the offending text is already at the very start, keep the beginning and
    # only a trailing ellipsis is needed.
    offense = "BADSTART"
    content = offense + "c" * 10000
    desc = build_flag_description(content, RULES_URL, PR_URL, rule=offense)
    assert len(desc) <= EMBED_DESCRIPTION_LIMIT
    assert f"> {offense}" in desc
    # No leading ellipsis before the offending text at the start.
    assert not desc.lstrip().startswith("> …")


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
