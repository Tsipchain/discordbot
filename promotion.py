"""Persistent, locally scheduled community promotion service."""
import asyncio
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import discord

import database

logger = logging.getLogger("thronos_bot.promotion")
CAMPAIGN = "sigbalbot_ecosystem"
MINIMUM_INTERVAL_SECONDS = 3600


def _boolean(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def validate_https_url(value, name, required=False):
    value = (value or "").strip()
    if not value and not required:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{name} must be a public HTTPS URL")
    return value


@dataclass(frozen=True)
class PromotionConfig:
    enabled: bool
    interval_seconds: int
    channel_id: int | None
    telegram_url: str | None
    public_url: str | None
    sentinel_url: str | None
    wallet_url: str | None

    @classmethod
    def from_env(cls):
        enabled = _boolean(os.getenv("COMMUNITY_PROMOTION_ENABLED"), False)
        raw_channel = os.getenv("DISCORD_GENERAL_CHANNEL_ID", "").strip()
        if raw_channel and (not raw_channel.isdigit() or not 17 <= len(raw_channel) <= 20):
            raise ValueError("DISCORD_GENERAL_CHANNEL_ID must be a Discord snowflake")
        interval = max(int(os.getenv("COMMUNITY_PROMOTION_CHECK_INTERVAL_SECONDS", "3600")),
                       MINIMUM_INTERVAL_SECONDS)
        config = cls(
            enabled, interval, int(raw_channel) if raw_channel else None,
            validate_https_url(os.getenv("SIGBALBOT_TELEGRAM_URL"), "SIGBALBOT_TELEGRAM_URL"),
            validate_https_url(os.getenv("SIGBALBOT_PUBLIC_URL"), "SIGBALBOT_PUBLIC_URL"),
            validate_https_url(os.getenv("SENTINEL_DOWNLOAD_URL", "https://api.thronoschain.org/downloads"), "SENTINEL_DOWNLOAD_URL"),
            validate_https_url(os.getenv("THRONOS_WALLET_URL", "https://api.thronoschain.org/wallet-pwa"), "THRONOS_WALLET_URL"),
        )
        if enabled and (not config.channel_id or not config.telegram_url):
            raise ValueError("enabled promotion requires channel ID and Telegram URL")
        return config


def build_message(config):
    lines = ["🌐 **Explore the SigBalBot trading community**", "",
             "🤖 Receive verified crypto market signals and ecosystem updates on Telegram:",
             config.telegram_url]
    if config.public_url:
        lines += ["", "📊 Learn more or subscribe:", config.public_url]
    if config.sentinel_url:
        lines += ["", "🛡️ Trader Sentinel:", config.sentinel_url]
    if config.wallet_url:
        lines += ["", "👛 Thronos Wallet:", config.wallet_url]
    lines += ["", "Market analysis only — always verify risk before acting."]
    return "\n".join(lines)


class PromotionService:
    def __init__(self, bot, config, sleep=asyncio.sleep):
        self.bot, self.config, self.sleep = bot, config, sleep

    def reserve(self, today):
        conn = database.get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO community_promotions "
                "(campaign,destination,promotion_date,status,attempt_count) VALUES (?,?,?,?,1) "
                "ON CONFLICT(campaign,destination,promotion_date) DO UPDATE SET "
                "status='reserved', attempt_count=attempt_count+1, updated_at=CURRENT_TIMESTAMP "
                "WHERE status='retryable'",
                (CAMPAIGN, str(self.config.channel_id), today.isoformat(), "reserved"))
            conn.commit()
            return cur.rowcount == 1
        finally:
            conn.close()

    def _update(self, today, status, message_id=None, error=None):
        conn = database.get_connection()
        try:
            conn.execute(
                "UPDATE community_promotions SET status=?, discord_message_id=?, "
                "delivered_at=CASE WHEN ?='delivered' THEN CURRENT_TIMESTAMP ELSE delivered_at END, "
                "safe_error_code=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE campaign=? AND destination=? AND promotion_date=?",
                (status, message_id, status, error, CAMPAIGN,
                 str(self.config.channel_id), today.isoformat()))
            conn.commit()
        finally:
            conn.close()

    async def run_once(self, now=None):
        if not self.config.enabled:
            return "disabled"
        today = (now or datetime.now(timezone.utc)).date()
        if not self.reserve(today):
            return "suppressed"
        channel = self.bot.get_channel(self.config.channel_id)
        if channel is None:
            self._update(today, "permanent_failure", error="CHANNEL_NOT_FOUND")
            return "permanent_failure"
        for attempt in range(3):
            try:
                message = await channel.send(
                    build_message(self.config),
                    allowed_mentions=discord.AllowedMentions.none())
                self._update(today, "delivered", str(message.id))
                return "delivered"
            except (discord.Forbidden, discord.NotFound):
                self._update(today, "permanent_failure", error="DISCORD_ACCESS_DENIED")
                return "permanent_failure"
            except (discord.HTTPException, OSError):
                if attempt < 2:
                    await self.sleep(2 ** attempt)
        self._update(today, "retryable", error="DISCORD_TRANSIENT")
        logger.warning("Community promotion failed with safe code DISCORD_TRANSIENT")
        return "retryable"

    def diagnostics(self, now=None):
        today = (now or datetime.now(timezone.utc)).date()
        conn = database.get_connection()
        row = conn.execute(
            "SELECT * FROM community_promotions WHERE campaign=? AND destination=? "
            "ORDER BY promotion_date DESC LIMIT 1", (CAMPAIGN, str(self.config.channel_id))).fetchone()
        success = conn.execute(
            "SELECT promotion_date FROM community_promotions WHERE campaign=? AND destination=? "
            "AND status='delivered' ORDER BY promotion_date DESC LIMIT 1",
            (CAMPAIGN, str(self.config.channel_id))).fetchone()
        conn.close()
        cid = str(self.config.channel_id or "")
        return {
            "enabled": self.config.enabled,
            "last_successful_promotion_date": success["promotion_date"] if success else None,
            "destination_channel_id": ("…" + cid[-4:]) if cid else None,
            "last_discord_message_id": row["discord_message_id"] if row else None,
            "last_safe_error_code": row["safe_error_code"] if row else None,
            "next_eligibility_date": (today + timedelta(days=1)).isoformat() if row and row["promotion_date"] == today.isoformat() else today.isoformat(),
        }


async def health_handler(request):
    """Safe HTTP diagnostics; credentials and full Discord errors are never read."""
    from aiohttp import web
    try:
        config = PromotionConfig.from_env()
        data = PromotionService(bot=None, config=config).diagnostics()
    except (ValueError, TypeError):
        data = {"enabled": False, "last_safe_error_code": "INVALID_CONFIG"}
    return web.json_response(data)
