"""Builds the moderation flag embed description, with Discord-safe truncation.

The public flag text is fixed wording. We include the full offending message as a
blockquote when it fits, and only truncate the quote if the whole embed description
would exceed Discord's limit.
"""

# Discord embed description hard limit.
EMBED_DESCRIPTION_LIMIT = 4096

ELLIPSIS = " …"


def _quote_block(text: str) -> str:
    """Render text as a Discord blockquote (each line prefixed with '> ')."""
    if text == "":
        return ">"
    return "\n".join(("> " + line) if line else ">" for line in text.split("\n"))


def flag_line(rules_url: str, pr_url: str) -> str:
    """The fixed public flag text, with 'community rules' and 'PR here' hyperlinked."""
    return (
        f"This message does not align with our [community rules]({rules_url}). "
        f"If you think this was flagged mistakenly, please submit a [PR here]({pr_url})"
    )


def build_flag_description(
    content: str,
    rules_url: str,
    pr_url: str,
    max_len: int = EMBED_DESCRIPTION_LIMIT,
) -> str:
    """Build the embed description: quoted offending message + fixed flag text.

    Includes the whole message when possible; truncates only the quote (with an
    ellipsis) when the full description would exceed ``max_len``.
    """
    content = content or ""
    flag = flag_line(rules_url, pr_url)
    sep = "\n\n"

    full = _quote_block(content) + sep + flag
    if len(full) <= max_len:
        return full

    # Budget left for the quoted block once the flag text and separator are placed.
    budget = max_len - len(flag) - len(sep)

    # Shrink the raw content until the quoted block (plus ellipsis) fits the budget.
    trimmed = content
    while trimmed and len(_quote_block(trimmed + ELLIPSIS)) > budget:
        trimmed = trimmed[:-1]

    quote = _quote_block((trimmed + ELLIPSIS) if trimmed else ELLIPSIS.strip())
    # Final guard: never exceed max_len even in pathological cases (e.g. huge URLs).
    return (quote + sep + flag)[:max_len]
