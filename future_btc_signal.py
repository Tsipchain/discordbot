"""Authenticated SigBalBot intake and independently enabled Discord publication."""
import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import discord
import database

EVENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
TIMEFRAME_RE = re.compile(r"^[1-9][0-9]?[mhdw]$")
LINK_OR_MARKUP_RE = re.compile(r"https?://|www\.|<[^>]*>|@(?:everyone|here)|<@", re.I)
SIGNATURE_HEADER = "X-SigBalBot-Signature"
MAX_BODY_BYTES = 4096
MAX_PUBLICATION_ATTEMPTS = 6
WEEKLY_WINDOW = timedelta(days=7)
logger = logging.getLogger("thronos_bot.future_btc_signal")
_publisher = None


class ContractError(ValueError):
    pass


def enabled():
    return os.getenv("FREE_BTC_SIGNAL_RELAY_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def verify_signature(body, supplied, secret=None):
    secret = secret if secret is not None else os.getenv("SIGBALBOT_RELAY_SECRET", "")
    if not secret or not supplied:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def _timestamp(value, field):
    if not isinstance(value, str) or len(value) > 35 or not value.endswith("Z"):
        raise ContractError(f"INVALID_{field.upper()}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"INVALID_{field.upper()}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"INVALID_{field.upper()}")
    return parsed.astimezone(timezone.utc)


def validate_payload(data, now=None):
    if not isinstance(data, dict) or set(data) != {
        "contract_version", "event_id", "symbol", "signal", "timeframe",
        "published_at", "valid_until", "price", "confidence", "risk", "summary"
    }:
        raise ContractError("INVALID_FIELDS")
    if data["contract_version"] != "1.0":
        raise ContractError("INVALID_VERSION")
    if not isinstance(data["event_id"], str) or not EVENT_ID_RE.fullmatch(data["event_id"]):
        raise ContractError("INVALID_EVENT_ID")
    if data["symbol"] != "BTC/USDT":
        raise ContractError("INVALID_SYMBOL")
    if data["signal"] not in {"LONG", "SHORT"}:
        raise ContractError("INVALID_SIGNAL")
    if not isinstance(data["timeframe"], str) or not TIMEFRAME_RE.fullmatch(data["timeframe"]):
        raise ContractError("INVALID_TIMEFRAME")
    if data["risk"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise ContractError("INVALID_RISK")
    if (isinstance(data["price"], bool) or not isinstance(data["price"], (int, float))
            or not math.isfinite(data["price"]) or data["price"] < 0):
        raise ContractError("INVALID_PRICE")
    if (isinstance(data["confidence"], bool) or not isinstance(data["confidence"], (int, float))
            or not math.isfinite(data["confidence"]) or not 0 <= data["confidence"] <= 100):
        raise ContractError("INVALID_CONFIDENCE")
    summary = data["summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 280 or LINK_OR_MARKUP_RE.search(summary):
        raise ContractError("INVALID_SUMMARY")
    published = _timestamp(data["published_at"], "published_at")
    valid_until = _timestamp(data["valid_until"], "valid_until")
    now = now or datetime.now(timezone.utc)
    if published > now + timedelta(minutes=5) or published < now - timedelta(hours=24):
        raise ContractError("STALE_EVENT")
    if valid_until <= now or valid_until <= published:
        raise ContractError("STALE_EVENT")
    return data


def store_event(data):
    """Return True for a new event and False for an idempotent duplicate."""
    conn = database.get_connection()
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO future_btc_signal_events "
            "(event_id,published_at,valid_until) VALUES (?,?,?)",
            (data["event_id"], data["published_at"], data["valid_until"]))
        conn.execute(
            "INSERT OR IGNORE INTO future_btc_signal_publications (event_id,state) "
            "VALUES (?, 'received')", (data["event_id"],))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def _env_bool(name):
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _snowflake(name):
    value = os.getenv(name, "").strip()
    return int(value) if value.isdigit() and 17 <= len(value) <= 20 else None


def _public_url():
    for name in ("SIGBALBOT_TELEGRAM_URL", "SIGBALBOT_PUBLIC_URL"):
        value = os.getenv(name, "").strip()
        parsed = urlparse(value)
        if value and parsed.scheme == "https" and parsed.netloc and not parsed.username:
            return value
    return None


@dataclass(frozen=True)
class PublicationConfig:
    enabled: bool
    channel_id: int | None
    test_channel_id: int | None
    community_url: str | None

    @classmethod
    def from_env(cls):
        return cls(
            _env_bool("FREE_BTC_SIGNAL_PUBLICATION_ENABLED"),
            _snowflake("FREE_BTC_SIGNAL_CHANNEL_ID"),
            _snowflake("FREE_BTC_SIGNAL_TEST_CHANNEL_ID"),
            _public_url(),
        )


def _utc_text(value):
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_publication_message(data, community_url):
    summary = discord.utils.escape_markdown(data["summary"])
    return (
        "🟠 **SIGBALBOT FREE BTC SIGNAL**\n\n"
        f"Direction: **{data['signal']}**\n"
        "Instrument: **BTC/USDT**\n"
        f"Timeframe: {data['timeframe']}\n"
        f"Reference price: {data['price']}\n"
        f"Confidence: {data['confidence']}%\n"
        f"Risk: {data['risk']}\n\n"
        f"{summary}\n\n"
        f"Published: {_utc_text(_timestamp(data['published_at'], 'published_at'))}\n"
        f"Valid until: {_utc_text(_timestamp(data['valid_until'], 'valid_until'))}\n\n"
        "Market analysis only — not financial advice.\n"
        f"Join the full SigBalBot community: {community_url}"
    )


class SignalPublisher:
    def __init__(self, bot, config=None, sleep=asyncio.sleep):
        self.bot = bot
        self.config = config or PublicationConfig.from_env()
        self.sleep = sleep

    def _reserve(self, event_id, now):
        """Atomically choose one event for the rolling publication window."""
        conn = database.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM future_btc_signal_publications WHERE event_id=?",
                (event_id,)).fetchone()
            if row["discord_message_id"] or row["state"] in {
                    "published", "permanent_failure", "weekly_limited", "publication_pending"}:
                conn.commit()
                return "suppressed"
            if row["attempt_count"] >= MAX_PUBLICATION_ATTEMPTS:
                conn.execute(
                    "UPDATE future_btc_signal_publications SET state='permanent_failure', "
                    "safe_error_code='ATTEMPTS_EXHAUSTED' WHERE event_id=?", (event_id,))
                conn.commit()
                return "permanent_failure"
            cutoff = _utc_text(now - WEEKLY_WINDOW)
            occupied = conn.execute(
                "SELECT 1 FROM future_btc_signal_publications WHERE event_id<>? AND ("
                "(state='published' AND published_at>?) OR "
                "(state='publication_pending' AND first_publication_attempt>?)) LIMIT 1",
                (event_id, cutoff, cutoff)).fetchone()
            if occupied:
                conn.execute(
                    "UPDATE future_btc_signal_publications SET state='weekly_limited', "
                    "safe_error_code='WEEKLY_PUBLICATION_LIMIT' WHERE event_id=?", (event_id,))
                conn.commit()
                return "weekly_limited"
            stamp = _utc_text(now)
            conn.execute(
                "UPDATE future_btc_signal_publications SET state='publication_pending', "
                "first_publication_attempt=COALESCE(first_publication_attempt,?), "
                "last_publication_attempt=?, safe_error_code=NULL WHERE event_id=?",
                (stamp, stamp, event_id))
            conn.commit()
            return "reserved"
        finally:
            conn.close()

    def _record(self, event_id, state, now, message_id=None, error=None, increment=False):
        conn = database.get_connection()
        try:
            conn.execute(
                "UPDATE future_btc_signal_publications SET state=?, discord_message_id=?, "
                "last_publication_attempt=?, published_at=CASE WHEN ?='published' THEN ? ELSE published_at END, "
                "safe_error_code=?, attempt_count=MIN(6,attempt_count+?) WHERE event_id=?",
                (state, message_id, _utc_text(now), state, _utc_text(now), error,
                 1 if increment else 0, event_id))
            conn.commit()
        finally:
            conn.close()

    async def publish(self, data, now=None):
        if not self.config.enabled:
            return "publication_disabled"
        now = now or datetime.now(timezone.utc)
        reservation = self._reserve(data["event_id"], now)
        if reservation != "reserved":
            return reservation
        if not self.config.channel_id or not self.config.community_url:
            self._record(data["event_id"], "permanent_failure", now,
                         error="INVALID_PUBLICATION_CONFIG", increment=True)
            return "permanent_failure"
        channel = self.bot.get_channel(self.config.channel_id)
        if channel is None:
            self._record(data["event_id"], "permanent_failure", now,
                         error="CHANNEL_NOT_FOUND", increment=True)
            return "permanent_failure"
        conn = database.get_connection()
        used = conn.execute(
            "SELECT attempt_count FROM future_btc_signal_publications WHERE event_id=?",
            (data["event_id"],)).fetchone()["attempt_count"]
        conn.close()
        batch_attempts = min(3, MAX_PUBLICATION_ATTEMPTS - used)
        for attempt in range(batch_attempts):
            attempt_time = datetime.now(timezone.utc)
            try:
                message = await channel.send(
                    build_publication_message(data, self.config.community_url),
                    allowed_mentions=discord.AllowedMentions.none())
                self._record(data["event_id"], "published", attempt_time,
                             message_id=str(message.id), increment=True)
                return "published"
            except (discord.Forbidden, discord.NotFound):
                self._record(data["event_id"], "permanent_failure", attempt_time,
                             error="DISCORD_ACCESS_DENIED", increment=True)
                return "permanent_failure"
            except discord.HTTPException as exc:
                transient = exc.status == 429 or exc.status >= 500
                if not transient:
                    self._record(data["event_id"], "permanent_failure", attempt_time,
                                 error="DISCORD_PERMANENT_FAILURE", increment=True)
                    return "permanent_failure"
                self._record(data["event_id"], "publication_pending", attempt_time, increment=True)
            except OSError:
                self._record(data["event_id"], "publication_pending", attempt_time, increment=True)
            if attempt < batch_attempts - 1:
                await self.sleep(2 ** attempt)
        self._record(data["event_id"], "retryable_failure", datetime.now(timezone.utc),
                     error="DISCORD_TEMPORARY_FAILURE")
        logger.warning("Signal publication failed with safe code DISCORD_TEMPORARY_FAILURE")
        return "retryable_failure"

    async def dry_run(self):
        if not self.config.test_channel_id:
            return "test_channel_missing"
        channel = self.bot.get_channel(self.config.test_channel_id)
        if channel is None:
            return "test_channel_missing"
        try:
            await channel.send(
                "🧪 **SIGBALBOT PUBLICATION TEST — NON-TRADING FIXTURE**\n\n"
                "This is an administrator-requested delivery test. It is not a market signal "
                "and does not affect weekly eligibility.",
                allowed_mentions=discord.AllowedMentions.none())
            return "sent"
        except (discord.Forbidden, discord.NotFound):
            return "test_channel_access_denied"
        except (discord.HTTPException, OSError):
            return "test_delivery_failed"

    def diagnostics(self, now=None):
        now = now or datetime.now(timezone.utc)
        conn = database.get_connection()
        pending = conn.execute(
            "SELECT COUNT(*) AS count FROM future_btc_signal_publications "
            "WHERE state IN ('received','publication_pending','retryable_failure')").fetchone()["count"]
        last = conn.execute(
            "SELECT * FROM future_btc_signal_publications WHERE state='published' "
            "ORDER BY published_at DESC LIMIT 1").fetchone()
        error = conn.execute(
            "SELECT safe_error_code FROM future_btc_signal_publications "
            "WHERE safe_error_code IS NOT NULL ORDER BY last_publication_attempt DESC LIMIT 1").fetchone()
        conn.close()
        channel = str(self.config.channel_id or "")
        last_time = last["published_at"] if last else None
        eligible = (_timestamp(last_time, "published_at") + WEEKLY_WINDOW
                    if last_time else now)
        return {
            "intake_enabled": enabled(),
            "publication_enabled": self.config.enabled,
            "publication_channel_id": "…" + channel[-4:] if channel else None,
            "pending_publication_count": pending,
            "last_published_event_id": last["event_id"] if last else None,
            "last_discord_message_id": last["discord_message_id"] if last else None,
            "last_publication_time": last_time,
            "last_safe_error_code": error["safe_error_code"] if error else None,
            "next_weekly_eligibility_time": _utc_text(max(now, eligible)),
        }


def configure_publisher(bot):
    global _publisher
    _publisher = SignalPublisher(bot)
    return _publisher


def _json_response(web, data, status=200):
    """Produce the byte-stable compact response documented for senders."""
    return web.json_response(
        data, status=status,
        dumps=lambda value: json.dumps(value, separators=(",", ":")),
    )


async def handle_request(request):
    from aiohttp import web
    if not enabled():
        return _json_response(web, {"error": "RELAY_DISABLED"}, status=404)
    # Railway and similar proxies terminate TLS, then provide the original scheme.
    if not request.secure and request.headers.get("X-Forwarded-Proto", "").lower() != "https":
        return _json_response(web, {"error": "HTTPS_REQUIRED"}, status=400)
    body = await request.read()
    if len(body) > MAX_BODY_BYTES:
        return _json_response(web, {"error": "PAYLOAD_TOO_LARGE"}, status=413)
    if not verify_signature(body, request.headers.get(SIGNATURE_HEADER)):
        return _json_response(web, {"error": "INVALID_SIGNATURE"}, status=401)
    try:
        data = validate_payload(json.loads(body))
    except (json.JSONDecodeError, ContractError) as exc:
        code = str(exc) if isinstance(exc, ContractError) else "INVALID_JSON"
        return _json_response(web, {"error": code}, status=400)
    created = store_event(data)
    if _publisher is not None:
        publication = await _publisher.publish(data)
        if publication == "weekly_limited":
            return _json_response(web, {"error": "WEEKLY_PUBLICATION_LIMIT"}, status=429)
        if publication == "retryable_failure":
            return _json_response(
                web, {"error": "DISCORD_TEMPORARY_FAILURE", "stored": True}, status=503)
    return _json_response(web, {"status": "accepted", "duplicate": not created})
