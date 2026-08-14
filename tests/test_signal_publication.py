import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import discord
import pytest

import database
import future_btc_signal as relay
from future_btc_signal import PublicationConfig, SignalPublisher, store_event


class Message:
    def __init__(self, message_id=444444444444444444):
        self.id = message_id


class Response:
    def __init__(self, status):
        self.status = status
        self.reason = "safe test reason"
        self.headers = {}


class Channel:
    def __init__(self, errors=None):
        self.errors = list(errors or [])
        self.calls = []

    async def send(self, content, **kwargs):
        self.calls.append((content, kwargs))
        if self.errors:
            raise self.errors.pop(0)
        return Message()


class Bot:
    def __init__(self, channel):
        self.channel = channel

    def get_channel(self, channel_id):
        return self.channel


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()


def signal(event_id, now):
    return {
        "contract_version": "1.0", "event_id": event_id, "symbol": "BTC/USDT",
        "signal": "LONG", "timeframe": "4h",
        "published_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valid_until": (now + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price": 65000, "confidence": 95, "risk": "MEDIUM",
        "summary": "Bounded public thesis with *untrusted* markdown.",
    }


def config(enabled=True):
    return PublicationConfig(enabled, 123456789012345678, 987654321098765432,
                             "https://t.me/SigBalBot")


def row(event_id):
    conn = database.get_connection()
    result = conn.execute(
        "SELECT * FROM future_btc_signal_publications WHERE event_id=?", (event_id,)
    ).fetchone()
    conn.close()
    return dict(result)


def test_publication_disabled_stores_without_posting():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    data, channel = signal("disabled-1", now), Channel()
    store_event(data)
    result = asyncio.run(SignalPublisher(Bot(channel), config(False)).publish(data, now))
    assert result == "publication_disabled"
    assert channel.calls == []
    assert row(data["event_id"])["state"] == "received"


def test_enabled_duplicate_restart_and_message_id():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    data, channel = signal("once-1", now), Channel()
    store_event(data)
    assert asyncio.run(SignalPublisher(Bot(channel), config()).publish(data, now)) == "published"
    assert asyncio.run(SignalPublisher(Bot(channel), config()).publish(data, now)) == "suppressed"
    assert len(channel.calls) == 1
    stored = row(data["event_id"])
    assert stored["state"] == "published"
    assert stored["discord_message_id"] == "444444444444444444"
    assert stored["published_at"] is not None
    mentions = channel.calls[0][1]["allowed_mentions"]
    assert mentions.everyone is False and mentions.users is False
    assert mentions.roles is False and mentions.replied_user is False
    assert "\\*untrusted\\*" in channel.calls[0][0]


def test_duplicate_posts_do_not_republish(monkeypatch):
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    data, channel = signal("post-once-1", now), Channel()
    body = json.dumps(data, separators=(",", ":")).encode()
    secret = "endpoint-test-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    class Request:
        secure = True
        headers = {relay.SIGNATURE_HEADER: signature}

        async def read(self):
            return body

    real_validate = relay.validate_payload
    monkeypatch.setenv("FREE_BTC_SIGNAL_RELAY_ENABLED", "true")
    monkeypatch.setenv("SIGBALBOT_RELAY_SECRET", secret)
    monkeypatch.setattr(relay, "_publisher", SignalPublisher(Bot(channel), config()))
    monkeypatch.setattr(relay, "validate_payload", lambda value: real_validate(value, now))
    first = asyncio.run(relay.handle_request(Request()))
    second = asyncio.run(relay.handle_request(Request()))
    assert json.loads(first.body) == {"status": "accepted", "duplicate": False}
    assert json.loads(second.body) == {"status": "accepted", "duplicate": True}
    assert len(channel.calls) == 1


def test_concurrent_reservation_posts_once():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    data, channel = signal("concurrent-1", now), Channel()
    store_event(data)

    async def scenario():
        publisher = SignalPublisher(Bot(channel), config())
        return await asyncio.gather(*[publisher.publish(data, now) for _ in range(8)])

    results = asyncio.run(scenario())
    assert results.count("published") == 1
    assert len(channel.calls) == 1


def test_rate_limit_retries_with_backoff():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    errors = [discord.HTTPException(Response(429), "rate limited")]
    data, channel, sleeps = signal("rate-1", now), Channel(errors), []
    store_event(data)

    async def sleep(delay):
        sleeps.append(delay)

    result = asyncio.run(SignalPublisher(Bot(channel), config(), sleep).publish(data, now))
    assert result == "published"
    assert sleeps == [1]
    assert len(channel.calls) == 2


def test_permission_failure_and_missing_channel_are_permanent():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    denied = signal("denied-1", now)
    store_event(denied)
    channel = Channel([discord.Forbidden(Response(403), "do not log secret-body")])
    assert asyncio.run(SignalPublisher(Bot(channel), config()).publish(denied, now)) == "permanent_failure"
    assert len(channel.calls) == 1
    assert row("denied-1")["safe_error_code"] == "DISCORD_ACCESS_DENIED"

    missing = signal("missing-1", now)
    store_event(missing)
    # The pending first event occupies the window only until its permanent result is saved.
    assert asyncio.run(SignalPublisher(Bot(None), config()).publish(missing, now)) == "permanent_failure"
    assert row("missing-1")["safe_error_code"] == "CHANNEL_NOT_FOUND"


def test_weekly_limit_and_next_event_after_seven_days():
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    channel = Channel()
    publisher = SignalPublisher(Bot(channel), config())
    first = signal("week-1", now)
    second = signal("week-2", now + timedelta(hours=1))
    store_event(first)
    store_event(second)
    assert asyncio.run(publisher.publish(first, now)) == "published"
    assert asyncio.run(publisher.publish(second, now + timedelta(hours=1))) == "weekly_limited"
    assert row("week-2")["state"] == "weekly_limited"

    published_time = datetime.fromisoformat(
        row("week-1")["published_at"].replace("Z", "+00:00")
    )
    later_time = published_time + timedelta(days=7, seconds=1)
    later = signal("week-3", later_time)
    store_event(later)
    assert asyncio.run(publisher.publish(later, later_time)) == "published"
    assert len(channel.calls) == 2


def test_diagnostics_and_logs_never_contain_secrets(caplog):
    caplog.set_level(logging.WARNING)
    now = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)
    data = signal("safe-1", now)
    store_event(data)
    channel = Channel([OSError("SIGBALBOT_RELAY_SECRET=real-secret") for _ in range(3)])
    publisher = SignalPublisher(Bot(channel), config(), sleep=lambda _: asyncio.sleep(0))
    assert asyncio.run(publisher.publish(data, now)) == "retryable_failure"
    diagnostics = str(publisher.diagnostics(now))
    assert "123456789012345678" not in diagnostics
    assert "real-secret" not in diagnostics
    assert "real-secret" not in caplog.text


def test_dry_run_uses_only_test_channel_and_does_not_touch_policy():
    channel = Channel()
    publisher = SignalPublisher(Bot(channel), config())
    before = publisher.diagnostics()["last_publication_time"]
    assert asyncio.run(publisher.dry_run()) == "sent"
    assert "NON-TRADING FIXTURE" in channel.calls[0][0]
    assert publisher.diagnostics()["last_publication_time"] == before
