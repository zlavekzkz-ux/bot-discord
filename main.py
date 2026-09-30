import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View

# --- CONFIGURATION (Remplace les IDs ci-dessous par les tiens) ---
MEMBERS_CHANNEL_ID = 123456789012345678  # ID du salon vocal Membres
BOTS_CHANNEL_ID = 123456789012345678     # ID du salon vocal Bots
VERIFIED_ROLE_ID = 123456789012345678    # ID du rôle donné à la vérification
TICKET_CATEGORY_ID = 123456789012345678  # ID de la catégorie où créer les tickets

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- VUES INTERACTIVES (BOUTONS) ---

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'inscrire / Se vérifier", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role:
            if role in interaction.user.roles:
                await interaction.response.send_message("Tu es déjà vérifié !", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("Tu as été vérifié avec succès ! 🎉", ephemeral=True)
        else:
            await interaction.response.send_message("Erreur : Rôle introuvable. Vérifie l'ID.", ephemeral=True)

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Fermeture du ticket dans 5 secondes...")
        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=5))
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un ticket", style=discord.ButtonStyle.blurple, emoji="📩", custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="Ticket Ouvert",
            description=f"Bonjour {interaction.user.mention}, explique ton problème ici. Un membre du staff va te répondre.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Ton ticket a été créé : {channel.mention}", ephemeral=True)

# --- ÉVÉNEMENTS & TÂCHES DE FOND ---

@tasks.loop(minutes=10)
async def update_stats():
    for guild in bot.guilds:
        members_count = sum(1 for member in guild.members if not member.bot)
        bots_count = sum(1 for member in guild.members if member.bot)
        
        members_channel = guild.get_channel(MEMBERS_CHANNEL_ID)
        bots_channel = guild.get_channel(BOTS_CHANNEL_ID)
        
        if members_channel:
            await members_channel.edit(name=f"👥 | Membres : {members_count}")
        if bots_channel:
            await bots_channel.edit(name=f"🤖 | Bots : {bots_count}")

@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")
    bot.add_view(VerifyView())
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
    if not update_stats.is_running():
        update_stats.start()

# --- COMMANDES POUR DÉPLOYER LES PANNEAUX ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    embed = discord.Embed(
        title="Vérification",
        description="Clique sur le bouton ci-dessous pour accéder à la totalité du serveur.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=VerifyView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="Support & Tickets",
        description="Besoin d'aide ou d'un signalement ? Clique sur le bouton ci-dessous pour ouvrir un ticket.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TicketView())

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("Erreur : Aucun token trouvé.")
