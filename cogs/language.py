import discord
from discord.ext import commands
from discord import app_commands
from utils.locales import get_text

LANGUAGE_ROLES = {
    "GR": "Greek",
    "EN": "English",
    "ES": "Spanish",
    "RU": "Russian",
    "JA": "Japanese"
}

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def update_lang_role(self, interaction: discord.Interaction, lang_code: str):
        user = interaction.user
        guild = interaction.guild
        
        # Remove existing language roles
        roles_to_remove = []
        for role in user.roles:
            if role.name in LANGUAGE_ROLES.values():
                roles_to_remove.append(role)
        
        if roles_to_remove:
            await user.remove_roles(*roles_to_remove)

        # Add new language role
        role_name = LANGUAGE_ROLES[lang_code]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
             # Auto-create the role if it doesn't exist
            try:
                role = await guild.create_role(name=role_name, reason="Required for language selection")
            except discord.Forbidden:
                # Fallback to English error if we can't determine language yet (though we are setting it now)
                await interaction.response.send_message(get_text("role_error", "EN"), ephemeral=True)
                return

        try:
            await user.add_roles(role)
            await interaction.response.send_message(get_text("lang_selected", lang_code), ephemeral=True)
        except discord.Forbidden:
             await interaction.response.send_message(get_text("role_error", lang_code), ephemeral=True)

    @discord.ui.button(label="🇬🇷 Greek", style=discord.ButtonStyle.secondary, custom_id="lang_gr")
    async def gr_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_lang_role(interaction, "GR")

    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.secondary, custom_id="lang_en")
    async def en_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_lang_role(interaction, "EN")

    @discord.ui.button(label="🇪🇸 Spanish", style=discord.ButtonStyle.secondary, custom_id="lang_es")
    async def es_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_lang_role(interaction, "ES")

    @discord.ui.button(label="🇷🇺 Russian", style=discord.ButtonStyle.secondary, custom_id="lang_ru")
    async def ru_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_lang_role(interaction, "RU")

    @discord.ui.button(label="🇯🇵 Japanese", style=discord.ButtonStyle.secondary, custom_id="lang_ja")
    async def ja_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_lang_role(interaction, "JA")
class Language(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_language", description="Post the language selection menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_language(self, interaction: discord.Interaction):
        await interaction.response.send_message("Select your language / Επιλέξτε τη γλώσσα σας:", view=LanguageView())

    @commands.Cog.listener()
    async def on_ready(self):
        # Register the persistent view so buttons work after restart
        self.bot.add_view(LanguageView())

async def setup(bot):
    await bot.add_cog(Language(bot))
