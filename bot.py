import discord
from discord.ext import commands
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Configure logging
os.makedirs("logs", exist_ok=True)

# Create formatters
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler with rotation (10MB per file, keep 5 backups)
file_handler = RotatingFileHandler(
    'logs/thronos_bot.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger('thronos_bot')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class ThronosBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Required for role management
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Load extensions
        logger.info("Loading extensions...")
        await self.load_extension('cogs.info')
        await self.load_extension('cogs.language')
        await self.load_extension('cogs.verification')
        await self.load_extension('cogs.server_setup')
        await self.load_extension('cogs.network_stats')
        await self.load_extension('cogs.help_command')
        await self.load_extension('cogs.auto_sync')
        await self.load_extension('cogs.welcome')
        await self.load_extension('cogs.moderation')
        await self.load_extension('cogs.announcements')
        await self.load_extension('cogs.governance')
        await self.load_extension('cogs.ticker_status')
        await self.load_extension('cogs.leaderboard')
        await self.load_extension('cogs.nft_gallery')
        
        # Sync commands with Discord
        await self.tree.sync()
        logger.info("Commands synced!")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('Bot is ready!')

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    else:
        bot = ThronosBot()
        bot.run(TOKEN)
