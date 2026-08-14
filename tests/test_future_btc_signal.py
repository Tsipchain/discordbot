import json
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
