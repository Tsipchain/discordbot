import discord
from discord.ext import commands
import logging
from aiohttp import web
import asyncio
import hashlib
import hmac
import html
import os
import re
import time

logger = logging.getLogger('thronos_bot.pytheia')

# Allowed values for input validation
VALID_SIGNAL_TYPES = {"trade", "alert", "rebalance", "liquidation"}
VALID_ACTIONS = {"buy", "sell", "swap", "stake", "unstake"}

# Rate limiting: max requests per window
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60  # seconds


def sanitize_field(value, max_length=200):
    """Sanitize a string value for safe embedding in Discord messages."""
    if not isinstance(value, str):
        value = str(value)
    # Strip HTML tags and escape remaining HTML entities
    value = re.sub(r'<[^>]+>', '', value)
    value = html.escape(value)
    # Remove Discord markdown injection patterns (e.g. @everyone, @here)
    value = value.replace('@everyone', '@\u200beveryone')
    value = value.replace('@here', '@\u200bhere')
    # Truncate to max length
    return value[:max_length]


def is_valid_tx_hash(tx_hash):
    """Validate that a tx_hash looks like a valid hex transaction hash."""
    return bool(re.match(r'^0x[0-9a-fA-F]{64}$', tx_hash))


class PytheiaWebhook(commands.Cog):
    """Listens for Pytheia Autonomous Agent trades and alerts Discord."""

    def __init__(self, bot):
        self.bot = bot
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")
        if not self.webhook_secret:
            logger.warning("WEBHOOK_SECRET not set - webhook endpoint will reject all requests")

        self.app = web.Application()
        self.app.router.add_post('/pytheia/alert', self.handle_alert)
        self.runner = None
        self.site = None

        # Rate limiting state: list of timestamps
        self._request_timestamps = []

        # Start the webhook server when cog loads
        self.bot.loop.create_task(self.start_server())

    async def start_server(self):
        await self.bot.wait_until_ready()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        # Bind to PORT from environment (fallback to 5005) for external Vercel/Railway hosting
        port = int(os.getenv("PORT", 5005))
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        logger.info(f"Pytheia Webhook listening on 0.0.0.0:{port}/pytheia/alert")

    def cog_unload(self):
        if self.runner:
            asyncio.create_task(self.runner.cleanup())

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature of the request body."""
        if not self.webhook_secret:
            return False
        expected = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    def _check_rate_limit(self) -> bool:
        """Return True if the request is within rate limits."""
        now = time.monotonic()
        # Prune old timestamps outside the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if now - ts < RATE_LIMIT_WINDOW
        ]
        if len(self._request_timestamps) >= RATE_LIMIT_MAX:
            return False
        self._request_timestamps.append(now)
        return True

    async def handle_alert(self, request):
        try:
            # --- HMAC signature verification ---
            signature = request.headers.get("X-Signature")
            if not signature:
                logger.warning("Webhook request missing X-Signature header")
                return web.json_response({"error": "Missing signature"}, status=401)

            body = await request.read()
            if not self._verify_signature(body, signature):
                logger.warning("Webhook request with invalid signature")
                return web.json_response({"error": "Invalid signature"}, status=403)

            # --- Rate limiting ---
            if not self._check_rate_limit():
                logger.warning("Webhook rate limit exceeded")
                return web.json_response({"error": "Rate limit exceeded"}, status=429)

            # --- Parse and validate payload ---
            import json
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return web.json_response({"error": "Invalid JSON"}, status=400)

            # Validate required fields
            required_fields = ["signal_type", "symbol", "action", "tx_hash"]
            missing = [f for f in required_fields if f not in data or not data[f]]
            if missing:
                return web.json_response(
                    {"error": f"Missing required fields: {', '.join(missing)}"},
                    status=400
                )

            # Validate field values
            if data["signal_type"] not in VALID_SIGNAL_TYPES:
                return web.json_response(
                    {"error": f"Invalid signal_type. Must be one of: {', '.join(sorted(VALID_SIGNAL_TYPES))}"},
                    status=400
                )

            if data["action"] not in VALID_ACTIONS:
                return web.json_response(
                    {"error": f"Invalid action. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"},
                    status=400
                )

            if not is_valid_tx_hash(data["tx_hash"]):
                return web.json_response(
                    {"error": "Invalid tx_hash format. Expected 0x-prefixed 64 hex characters."},
                    status=400
                )

            # --- Sanitize data before embedding ---
            safe_signal_type = sanitize_field(data["signal_type"], 50)
            safe_symbol = sanitize_field(data["symbol"], 20)
            safe_action = sanitize_field(data["action"], 20)
            safe_tx_hash = data["tx_hash"]  # Already validated as hex

            # Route to all guilds #autonomous-trading channel
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="autonomous-trading")
                if not channel:
                    category = discord.utils.get(guild.categories, name="\U0001f6e0\ufe0f Ecosystem")
                    if category:
                        try:
                            channel = await guild.create_text_channel("autonomous-trading", category=category)
                        except discord.Forbidden:
                            logger.warning(f"Missing permissions to create channel in guild {guild.id}")
                            continue

                if channel:
                    embed = discord.Embed(
                        title="\U0001f916 Pytheia Autonomous Trade executed",
                        color=0xf1c40f
                    )

                    embed.add_field(name="Signal", value=safe_signal_type, inline=True)
                    embed.add_field(name="Symbol", value=safe_symbol, inline=True)
                    embed.add_field(name="Action", value=safe_action, inline=True)

                    if "amount" in data and "token" in data:
                        safe_amount = sanitize_field(str(data["amount"]), 30)
                        safe_token = sanitize_field(data["token"], 20)
                        embed.add_field(name="Amount", value=f"{safe_amount} {safe_token}", inline=True)
                    if "profit_estimate" in data:
                        safe_profit = sanitize_field(str(data["profit_estimate"]), 30)
                        embed.add_field(name="Expected Profit", value=safe_profit, inline=True)

                    embed.description = f"[View on Explorer](https://explorer.thronoschain.org/tx/{safe_tx_hash})"

                    embed.set_footer(text="Pytheia AI Network Layer")
                    await channel.send(embed=embed)

            return web.json_response({"status": "delivered"})
        except Exception as e:
            logger.error(f"Error handling pytheia webhook: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

async def setup(bot):
    await bot.add_cog(PytheiaWebhook(bot))
