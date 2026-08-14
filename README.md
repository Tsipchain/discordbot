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
   in `migrations/001_community_promotions.sql` for managed migration workflows.
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

## Future free BTC signal contract (storage only)

`POST /sigbalbot/free-btc-signal` is disabled by default with
`FREE_BTC_SIGNAL_RELAY_ENABLED=false`. When the storage contract is deliberately
tested, it requires HTTPS and an `X-SigBal-Signature: sha256=<HMAC-SHA256>` over the
raw body using the dedicated `SIGBALBOT_RELAY_SECRET`. It validates the versioned
BTC/USDT LONG/SHORT payload, timestamp freshness, bounded plain-text summary, and
stable unique `event_id`. Duplicate IDs return success without another row.

This release **does not post accepted events to Discord**, scan markets, make trading
decisions, or execute orders. A later delivery change must enforce at most one
finalized high-confidence public signal per rolling seven days, use only the
server-configured destination, include `valid_until` and an educational-risk notice,
and exclude paid Sentinel, subscriber, wallet, and execution data.

## Webhook Deployment Note

If deploying on external cloud providers (like Railway, Vercel, or Heroku), the Pytheia Webhook component automatically detects the provider's native `PORT` string. No internal code adjustments are required.
