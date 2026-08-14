# Thronos V3.6 Discord Bot

The official Discord integration bot for the Thronos V3.6 Ecosystem. This bot bridges the gap between your Discord community and the live Thronos blockchain, providing real-time statistics, smart contract monitoring, AI network integration, and DAO governance directly inside your server.

## Features

- **🌐 Live Ecosystem Monitoring:** Real-time updates on Thronos Network TPS, Block Height, Token Prices, Burned Supply, and Active Wallets.
- **🤖 Decentralized AI Hub:** Users can interact with the Thronos AI Network using `!ask`.
- **🔗 Wallet Binding:** Users can bind their Thronos EVM wallets via `!bind <address>` to securely consume their on-chain AI credits for premium models.
- **📜 Smart Contract Announcements:** A background EVM loop detects new contracts and tokens deployed on Thronos and automatically announces them in `#smart-contracts`.
- **⚡ Pytheia Autonomous Yield Hooks:** An embedded webhook server (`0.0.0.0:5005`) listens for live yield generation or arbitrage trades from Pytheia bots on the network and broadcasts them to `#autonomous-trading`.
- **🏛️ In-Discord DAO Voting:** Admins can launch interactive voting proposals (`!propose`) with persistent database storage.
- **🌍 Multi-Lingual Server Bootstrapping:** `!setup_server` automatically creates fully formatted channel hierarchies in English, Greek, Spanish, Russian, and Japanese for international communities.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Tsipchain/discordbot.git
   cd discordbot
   ```

2. **Install dependencies:**
   Make sure you have Python 3.8+ installed.
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your credentials:
   - `DISCORD_TOKEN`: Your bot token from the Discord Developer Portal.
   - `THRONOS_API_URL`: (Optional) Defaults to `https://api.thronoschain.org/api`.

4. **Run the bot:**
   ```bash
   python3 bot.py
   ```

## Daily community promotion

The bot contains a server-side worker that checks hourly and reserves a database row
before posting. `UNIQUE(campaign, destination, promotion_date)` prevents another
process or restart from posting a second advertisement on the same UTC date. This is
a local campaign: it does not call a Telegram promotion webhook and therefore cannot
form a Discord/Telegram promotion loop.

Set the variables documented in `.env.example`. `DISCORD_GENERAL_CHANNEL_ID` must be
the 17–20 digit ID of the configured General/community channel and all public links
must use HTTPS. `SIGBALBOT_TELEGRAM_URL` and the channel ID are required when
`COMMUNITY_PROMOTION_ENABLED=true`; the landing page, Wallet, and Sentinel links are
optional. Values below 3600 for the check interval are clamped to one hour. The
interval is only the polling frequency, never a posting frequency.

Administrators can run `/promotion_status` for redacted diagnostics. It reports the
enabled state, last successful date/message, safe error code, and next eligible UTC
date. It never returns tokens, secrets, headers, webhook URLs, or Discord response
bodies. The same safe fields are available to server health monitoring at
`GET /health/community-promotion`.

### Deployment

1. Back up the persistent `data/thronos.db` volume and deploy the new revision. On
   startup `database.init_db()` applies the idempotent schema; the equivalent SQL is
   in `migrations/001_community_promotions.sql` and
   `migrations/002_future_btc_publications.sql` for managed migration workflows.
2. Attach a persistent Railway volume for `data/` (or provide equivalent durable
   storage), configure the promotion variables, and initially leave the feature off.
3. Start exactly one `web: python bot.py` process, confirm `/promotion_status`, then
   enable the campaign. Duplicate workers are database-safe, but SQLite requires all
   instances to share the same volume; for horizontally distributed deployment,
   migrate this schema to a shared transactional database first.
4. Grant the bot View Channel and Send Messages permissions only in the configured
   channel. Missing/forbidden channels are recorded as permanent safe failures rather
   than retried every hour.

### Rollback

Set `COMMUNITY_PROMOTION_ENABLED=false` before rolling back the application revision.
Keep the two new tables: they are inert and retain the daily idempotency history for a
later redeploy. If removal is mandatory, back up the database and drop
`community_promotions` and `future_btc_signal_events` only after the old code is live.
Do not delete only the current day's reservation while any promotion worker is active.

## SigBalBot sender integration contract

The exact production route is `POST /sigbalbot/free-btc-signal` on the discordbot
HTTPS origin. The sender must not include a channel ID. The only publication destination is
the discordbot server-side `FREE_BTC_SIGNAL_CHANNEL_ID` setting.

### Receiver environment and current behavior

