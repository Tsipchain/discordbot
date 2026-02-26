import discord
from discord.ext import commands
import logging

logger = logging.getLogger('thronos_bot.welcome')

class Welcome(commands.Cog):
    """Enhanced welcome system with language selection."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Triggered when a new member joins the server."""
        try:
            # Send DM with welcome message and language selection
            welcome_embed = discord.Embed(
                title="🎉 Welcome to Thronos Network!",
                description=(
                    "Welcome! Please select your preferred language:\n\n"
                    "🇬🇧 **English** - Type `!language` and select English\n"
                    "🇬🇷 **Ελληνικά** - Πληκτρολογήστε `!language` και επιλέξτε Ελληνικά\n"
                    "🇪🇸 **Español** - Escribe `!language` y selecciona Español\n"
                    "🇷🇺 **Русский** - Введите `!language` и выберите Русский\n"
                    "🇯🇵 **日本語** - `!language`と入力して日本語を選択\n\n"
                    "Then click the **Verify** button in the verification channel to access all channels!"
                ),
                color=0x00ff00
            )
            welcome_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
            
            try:
                await member.send(embed=welcome_embed)
                logger.info(f"Sent welcome DM to {member}")
            except discord.Forbidden:
                logger.warning(f"Could not send DM to {member} (DMs disabled)")
            
            # Post in general channel if it exists
            general_channel = discord.utils.get(member.guild.text_channels, name="general")
            if general_channel:
                await general_channel.send(
                    f"👋 Welcome {member.mention} to **Thronos Network**! "
                    f"Please select your language with `!language` and verify to access channels."
                )
                logger.info(f"Posted welcome message for {member} in #general")
        
        except Exception as e:
            logger.error(f"Error in on_member_join: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
