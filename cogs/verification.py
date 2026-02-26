import discord
from discord.ext import commands
from discord import app_commands
from utils.locales import get_text, DEFAULT_LOCALE

# Mapping of role names to language codes (Must match cogs/language.py)
ROLE_TO_LANG = {
    "Greek": "GR",
    "English": "EN",
    "Spanish": "ES",
    "Russian": "RU",
    "Japanese": "JA"
}

def get_user_lang(user: discord.Member) -> str:
    """Detect user language based on their roles."""
    for role in user.roles:
        if role.name in ROLE_TO_LANG:
            return ROLE_TO_LANG[role.name]
    return DEFAULT_LOCALE

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify / Επαλήθευση", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        role_name = "Thronidian"
        
        # Determine language for response
        lang = get_user_lang(user)
        
        role = discord.utils.get(guild.roles, name=role_name)

        if not role:
            # Auto-create the role if it doesn't exist
            try:
                role = await guild.create_role(name=role_name, reason="Required for verification system")
            except discord.Forbidden:
                await interaction.response.send_message(get_text("role_error", lang), ephemeral=True)
                return

        # Check if user has the verification role OR "The Creator" / "Admins" role OR is an Administrator
        has_creator_role = discord.utils.get(user.roles, name="The Creator")
        has_admin_role = discord.utils.get(user.roles, name="Admins")
        is_admin_perm = user.guild_permissions.administrator
        
        if role in user.roles or has_creator_role or has_admin_role or is_admin_perm:
            await interaction.response.send_message(get_text("already_verified", lang), ephemeral=True)
        else:
            try:
                await user.add_roles(role)
                await interaction.response.send_message(get_text("verified_msg", lang), ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message(get_text("role_error", lang), ephemeral=True)

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_verification", description="Post the verification menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_verification(self, interaction: discord.Interaction):
        # Use default locale for the static embed, or bilingual
        # Following the pattern in the file: specific bilingual title/desc are hardcoded in locales now
        lang = DEFAULT_LOCALE
        embed = discord.Embed(
            title=get_text("verification_title", lang),
            description=get_text("verification_desc", lang),
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, view=VerificationView())

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerificationView())

async def setup(bot):
    await bot.add_cog(Verification(bot))
