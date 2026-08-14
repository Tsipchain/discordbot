import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

import database
import future_btc_signal as relay


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()
    monkeypatch.delenv("FREE_BTC_SIGNAL_RELAY_ENABLED", raising=False)


def payload(now=None, **changes):
    now = now or datetime.now(timezone.utc)
    data = {
        "contract_version": "1.0", "event_id": "stable-1", "symbol": "BTC/USDT",
        "signal": "LONG", "timeframe": "4h",
        "published_at": now.isoformat().replace("+00:00", "Z"),
        "valid_until": (now + timedelta(hours=4)).isoformat().replace("+00:00", "Z"),
        "price": 65000, "confidence": 90, "risk": "MEDIUM",
        "summary": "Finalized public market thesis. Educational analysis only."
    }
    data.update(changes)
    return data


def test_relay_disabled_by_default():
    assert relay.enabled() is False


def test_duplicate_event_id_is_idempotent():
    data = relay.validate_payload(payload())
    assert relay.store_event(data) is True
    assert relay.store_event(data) is False


@pytest.mark.parametrize("changes", [
    {"symbol": "ETH/USDT"}, {"signal": "HOLD"},
    {"summary": "Go to https://bad.example"}, {"summary": "hello @everyone"},
])
def test_invalid_payloads_rejected(changes):
    with pytest.raises(relay.ContractError):
        relay.validate_payload(payload(**changes))


def test_destination_fields_are_rejected():
    for field in ("channel_id", "guild_id", "role_id", "webhook_url"):
        with pytest.raises(relay.ContractError):
            relay.validate_payload(payload(**{field: "123456789012345678"}))


def test_stale_and_invalid_timestamps_rejected():
    now = datetime.now(timezone.utc)
    with pytest.raises(relay.ContractError):
        relay.validate_payload(payload(now - timedelta(days=2)), now=now)
    with pytest.raises(relay.ContractError):
        relay.validate_payload(payload(published_at="yesterday"), now=now)


def test_signature_is_constant_time_contract(monkeypatch):
    body = json.dumps(payload()).encode()
    monkeypatch.setenv("SIGBALBOT_RELAY_SECRET", "dedicated-test-secret")
    import hashlib, hmac
    signature = "sha256=" + hmac.new(b"dedicated-test-secret", body, hashlib.sha256).hexdigest()
    assert relay.verify_signature(body, signature)
    assert not relay.verify_signature(body, signature + "x")


def test_sender_contract_fixture_end_to_end(monkeypatch):
    fixture_path = Path(__file__).parent / "fixtures" / "sigbalbot_contract_v1.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    body = fixture["raw_body_utf8"].encode("utf-8")

    assert fixture["signature_header"] == relay.SIGNATURE_HEADER
    assert relay.verify_signature(
        body, fixture["signature_value"], fixture["shared_secret"]
    )
    data = relay.validate_payload(
        json.loads(body), now=datetime(2026, 8, 14, 12, 1, tzinfo=timezone.utc)
    )
    assert data["event_id"] == "fixture-event-20260814"

    class Request:
        secure = True
        headers = {fixture["signature_header"]: fixture["signature_value"]}

        async def read(self):
            return body

    real_validate = relay.validate_payload
    monkeypatch.setenv("FREE_BTC_SIGNAL_RELAY_ENABLED", "true")
    monkeypatch.setenv("SIGBALBOT_RELAY_SECRET", fixture["shared_secret"])
    monkeypatch.setattr(
        relay, "validate_payload",
        lambda value: real_validate(
            value, now=datetime(2026, 8, 14, 12, 1, tzinfo=timezone.utc)
        ),
    )

    first = asyncio.run(relay.handle_request(Request()))
    assert first.status == 200
    assert json.loads(first.body) == fixture["expected_new_response"]
    second = asyncio.run(relay.handle_request(Request()))
    assert second.status == 200
    assert json.loads(second.body) == fixture["expected_duplicate_response"]
