import logging

import discord

import bot


def test_login_failure_is_reported_without_token_or_response(monkeypatch, caplog):
    secret = "a-real-looking-discord-token"

    class InvalidTokenBot:
        def run(self, token):
            assert token == secret
            raise discord.LoginFailure("401 response body containing " + secret)

    monkeypatch.setattr(bot, "TOKEN", secret)
    monkeypatch.setattr(bot, "THRONOS_API_URL", "https://api.thronoschain.org/api")
    monkeypatch.setattr(bot, "ThronosBot", InvalidTokenBot)
    caplog.set_level(logging.CRITICAL)

    assert bot.run_bot() == 1
    assert "DISCORD_AUTH_FAILED" in caplog.text
    assert secret not in caplog.text
    assert "401 response body" not in caplog.text


def test_missing_token_stops_before_constructing_bot(monkeypatch, caplog):
    monkeypatch.setattr(bot, "TOKEN", "")
    monkeypatch.setattr(bot, "ThronosBot", lambda: (_ for _ in ()).throw(AssertionError()))
    caplog.set_level(logging.CRITICAL)

    assert bot.run_bot() == 1
    assert "DISCORD_TOKEN_MISSING" in caplog.text
