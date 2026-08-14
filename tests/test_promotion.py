import asyncio
import logging
from datetime import datetime, timezone

import pytest

import database
from promotion import PromotionConfig, PromotionService, build_message


class Message:
    id = 987654321098765432


class Channel:
    def __init__(self, failures=0):
        self.calls = []
        self.failures = failures

    async def send(self, content, **kwargs):
        self.calls.append((content, kwargs))
        if self.failures:
            self.failures -= 1
            raise OSError("network failed; secret-value must never be logged")
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


@pytest.fixture
def config():
    return PromotionConfig(True, 3600, 123456789012345678,
                           "https://t.me/SigBalBot", "https://sigbal.example/",
                           "https://api.thronoschain.org/downloads",
                           "https://api.thronoschain.org/wallet-pwa")


def test_daily_dedup_next_day_and_restart(config):
    async def scenario():
        channel = Channel()
        day_one = datetime(2026, 8, 14, tzinfo=timezone.utc)
        assert await PromotionService(Bot(channel), config).run_once(day_one) == "delivered"
        assert await PromotionService(Bot(channel), config).run_once(day_one) == "suppressed"
        assert len(channel.calls) == 1
        assert await PromotionService(Bot(channel), config).run_once(
            datetime(2026, 8, 15, tzinfo=timezone.utc)) == "delivered"
        assert len(channel.calls) == 2
    asyncio.run(scenario())


def test_concurrent_reservations_send_once(config):
    async def scenario():
        channel = Channel()
        now = datetime(2026, 8, 14, tzinfo=timezone.utc)
        results = await asyncio.gather(*[
            PromotionService(Bot(channel), config).run_once(now) for _ in range(8)
        ])
        assert results.count("delivered") == 1
        assert len(channel.calls) == 1
    asyncio.run(scenario())


def test_failed_send_is_retryable(config):
    async def scenario():
        channel = Channel(failures=3)
        sleeps = []

        async def sleep(delay):
            sleeps.append(delay)

        service = PromotionService(Bot(channel), config, sleep=sleep)
        now = datetime(2026, 8, 14, tzinfo=timezone.utc)
        assert await service.run_once(now) == "retryable"
        assert sleeps == [1, 2]
        assert await service.run_once(now) == "delivered"
    asyncio.run(scenario())


def test_missing_channel_fails_safely(config):
    async def scenario():
        service = PromotionService(Bot(None), config)
        assert await service.run_once(datetime(2026, 8, 14, tzinfo=timezone.utc)) == "permanent_failure"
        assert service.diagnostics()["last_safe_error_code"] == "CHANNEL_NOT_FOUND"
    asyncio.run(scenario())


def test_invalid_urls_channel_and_minimum_interval(monkeypatch):
    monkeypatch.setenv("COMMUNITY_PROMOTION_ENABLED", "true")
    monkeypatch.setenv("DISCORD_GENERAL_CHANNEL_ID", "123456789012345678")
    monkeypatch.setenv("SIGBALBOT_TELEGRAM_URL", "http://not-secure.example")
    with pytest.raises(ValueError):
        PromotionConfig.from_env()
    monkeypatch.setenv("SIGBALBOT_TELEGRAM_URL", "https://t.me/SigBalBot")
    monkeypatch.setenv("COMMUNITY_PROMOTION_CHECK_INTERVAL_SECONDS", "10")
    assert PromotionConfig.from_env().interval_seconds == 3600
    monkeypatch.setenv("DISCORD_GENERAL_CHANNEL_ID", "general")
    with pytest.raises(ValueError):
        PromotionConfig.from_env()


def test_no_mentions_or_secrets_in_message_and_diagnostics(config):
    text = build_message(config)
    assert "@everyone" not in text and "@here" not in text
    service = PromotionService(Bot(Channel()), config)
    diagnostics = str(service.diagnostics())
    assert "123456789012345678" not in diagnostics
    assert "DISCORD_TOKEN" not in diagnostics and "SIGBALBOT_RELAY_SECRET" not in diagnostics


def test_secret_not_logged_on_error(config, caplog):
    async def scenario():
        caplog.set_level(logging.WARNING)
        await PromotionService(
            Bot(Channel(failures=3)), config, sleep=lambda _: asyncio.sleep(0)
        ).run_once()
        assert "secret-value" not in caplog.text
    asyncio.run(scenario())
