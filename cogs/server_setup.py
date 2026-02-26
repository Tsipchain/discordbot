import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup

class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_html(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                return None

    async def get_roadmap_embed(self):
        url = "https://thrchain.up.railway.app/roadmap"
        html = await self.fetch_html(url)
        
        embed = discord.Embed(
            title="🗺️ Official Roadmap / Χάρτης / Mapa", 
            description=f"**Live Sync Source**: [Thronos Network]({url})\nUpdates from the dev team.", 
            color=0x2ecc71
        )
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract list items
            items = []
            for li in soup.find_all('li'):
                text = li.get_text(strip=True)
                # Filter for relevant roadmap items using status emojis
                if "✅" in text or "⏳" in text or "🔄" in text:
                    items.append(text)
            
            if items:
                # Split into chunks of 1024 chars for Fields if needed
                # For now, let's categorize by Status
                completed = [i for i in items if "✅" in i]
                in_progress = [i for i in items if "⏳" in i]
                
                # Helper to chunk text
                def chunk_list(data_list, chunk_size=5):
                    return [data_list[i:i + chunk_size] for i in range(0, len(data_list), chunk_size)]

                if completed:
                    chunks = chunk_list(completed, 8) # 8 items per field
                    for idx, chunk in enumerate(chunks):
                        name = "✅ Completed / Ολοκληρωμένα" if idx == 0 else "✅ Completed (cont.)"
                        val = "\n".join(chunk)
                        if len(val) > 1024: val = val[:1021] + "..."
                        embed.add_field(name=name, value=val, inline=False)
                
                if in_progress:
                    val = "\n".join(in_progress)
                    if len(val) > 1024: val = val[:1021] + "..."
                    embed.add_field(name="⏳ In Progress / Σε εξέλιξη", value=val, inline=False)
        
        return embed

    async def get_whitepaper_embed(self):
        url = "https://thrchain.up.railway.app/whitepaper"
        html = await self.fetch_html(url)
        
        embed = discord.Embed(
            title="📜 Thronos Whitepaper / Λευκή Βίβλος", 
            url=url,
            color=0xecf0f1
        )
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to grab structure: H2/H3 -> Paragraphs
            # We want to summarize the content sections
            
            # Strategy: Find headings, take the first paragraph after them
            sections = []
            
            # Find the main container if possible, or just iterate body
            # content = soup.find('main') or soup.body
            
            for header in soup.find_all(['h2', 'h3']):
                header_text = header.get_text(strip=True)
                # Skip simple navigation headers
                if len(header_text) < 3 or "Menu" in header_text: continue
                
                # Find next sibling paragraph
                next_node = header.find_next_sibling()
                content = ""
                while next_node and next_node.name != 'h2' and next_node.name != 'h3':
                    if next_node.name == 'p':
                        text = next_node.get_text(strip=True)
                        if len(text) > 30: # meaningful text
                            content += text + "\n\n"
                            if len(content) > 300: break # limit per section
                    next_node = next_node.find_next_sibling()
                
                if content:
                    sections.append((header_text, content))
                    if len(sections) >= 6: break # Limit total fields
            
            if sections:
                embed.description = f"**Executive Summary**\nRead full doc at [thronos.network]({url})"
                for title, body in sections:
                    if len(body) > 1024: body = body[:1021] + "..."
                    embed.add_field(name=f"🔹 {title}", value=body, inline=False)
            else:
                 # Fallback if structure is weird
                 embed.description = "Could not parse structure automatically. Please view the PDF or Website."

        return embed

    async def create_category_and_channels(self, guild, category_name, channels):
        """Helper to create a category and its channels if they don't exist."""
        # Find or create category
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            print(f"Created category: {category_name}")
        
        # Create channels
        for channel_name in channels:
            channel = discord.utils.get(guild.text_channels, name=channel_name, category=category)
            if not channel:
                await guild.create_text_channel(channel_name, category=category)
                print(f"Created channel: {channel_name} in {category_name}")

    @commands.hybrid_command(name="setup_server", description="Auto-configure server channels with unified multi-language content")
    async def setup_server(self, ctx: commands.Context):
        # Handle interaction or context
        user = ctx.author
        
        # Permission check
        is_allowed = False
        if user.guild_permissions.administrator:
            is_allowed = True
        elif discord.utils.get(user.roles, name="The Creator"):
            is_allowed = True
        elif discord.utils.get(user.roles, name="Admins"):
            is_allowed = True
            
        if not is_allowed:
            await ctx.reply("❌ You do not have permission to run this command (Admin, 'Admins' or 'The Creator' required).", ephemeral=True)
            return

        # Defer check
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)
        else:
             await ctx.typing()

        guild = ctx.guild

        structure = {
            "📜 Information": ["announcements", "roadmap", "whitepaper"],
            "📊 Thronos Network": ["network-stats", "governance"],
            "🛠️ Ecosystem": ["token-factory", "nft-marketplace", "smart-contracts", "decent-music"],
            "🎓 Community & Earn": ["learn-and-earn", "general"],
            "🎮 Gaming": ["crypto-hunters"]
        }
        
        # Unified Content Map (EN, EL, ES, RU, JA)
        # Format: key: { "url": ..., "en": (Title, Desc), ... }
        unified_content = {
            "token-factory": {
                "url": "https://thrchain.up.railway.app/tokens",
                "en": ("🏭 Token Factory", "Create your own tokens with one click. ERC-20 compatible with full control."),
                "el": ("🏭 Εργοστάσιο Token", "Δημιουργήστε τα δικά σας tokens με μία κλικ. ERC-20 compatible με πλήρη έλεγχο."),
                "es": ("🏭 Fábrica de Tokens", "Crea tus propios tokens con un clic. Compatible con ERC-20 con control total."),
                "ru": ("🏭 Фабрика Токенов", "Создавайте свои токены одним кликом. Совместимость с ERC-20 и полный контроль."),
                "ja": ("🏭 トークン工場", "ワンクリックで独自のトークンを作成。ERC-20互換で完全制御。")
            },
            "nft-marketplace": {
                "url": "https://thrchain.up.railway.app/nft",
                "en": ("🖼️ NFT Marketplace", "Mint, buy and sell unique digital artworks."),
                "el": ("🖼️ Αγορά NFT", "Mint, αγοράστε και πουλήστε μοναδικά ψηφιακά έργα τέχνης."),
                "es": ("🖼️ Mercado NFT", "Acuña, compra y vende obras de arte digitales únicas."),
                "ru": ("🖼️ NFT Маркетплейс", "Создавайте, покупайте и продавайте уникальные цифровые произведения искусства."),
                "ja": ("🖼️ NFT マーケットプレイス", "ユニークなデジタルアートをミント、購入、販売。")
            },
            "smart-contracts": {
                "url": "https://thrchain.up.railway.app/evm",
                "en": ("📜 Smart Contracts", "Deploy EVM-compatible smart contracts with ready templates."),
                "el": ("📜 Έξυπνα Συμβόλαια", "Deploy EVM-compatible smart contracts με έτοιμα templates."),
                "es": ("📜 Contratos Inteligentes", "Despliega contratos inteligentes compatibles con EVM con plantillas listas."),
                "ru": ("📜 Смарт-контракты", "Развертывайте EVM-совместимые смарт-контракты с готовыми шаблонами."),
                "ja": ("📜 スマートコントラクト", "既製テンプレートでEVM互換スマートコントラクトをデプロイ。")
            },
            "decent-music": {
                "url": "https://thrchain.up.railway.app/music",
                "en": ("🎵 Decent Music", "Decentralized music platform for artists and listeners."),
                "el": ("🎵 Αποκεντρωμένη Μουσική", "Αποκεντρωμένη πλατφόρμα μουσικής για καλλιτέχνες και ακροατές."),
                "es": ("🎵 Música Descentralizada", "Plataforma de música descentralizada para artistas y oyentes."),
                "ru": ("🎵 Децентрализованная Музыка", "Децентрализованная музыкальная платформа для артистов и слушателей."),
                "ja": ("🎵 分散型音楽", "アーティストとリスナーのための分散型音楽プラットフォーム。")
            },
            "learn-and-earn": {
                "url": "https://thrchain.up.railway.app/courses",
                "en": ("📚 Learn & Earn", "Learn about blockchain and earn THR tokens by completing courses."),
                "el": ("📚 Μάθε & Κέρδισε", "Μάθετε για το blockchain και κερδίστε THR tokens ολοκληρώνοντας μαθήματα."),
                "es": ("📚 Aprende y Gana", "Aprende sobre blockchain y gana tokens THR completando cursos."),
                "ru": ("📚 Учись и Зарабатывай", "Изучайте блокчейн и зарабатывайте токены THR, проходя курсы."),
                "ja": ("📚 学んで稼ぐ", "ブロックチェーンを学び、コース完了でTHRトークンを獲得。")
            },
            "governance": {
                "url": "https://thrchain.up.railway.app/governance",
                "en": ("🏛️ DAO Governance", "Vote on proposals and shape the future of the network."),
                "el": ("🏛️ Διακυβέρνηση DAO", "Ψηφίστε για προτάσεις και διαμορφώστε το μέλλον του δικτύου."),
                "es": ("🏛️ Gobernanza DAO", "Vota propuestas y da forma al futuro de la red."),
                "ru": ("🏛️ DAO Управление", "Голосуйте за предложения и формируйте будущее сети."),
                "ja": ("🏛️ DAO ガバナンス", "提案に投票し、ネットワークの未来を形作りましょう。")
            },
            "crypto-hunters": {
                "url": "https://thrchain.up.railway.app/game",
                "en": ("🎮 Crypto Hunters", "Join the hunt! Help us test the upcoming game. Vote on features."),
                "el": ("🎮 Κυνηγοί Crypto", "Λάβετε μέρος στο κυνήγι! Βοηθήστε μας να δοκιμάσουμε το επερχόμενο παιχνίδι."),
                "es": ("🎮 Cazadores Crypto", "¡Únete a la caza! Ayúdanos a probar el próximo juego."),
                "ru": ("🎮 Охотники за Крипто", "Присоединяйтесь к охоте! Помогите протестировать будущую игру."),
                "ja": ("🎮 クリプトハンターズ", "ハントに参加しよう！今後のゲームのテストにご協力ください。")
            }
        }

        try:
            for category, channels in structure.items():
                await self.create_category_and_channels(guild, category, channels)
            
            # --- Content Population ---
            async def update_channel_content(channel, content=None, file=None, embed=None, topic=None):
                if not channel: return
                
                # Update Topic if changed
                if topic and channel.topic != topic:
                    try: 
                        await channel.edit(topic=topic)
                    except: pass

                # Manage messages (delete older bot msgs to keep clean)
                # For unified content, we want ONE main message with the embed/file
                
                # Delete old bot messages first to avoid duplicates or clutter
                messages_to_delete = []
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user:
                        messages_to_delete.append(message)
                
                if messages_to_delete:
                    # If we are sending a file, or if there are multiple old messages, just clear them and send fresh
                    if file or len(messages_to_delete) > 1:
                        for m in messages_to_delete:
                            await m.delete()
                        await channel.send(content=content, embed=embed, file=file)
                    else:
                        # Single message, just edit it
                        msg = messages_to_delete[0]
                        # If we have a file, we can't 'edit' it in easily without removing attachments sometimes, 
                        # safer to delete and resend for files
                        if file:
                             await msg.delete()
                             await channel.send(content=content, file=file, embed=embed)
                        else:
                             await msg.edit(content=content, embed=embed)
                else:
                    await channel.send(content=content, embed=embed, file=file)

            # 1. Roadmap (Unified & Synced)
            roadmap_channel = discord.utils.get(guild.text_channels, name="roadmap")
            try:
                roadmap_embed = await self.get_roadmap_embed()
                # Topic: Brief description
                topic = "🇬🇧 Official project milestones & development timeline | 🇬🇷 Επίσημοι στόχοι έργου & χρονοδιάγραμμα | 🇪🇸 Hitos oficiales del proyecto"
                await update_channel_content(roadmap_channel, embed=roadmap_embed, file=discord.File("Thronos_Roadmap.pdf"), topic=topic)
            except Exception as e:
                print(f"Error syncing roadmap: {e}")
                fallback_embed = discord.Embed(title="Map / Χάρτης / Mapa", description="Offline Mode", color=0x2ecc71)
                await update_channel_content(roadmap_channel, embed=fallback_embed, file=discord.File("Thronos_Roadmap.pdf"))

            # 2. Whitepaper (Unified & Synced)
            whitepaper_channel = discord.utils.get(guild.text_channels, name="whitepaper")
            try:
                whitepaper_embed = await self.get_whitepaper_embed()
                topic = "🇬🇧 Complete technical documentation & vision | 🇬🇷 Πλήρης τεχνική τεκμηρίωση & όραμα | 🇪🇸 Documentación técnica completa y visión | 🇷🇺 Полная техническая документация | 🇯🇵 完全な技術文書とビジョン"
                await update_channel_content(whitepaper_channel, embed=whitepaper_embed, file=discord.File("Thronos_Whitepaper.pdf"), topic=topic)
            except Exception as e:
                 print(f"Error syncing whitepaper: {e}")
                 fallback_embed = discord.Embed(title="Whitepaper / Βίβλος / Libro", description="Offline Mode", color=0xecf0f1)
                 await update_channel_content(whitepaper_channel, embed=fallback_embed, file=discord.File("Thronos_Whitepaper.pdf"))

            # 3. Network Stats (Unified)
            stats_channel = discord.utils.get(guild.text_channels, name="network-stats")
            stats_embed = discord.Embed(title="📊 Network Statistics / Στατιστικά / Статистика / 統計", color=0x3498db)
            stats_embed.description = (
                "🇬🇧 **Live Dashboard**: Monitor the pulse of the Thronos Network in real-time.\n"
                "🇬🇷 **Ζωντανός Πίνακας**: Παρακολουθήστε τον παλμό του δικτύου σε πραγματικό χρόνο.\n"
                "🇪🇸 **Panel en Vivo**: Monitorea el pulso de la red en tiempo real.\n"
                "🇷🇺 **Живая Статистика**: Следите за пульсом сети в реальном времени.\n"
                "🇯🇵 **ライブ統計**: リアルタイムでThronosネットワークの脈動を監視します。"
            )
            stats_embed.add_field(name="🔗 Link / Σύνδεσμος / Ссылка / リンク", value="[dashboard.thronos.network](https://thrchain.up.railway.app/)", inline=False)
            topic = "🇬🇧 Monitor network in real-time | 🇬🇷 Παρακολουθήστε το δίκτυο σε πραγματικό χρόνο | 🇪🇸 Monitorea la red en tiempo real | 🇷🇺 Следите за сетью | 🇯🇵 ネットワークを監視"
            await update_channel_content(stats_channel, embed=stats_embed, topic=topic)

            # 4. Ecosystem & Others (Unified Embeds)
            for channel_name, data in unified_content.items():
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                url = data["url"]
                
                # Create Unified Embed
                # Use English title as main, but include others in fields
                main_title, _ = data["en"]
                embed = discord.Embed(title=main_title, url=url, color=0x9b59b6)
                
                # Add language fields
                embed.add_field(name="🇬🇧 English", value=data["en"][1], inline=False)
                embed.add_field(name="🇬🇷 Ελληνικά", value=data["el"][1], inline=False)
                embed.add_field(name="🇪🇸 Español", value=data["es"][1], inline=False)
                embed.add_field(name="🇷🇺 Русский", value=data["ru"][1], inline=False)
                embed.add_field(name="🇯🇵 日本語", value=data["ja"][1], inline=False)
                
                embed.add_field(name="🔗 Link", value=f"[Open Page]({url})", inline=False)
                
                # Topic: Use descriptions instead of titles (shortened to fit 1024 limit)
                # Include all 5 languages with shorter text (50 chars each to fit)
                topic_parts = [
                    f"🇬🇧 {data['en'][1][:50]}",
                    f"🇬🇷 {data['el'][1][:50]}",
                    f"🇪🇸 {data['es'][1][:50]}",
                    f"🇷🇺 {data['ru'][1][:50]}",
                    f"🇯🇵 {data['ja'][1][:50]}"
                ]
                topic = " | ".join(topic_parts)
                if len(topic) > 1024: 
                    topic = topic[:1021] + "..."
                
                await update_channel_content(channel, embed=embed, topic=topic)

                
                await update_channel_content(channel, embed=embed, topic=topic)

            # --- 5. Admin Role Setup ---
            # Create/Get 'Admin' role with Administrator permissions
            admin_role_name = "Admin"
            admin_role = discord.utils.get(guild.roles, name=admin_role_name)
            
            if not admin_role:
                try:
                    admin_role = await guild.create_role(
                        name=admin_role_name, 
                        permissions=discord.Permissions(administrator=True),
                        color=discord.Color.red(),
                        reason="Auto-setup for Admin privileges"
                    )
                    await ctx.send(f"✅ Created new role **{admin_role_name}** with Administrator permissions.")
                except discord.Forbidden:
                    await ctx.send(
                        "🛑 **Permission Error**: I cannot create the 'Admin' role.\n"
                        "**Fix:** Go to **Server Settings > Roles**, find my bot role (Thronos Bot), and **drag it higher** than the roles you want me to manage.\n"
                        "Also make sure I have 'Manage Roles' and 'Administrator' permission."
                    )
                except Exception as e:
                    await ctx.send(f"⚠️ Could not create Admin role: {e}")
            
            if admin_role:
                # Assign to Command Invoker (You)
                if admin_role not in user.roles:
                    try:
                        await user.add_roles(admin_role)
                        await ctx.send(f"✅ Assigned **{admin_role_name}** role to you ({user.display_name}).")
                    except Exception as e:
                         print(f"Failed to assign admin to invoker: {e}")

                # Assign to 'cryptox4490' or anyone with 'The Creator' role
                # Note: 'The Creator' logic handles cryptox4490 if they have that role, 
                # but we also check by name just in case.
                
                # Fetch all members (requires intent)
                for member in guild.members:
                    # Check for 'The Creator' role
                    has_creator = discord.utils.get(member.roles, name="The Creator")
                    
                    # Check for specific username 'cryptox4490'
                    is_target_user = member.name == "cryptox4490"
                    
                    if (has_creator or is_target_user) and admin_role not in member.roles:
                        try:
                            await member.add_roles(admin_role)
                            await ctx.send(f"✅ Assigned **{admin_role_name}** role to {member.display_name}.")
                        except Exception as e:
                            print(f"Failed to assign admin to {member.name}: {e}")

            await ctx.reply("✅ Unified multi-language server updated!")
        except Exception as e:
            await ctx.reply(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(ServerSetup(bot))
