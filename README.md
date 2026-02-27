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

## Webhook Deployment Note

If deploying on external cloud providers (like Railway, Vercel, or Heroku), the Pytheia Webhook component automatically detects the provider's native `PORT` string. No internal code adjustments are required.
