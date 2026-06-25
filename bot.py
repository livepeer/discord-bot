"""Lean Discord community moderation bot.

Listens to messages in accessible channels, classifies each with BlueClaw, and on a
violation replies with an embed quoting the message and the fixed flag text.
"""

from __future__ import annotations

import logging
import os
import sys

import discord
import httpx
from dotenv import load_dotenv

from formatting import build_flag_description
from moderation import evaluate_message

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("modbot")


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _load_rules(path: str = "rules.md") -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        logger.warning("rules file %s not found; using empty ruleset", path)
        return ""


# --- Config (read once at startup) ---------------------------------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BLUECLAW_BASE_URL = os.getenv("BLUECLAW_BASE_URL", "https://openai.blueclaw.network/v1")
BLUECLAW_MODEL = os.getenv("BLUECLAW_MODEL", "Qwen3.6-27B")
BLUECLAW_API_KEY = os.getenv("BLUECLAW_API_KEY", "")
BLUECLAW_MAX_TOKENS = int(os.getenv("BLUECLAW_MAX_TOKENS", "4096"))
RULES_URL = os.getenv(
    "RULES_URL", "https://github.com/livepeer/discord-bot/blob/main/rules.md"
)
PR_URL = os.getenv("PR_URL", "https://github.com/livepeer/discord-bot")
DRY_RUN = _bool_env("DRY_RUN", True)
MIN_MESSAGE_CHARS = int(os.getenv("MIN_MESSAGE_CHARS", "1"))
CHANNEL_IDS = {
    int(c) for c in os.getenv("CHANNEL_IDS", "").replace(" ", "").split(",") if c
}
RULES = _load_rules()


intents = discord.Intents.default()
intents.message_content = True  # privileged intent — enable it in the Developer Portal


class ModeratorClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.http_client: httpx.AsyncClient | None = None

    async def setup_hook(self) -> None:
        self.http_client = httpx.AsyncClient()

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()
        await super().close()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (dry_run=%s)", self.user, DRY_RUN)

    async def on_message(self, message: discord.Message) -> None:
        # Skip self, other bots, DMs, and empty/too-short messages.
        if message.author == self.user or message.author.bot:
            return
        if message.guild is None:  # DM
            return
        content = (message.content or "").strip()
        if len(content) < MIN_MESSAGE_CHARS:
            return
        if CHANNEL_IDS and message.channel.id not in CHANNEL_IDS:
            return

        decision = await evaluate_message(
            content,
            RULES,
            client=self.http_client,
            base_url=BLUECLAW_BASE_URL,
            model=BLUECLAW_MODEL,
            api_key=BLUECLAW_API_KEY,
            max_tokens=BLUECLAW_MAX_TOKENS,
        )
        if not decision.out_of_line:
            return

        description = build_flag_description(
            content,
            RULES_URL,
            PR_URL,
            mention=message.author.mention,
            rule=decision.rule,
        )
        embed = discord.Embed(description=description)

        if DRY_RUN:
            logger.info(
                "[DRY_RUN] would flag message %s in #%s (rule=%r)",
                message.id, getattr(message.channel, "name", message.channel.id), decision.rule,
            )
            return
        try:
            await message.reply(embed=embed, mention_author=True)
        except discord.DiscordException as exc:
            logger.warning("failed to post flag: %s", type(exc).__name__)


def main() -> int:
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN is not set; cannot start. Fill it in .env.")
        return 1
    if not BLUECLAW_API_KEY:
        logger.warning("BLUECLAW_API_KEY is empty; moderation calls will fail open (no flags).")
    client = ModeratorClient(intents=intents)
    client.run(DISCORD_BOT_TOKEN, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
