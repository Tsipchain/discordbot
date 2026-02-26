import discord
from discord.ext import commands
from discord import app_commands
import os
from utils.locales import get_text

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Assume PDFs are in the parent directory of the bot folder
        self.roadmap_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '../Thronos_Roadmap.pdf')
        self.whitepaper_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '../Thronos_Whitepaper.pdf')

    def get_user_lang(self, interaction: discord.Interaction):
        # Logic to get language based on user roles
        user_roles = [role.name for role in interaction.user.roles]
        if "Greek" in user_roles: return "GR"
        if "English" in user_roles: return "EN"
        if "Spanish" in user_roles: return "ES"
        if "Russian" in user_roles: return "RU"
        if "Japanese" in user_roles: return "JA"
        return "GR" # Default

    @app_commands.command(name="roadmap", description="Get the Thronos Roadmap")
    async def roadmap(self, interaction: discord.Interaction):
        lang = self.get_user_lang(interaction)
        text = get_text("roadmap_desc", lang)
        
        if os.path.exists(self.roadmap_path):
            await interaction.response.send_message(content=text, file=discord.File(self.roadmap_path))
        else:
            await interaction.response.send_message(content=f"{text}\n(File not found at {self.roadmap_path})", ephemeral=True)

    @app_commands.command(name="whitepaper", description="Get the Thronos Whitepaper")
    async def whitepaper(self, interaction: discord.Interaction):
        lang = self.get_user_lang(interaction)
        text = get_text("whitepaper_desc", lang)

        if os.path.exists(self.whitepaper_path):
            await interaction.response.send_message(content=text, file=discord.File(self.whitepaper_path))
        else:
            await interaction.response.send_message(content=f"{text}\n(File not found at {self.whitepaper_path})", ephemeral=True)

    @app_commands.command(name="website", description="Get the Thronos Website link")
    async def website(self, interaction: discord.Interaction):
        lang = self.get_user_lang(interaction)
        text = get_text("website_desc", lang)
        await interaction.response.send_message(f"{text} https://thrchain.up.railway.app/")

async def setup(bot):
    await bot.add_cog(Info(bot))