| Variable | Purpose |
| --- | --- |
| `FREE_BTC_SIGNAL_RELAY_ENABLED` | Enables authenticated contract intake and storage. Defaults to `false`. |
| `FREE_BTC_SIGNAL_PUBLICATION_ENABLED` | Separately enables publication of accepted events. Defaults to `false`. |
| `FREE_BTC_SIGNAL_CHANNEL_ID` | Server-side production free-signals destination. It never appears in a sender payload. |
| `FREE_BTC_SIGNAL_TEST_CHANNEL_ID` | Server-side private destination used only by the administrator dry-run command. |
| `SIGBALBOT_RELAY_SECRET` | Dedicated shared HMAC secret for this contract. Never use a Discord/Telegram token or another API secret. |

Intake and publication are independent. With intake enabled and publication disabled,
the receiver validates and stores only. Publication additionally requires
`FREE_BTC_SIGNAL_PUBLICATION_ENABLED=true`, a valid server-configured
`FREE_BTC_SIGNAL_CHANNEL_ID`, and an HTTPS SigBalBot Telegram/public URL. Enabling
intake never implicitly enables publication.

Publication reserves an event before calling Discord, persists its message ID, and
allows no more than one published BTC signal in a rolling seven-day window. Events
accepted while that window is occupied become `weekly_limited` and are never queued for
later stale publication. Discord sends disable all mentions and escape summary markdown.
Publication state is separate from intake and records `received`,
`publication_pending`, `published`, `retryable_failure`, `permanent_failure`, or
`weekly_limited`, along with bounded attempts, safe errors, attempt timestamps, the
publication time, and Discord message ID. A stored message ID is conclusive success;
duplicate requests and restarted/concurrent receivers do not send it again.

Administrators can use `/sigbalbot_publication_status`, or server monitoring can read
`GET /health/sigbalbot-relay`, for intake/publication flags, a redacted channel ID,
pending count, last event/message/publication values, the last safe error, and next
weekly eligibility. Neither surface returns secrets or Discord response bodies.

### Authentication and byte-level encoding

Compute HMAC-SHA256 over the **exact raw HTTP request bytes**, not over receiver-side
canonicalized JSON. Send the digest as 64 lowercase hexadecimal characters (not
Base64) with this exact header:

```text
X-SigBalBot-Signature: sha256=<64-lowercase-hex-digest>
```

The receiver compares the complete `sha256=<digest>` value in constant time. The body
is UTF-8 JSON and is limited to 4096 bytes. A sender may use this precise serialization
because those resulting bytes are both signed and sent unchanged:

```python
import hashlib
import hmac
import json
import os

body = json.dumps(
    payload, separators=(",", ":"), ensure_ascii=False
).encode("utf-8")
signature = hmac.new(
    os.environ["SIGBALBOT_RELAY_SECRET"].encode("utf-8"),
    body,
    hashlib.sha256,
).hexdigest()
headers = {
    "Content-Type": "application/json",
    "X-SigBalBot-Signature": f"sha256={signature}",
}
# Send `body` directly. Do not pass `json=payload`, which may reserialize it.
```

### Exact JSON schema and validation

The object must contain **exactly** these fields; missing, additional, or differently
cased fields are rejected:

```json
{
  "contract_version": "1.0",
  "event_id": "stable-retry-safe-id",
  "symbol": "BTC/USDT",
  "signal": "LONG",
  "timeframe": "4h",
  "published_at": "2026-08-14T12:00:00Z",
  "valid_until": "2026-08-14T16:00:00Z",
  "price": 65000,
  "confidence": 92,
  "risk": "MEDIUM",
  "summary": "Finalized public BTC market thesis for educational analysis only."
}
```

* `contract_version`: string, exactly `1.0`.
* `event_id`: string, 1–128 ASCII characters matching `[A-Za-z0-9._:-]+`; it must be
  stable across sender retries.
* `symbol`: string, exactly `BTC/USDT`.
* `signal`: string enum `LONG` or `SHORT`; `HOLD` is rejected.
* `timeframe`: string matching `[1-9][0-9]?[mhdw]` (1–99 minutes/hours/days/weeks).
* `published_at` and `valid_until`: strings of at most 35 characters in ISO-8601 UTC
  form ending in uppercase `Z`. `published_at` may be at most 24 hours old and no more
  than five minutes in the future. `valid_until` must be later than both the receiver's
  current time and `published_at`.
* `price`: non-boolean JSON number greater than or equal to zero.
* `confidence`: non-boolean JSON number from 0 through 100, inclusive.
* `risk`: string enum `LOW`, `MEDIUM`, or `HIGH`.
* `summary`: non-empty string, at most 280 Unicode code points. HTML-like tags, `http://`
  or `https://`, `www.`, `@everyone`, `@here`, and Discord user-mention syntax are
  rejected. Arbitrary HTML, mentions, and links are therefore not accepted.

### Exact response contract

All response bodies are JSON. Current intake responses are:

