"""Builds the moderation flag embed description, with Discord-safe truncation.

The public flag text is fixed wording. We include the full offending message as a
blockquote when it fits. When the message is too long, we don't blindly keep the
beginning: if the classifier gave us a ``rule`` hint we try to locate the offending
portion inside the message and quote a window around it (with leading/trailing
ellipses), so the part that actually tripped the filter survives truncation. When
there is no usable hint we fall back to keeping the start of the message.
"""

import re

# Discord embed description hard limit.
EMBED_DESCRIPTION_LIMIT = 4096

# Ellipsis markers: trailing (content continues after the window) and leading
# (content precedes the window). Both contain "…" so either signals truncation.
ELLIPSIS = " …"
ELLIPSIS_LEAD = "… "

# Only words at least this long are distinctive enough to anchor the window on; very
# short rule tokens ("a", "the", "is") would match almost anywhere and mislocate it.
_MIN_HINT_WORD = 4


def _quote_block(text: str) -> str:
    """Render text as a Discord blockquote (each line prefixed with '> ')."""
    if text == "":
        return ">"
    return "\n".join(("> " + line) if line else ">" for line in text.split("\n"))


def flag_line(rules_url: str, pr_url: str, mention: str = "") -> str:
    """The fixed public flag text, with 'community rules' and 'PR here' hyperlinked.

    When ``mention`` is given (e.g. a Discord ``<@id>`` mention), it is prepended so
    the warning explicitly tags the original author: ``@X This message does not …``.
    """
    prefix = f"{mention} " if mention else ""
    return (
        f"{prefix}This message does not align with our [community rules]({rules_url}). "
        f"If you think this was flagged mistakenly, please submit a [PR here]({pr_url})"
    )


def _find_offense(content: str, hint: str) -> tuple[int, int] | None:
    """Locate the likely offending span in ``content`` using the ``rule`` hint.

    The hint is the classifier's short id/phrase for the violated rule. We try the
    whole hint as a substring first, then fall back to its most distinctive (longest)
    word. Returns a ``(start, end)`` char span, or ``None`` when nothing matches and
    the caller should keep the beginning instead.
    """
    if not hint or not content:
        return None
    lc = content.lower()

    whole = hint.strip().lower()
    if whole:
        idx = lc.find(whole)
        if idx != -1:
            return (idx, idx + len(whole))

    # Longest words first: they are the most distinctive anchors for the window.
    words = sorted(
        {w for w in re.findall(r"\w+", whole) if len(w) >= _MIN_HINT_WORD},
        key=len,
        reverse=True,
    )
    for word in words:
        idx = lc.find(word)
        if idx != -1:
            return (idx, idx + len(word))
    return None


def _shrink_from_end(content: str, budget: int) -> str:
    """Quote the beginning of ``content`` (with a trailing ellipsis) to fit ``budget``."""
    trimmed = content
    while trimmed and len(_quote_block(trimmed + ELLIPSIS)) > budget:
        trimmed = trimmed[:-1]
    return _quote_block((trimmed + ELLIPSIS) if trimmed else ELLIPSIS.strip())


def _windowed_quote(content: str, span: tuple[int, int], budget: int) -> str:
    """Quote a window of ``content`` around ``span`` that fits ``budget``.

    The window starts at the offending span and is expanded outward (alternating
    sides) to use the remaining budget. Leading/trailing ellipses mark trimmed ends.
    If even the bare span is too large, it is trimmed from its end so the start of the
    offending text is still shown.
    """
    s, e = span
    n = len(content)

    def render(lo: int, hi: int) -> str:
        text = content[lo:hi]
        if lo > 0:
            text = ELLIPSIS_LEAD + text
        if hi < n:
            text = text + ELLIPSIS
        return text

    # If the offending span alone overflows, keep its start and trim the rest.
    if len(_quote_block(render(s, e))) > budget:
        hi = e
        while hi > s and len(_quote_block(render(s, hi))) > budget:
            hi -= 1
        return _quote_block(render(s, hi))

    # Expand outward one char at a time, alternating right then left, until full.
    lo, hi = s, e
    grew = True
    while grew:
        grew = False
        if hi < n and len(_quote_block(render(lo, hi + 1))) <= budget:
            hi += 1
            grew = True
        if lo > 0 and len(_quote_block(render(lo - 1, hi))) <= budget:
            lo -= 1
            grew = True
    return _quote_block(render(lo, hi))


def build_flag_description(
    content: str,
    rules_url: str,
    pr_url: str,
    mention: str = "",
    rule: str = "",
    max_len: int = EMBED_DESCRIPTION_LIMIT,
) -> str:
    """Build the embed description: quoted offending message + fixed flag text.

    Includes the whole message when it fits. When it must be truncated, ``rule`` (the
    classifier's hint about the violated rule) is used to locate the offending portion
    so a window around it is preserved rather than just the start of the message; when
    no hint matches, the beginning is kept. ``mention`` is prepended to the flag text
    so the warning explicitly tags the original author. The fixed flag text and links
    always survive truncation.
    """
    content = content or ""
    flag = flag_line(rules_url, pr_url, mention)
    sep = "\n\n"

    full = _quote_block(content) + sep + flag
    if len(full) <= max_len:
        return full

    # Budget left for the quoted block once the flag text and separator are placed.
    budget = max_len - len(flag) - len(sep)

    span = _find_offense(content, rule)
    if span is None:
        quote = _shrink_from_end(content, budget)
    else:
        quote = _windowed_quote(content, span, budget)

    # Final guard: never exceed max_len even in pathological cases (e.g. huge URLs).
    return (quote + sep + flag)[:max_len]
