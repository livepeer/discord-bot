# Discord Community Moderation Bot

A lean, experimental Discord bot that reads messages in channels it can access,
classifies each one against your community rules using the
[BlueClaw](https://blueclaw.network) (OpenAI-compatible) API, and replies to
violations with an embed quoting the message and a fixed flag notice.

When flagged, the bot replies with an embed:

> _\<the offending message, quoted in full; truncated only if the embed would exceed Discord's limit\>_
>
> This message does not align with our [community rules](RULES_URL). If you think this was flagged mistakenly, please submit a [PR here](PR_URL)

(`community rules` → `RULES_URL`, `PR here` → `PR_URL`. Masked links are used because
they render reliably inside embeds, unlike plain message content.)

## Stack
- Python 3.11+
- [`discord.py`](https://discordpy.readthedocs.io/) — gateway + message events
- [`httpx`](https://www.python-httpx.org/) — BlueClaw API calls
- [`python-dotenv`](https://github.com/theskumar/python-dotenv) — `.env` loading

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
```

In the Discord Developer Portal, enable the **Message Content Intent** (privileged)
and invite the bot with Read Messages + Send Messages permissions.

### BlueClaw API key
The classifier runs on [BlueClaw](https://blueclaw.network), which exposes an
OpenAI-compatible endpoint. To try the bot, sign up at
[blueclaw.network](https://blueclaw.network), create an API key from your account
dashboard, and put it in `.env` as `BLUECLAW_API_KEY` (with `BLUECLAW_BASE_URL`
pointing at the endpoint shown there). The key is kept out of git and never logged.

## Configuration (`.env`)
| Var | Purpose |
|-----|---------|
| `DISCORD_BOT_TOKEN` | Bot token. Required to run live. |
| `BLUECLAW_BASE_URL` | `https://openai.blueclaw.network/v1` |
| `BLUECLAW_MODEL` | `Qwen/Qwen3.6-35B-A3B-FP8` |
| `BLUECLAW_API_KEY` | BlueClaw key. Kept out of git; never logged. |
| `BLUECLAW_MAX_TOKENS` | Completion budget (default `4096`). Qwen3 spends tokens reasoning — too low truncates the reply to `null` before any JSON, especially with long rule sets. |
| `RULES_URL` | Link target for "community rules". Defaults to `rules.md` on GitHub. |
| `PR_URL` | Link target for "PR here". Defaults to the GitHub repo. |
| `DRY_RUN` | `true` logs the would-be flag instead of posting. |
| `CHANNEL_IDS` | Comma-separated allowlist. Empty = all visible channels. |
| `MIN_MESSAGE_CHARS` | Skip messages shorter than this. |
| `CONTEXT_MESSAGE_COUNT` | Previous human channel messages to include as context for each moderation check (default `4`). |
| `LOG_LEVEL` | `INFO` / `DEBUG` / ... |

Edit `rules.md` to change moderation behavior — its full text is injected into the
classifier prompt at startup.

## Run
```bash
python bot.py
```
Start with `DRY_RUN=true` to watch decisions in the logs before posting anything.

## Behavior notes
- **Fail-open:** any API or JSON-parse error is treated as "not out of line", so the
  bot never blocks or spams on errors.
- **Skips:** its own messages, other bots, DMs, and empty/too-short messages.
- **Conversation context:** each moderation call includes up to `CONTEXT_MESSAGE_COUNT`
  previous human messages from the same channel, oldest-to-newest, plus the current
  message being judged.
- **No structured-output dependency:** the classifier is prompted for strict JSON and
  parsed defensively (direct / fenced / first-object); non-boolean verdicts are rejected.
- **Qwen3 reasoning:** the prompt prepends `/no_think` to suppress chain-of-thought and
  `BLUECLAW_MAX_TOKENS` (default 4096) leaves headroom so the JSON is never truncated.
- **No secret logging:** the API key is never written to logs.

## Contributing moderation feedback

If the bot flags a message incorrectly, or misses a message that should have been
flagged, please open a moderation rule feedback issue with:

- the message example
- the prior conversation context, if relevant
- what happened vs. what you expected
- evidence and reasoning tied to `rules.md`
- a proposed rule fix, ideally followed by a PR updating `rules.md`

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Tests
```bash
pip install pytest
python -m pytest -q
```
Covers embed formatting/truncation and JSON decision parsing — both pure, no network.
