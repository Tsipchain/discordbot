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
THRONOS_API_URL = os.getenv('THRONOS_API_URL')

class ThronosBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Required for role management
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Load extensions
        logger.info("Loading extensions...")
        extensions = [
            'cogs.info', 'cogs.language', 'cogs.verification',
            'cogs.server_setup', 'cogs.network_stats', 'cogs.help_command',
            'cogs.auto_sync', 'cogs.welcome', 'cogs.moderation',
            'cogs.announcements', 'cogs.governance', 'cogs.ticker_status',
            'cogs.leaderboard', 'cogs.nft_gallery', 'cogs.ai_chat',
            'cogs.pytheia_webhook', 'cogs.evm_watcher',
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}")

        # Sync commands with Discord
        try:
            await self.tree.sync()
            logger.info("Commands synced!")
        except discord.Forbidden:
            logger.error(
                "Failed to sync commands: missing permissions. "
                "Ensure the bot has the 'applications.commands' scope."
            )
        except discord.HTTPException as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('Bot is ready!')

    async def on_command_error(self, ctx, error):
        """Global error handler for command errors including permission issues."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "You do not have the required permissions to use this command."
            )
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                f"I am missing required permissions: {', '.join(error.missing_permissions)}. "
                "Please check my role settings in Server Settings > Roles."
            )
        elif isinstance(error, commands.CommandInvokeError) and isinstance(
            error.original, discord.Forbidden
        ):
            await ctx.send(
                "I do not have permission to perform this action. "
                "Please ensure my role is positioned above the roles I need to manage "
                "and that I have the necessary permissions."
            )
            logger.error(f"Permission error in command {ctx.command}: {error.original}")
        else:
            logger.error(f"Unhandled error in command {ctx.command}: {error}")
            raise error

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    elif not THRONOS_API_URL:
        print("Error: THRONOS_API_URL not found in .env file.")
    else:
        bot = ThronosBot()
        bot.run(TOKEN)
