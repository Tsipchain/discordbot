"""Disabled-by-default storage contract for a future SigBalBot relay.

This module never posts to Discord.  Enabling delivery is intentionally outside
this change; the configured Discord channel will remain the only future target.
"""
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone, timedelta

import database

EVENT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
TIMEFRAME_RE = re.compile(r"^[1-9][0-9]?[mhdw]$")
LINK_OR_MARKUP_RE = re.compile(r"https?://|www\.|<[^>]*>|@(?:everyone|here)|<@", re.I)
SIGNATURE_HEADER = "X-SigBalBot-Signature"
MAX_BODY_BYTES = 4096


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
    if isinstance(data["price"], bool) or not isinstance(data["price"], (int, float)) or data["price"] < 0:
        raise ContractError("INVALID_PRICE")
    if isinstance(data["confidence"], bool) or not isinstance(data["confidence"], (int, float)) or not 0 <= data["confidence"] <= 100:
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
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


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
    return _json_response(web, {"status": "accepted", "duplicate": not created})