| Condition | HTTP | Exact JSON body |
| --- | ---: | --- |
| Accepted new event | `200` | `{"status":"accepted","duplicate":false}` |
| Duplicate `event_id` | `200` | `{"status":"accepted","duplicate":true}` |
| Invalid/missing HMAC | `401` | `{"error":"INVALID_SIGNATURE"}` |
| Intake disabled | `404` | `{"error":"RELAY_DISABLED"}` |
| Stale/future/expired event | `400` | `{"error":"STALE_EVENT"}` |

When publication is enabled, these additional responses apply:

| Publication condition | HTTP | Exact JSON body |
| --- | ---: | --- |
| Seven-day rolling publication limit | `429` | `{"error":"WEEKLY_PUBLICATION_LIMIT"}` |
| Stored, but temporary Discord delivery failure | `503` | `{"error":"DISCORD_TEMPORARY_FAILURE","stored":true}` |

Other validation errors return HTTP `400` with a stable uppercase error code, and an
oversized body returns `413` with `{"error":"PAYLOAD_TOO_LARGE"}`. Senders must treat
both accepted responses as success. `event_id` has a database uniqueness constraint,
so its idempotency survives process restarts and duplicate POSTs cannot create another
stored event—or a second future Discord message.

### SigBalBot sender handoff

```dotenv
DISCORDBOT_BASE_URL=https://<discordbot-production-host>
FREE_BTC_SIGNAL_RELAY_ENABLED=true                 # receiver only
FREE_BTC_SIGNAL_PUBLICATION_ENABLED=false          # receiver-only independent opt-in
FREE_BTC_SIGNAL_CHANNEL_ID=<discord-channel-id>    # receiver only; never in payload
FREE_BTC_SIGNAL_TEST_CHANNEL_ID=<private-test-channel-id> # receiver only
SIGBALBOT_RELAY_SECRET=<dedicated-random-secret>   # same value on sender and receiver
```

```bash
BODY='<exact-compact-json-body>'
DIGEST=$(printf '%s' "$BODY" | openssl dgst -sha256 \
  -hmac '<dedicated-random-secret>' -hex | awk '{print $NF}')
curl --fail-with-body -X POST \
  'https://<discordbot-production-host>/sigbalbot/free-btc-signal' \
  -H 'Content-Type: application/json' \
  -H "X-SigBalBot-Signature: sha256=${DIGEST}" \
  --data-binary "$BODY"
```

Never put a real secret directly in shell history in production; the placeholder above
is only a copy-pasteable contract illustration.

### Exact private-test deployment sequence

1. Deploy with `FREE_BTC_SIGNAL_RELAY_ENABLED=false` and
   `FREE_BTC_SIGNAL_PUBLICATION_ENABLED=false`.
2. Configure `SIGBALBOT_RELAY_SECRET`, the production
   `FREE_BTC_SIGNAL_CHANNEL_ID`, the distinct private
   `FREE_BTC_SIGNAL_TEST_CHANNEL_ID`, and `SIGBALBOT_TELEGRAM_URL` (or
   `SIGBALBOT_PUBLIC_URL`) entirely on the receiver.
3. Restart discordbot so it loads the settings. Run
   `/sigbalbot_publication_status` as a Discord administrator and confirm both flags are
   false and the production channel ID is redacted.
4. Run `/sigbalbot_publication_test`. It sends only a clearly labeled non-trading
   fixture to `FREE_BTC_SIGNAL_TEST_CHANNEL_ID`; it creates no event ID and does not
   change weekly eligibility.
5. Enable `FREE_BTC_SIGNAL_RELAY_ENABLED=true`, restart, and POST a signed payload using
   the integration fixture shape but fresh `published_at`, `valid_until`, and `event_id`
   values. Confirm it is stored but the production channel remains unchanged.
6. Only after those checks, set `FREE_BTC_SIGNAL_PUBLICATION_ENABLED=true` and restart.
   Do not reuse the private test channel as the production channel. Roll back publication
   independently by setting only this flag to `false`.

## Webhook Deployment Note

If deploying on external cloud providers (like Railway, Vercel, or Heroku), the Pytheia Webhook component automatically detects the provider's native `PORT` string. No internal code adjustments are required.

## Discord startup troubleshooting

If Railway shows a traceback ending at `discord/http.py` in `request` (often line 778),
check the safe code immediately following it. `DISCORD_AUTH_FAILED` means Discord
rejected `DISCORD_TOKEN`—normally an expired, reset, copied client secret, or otherwise
invalid credential. Generate/copy the **bot token** from the Discord Developer Portal,
replace the Railway `DISCORD_TOKEN` variable, and redeploy. Do not use the application
ID, public key, client secret, webhook secret, or a token with surrounding quotes.

Startup now trims accidental leading/trailing whitespace and logs only stable error
codes. It deliberately does not print Discord response bodies, tokens, or Authorization
headers. `DISCORD_FORBIDDEN` instead means the token authenticated but the bot lacks the
required server/channel permission; correct the bot role rather than rotating secrets.
