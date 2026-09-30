import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import datetime
import random
import string
import io
from PIL import Image, ImageDraw
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- MINI SERVEUR POUR KEEP-ALIVE RENDER ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot OK")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- CONFIGURATION DES IDS ---
MEMBERS_CHANNEL_ID = 1554876901099700255
BOTS_CHANNEL_ID = 1554876945227972608
VERIFIED_ROLE_ID = 1554878361988235344
TICKET_CATEGORY_ID = 1554871964848619541

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- GÉNÉRATEUR DE CAPTCHA VISUEL ---
def generate_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    img = Image.new('RGB', (200, 70), color=(35, 39, 42))
    draw = ImageDraw.Draw(img)

    for _ in range(6):
        x1, y1 = random.randint(0, 200), random.randint(0, 70)
        x2, y2 = random.randint(0, 200), random.randint(0, 70)
        draw.line([(x1, y1), (x2, y2)], fill=(114, 137, 218), width=2)

    draw.text((35, 25), code, fill=(255, 255, 255))

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return code, buffer

# --- FENÊTRE D'ENTRÉE DU CODE ---
class CaptchaModal(Modal):
    def __init__(self, correct_code):
        super().__init__(title="Vérification Captcha")
        self.correct_code = correct_code
        self.code_input = TextInput(
            label="Recopie le code de l'image :", 
            placeholder="EX: A1B2C", 
            max_length=5
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip().upper() == self.correct_code:
            role = interaction.guild.get_role(VERIFIED_ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("Accès validé ! Tu as reçu le rôle. 🎉", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur : Rôle introuvable sur le serveur.", ephemeral=True)
        else:
            await interaction.response.send_message("Code incorrect. Reclique sur le bouton pour réessayer.", ephemeral=True)

# --- VUES (BOUTONS) ---
class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="S'inscrire / Se vérifier", style=discord.ButtonStyle.green, custom_id="verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role and role in interaction.user.roles:
            await interaction.response.send_message("Tu es déjà vérifié !", ephemeral=True)
            return

        code, image_buffer = generate_captcha()
        file = discord.File(image_buffer, filename="captcha.png")
        
        await interaction.response.send_message("Regarde le code ci-dessous et entre-le dans la fenêtre :", file=file, ephemeral=True)
        await interaction.followup.send_modal(CaptchaModal(correct_code=code))

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Fermeture du ticket...")
        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=3))
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
            description=f"Bonjour {interaction.user.mention}, décris ton problème ici.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Ton ticket a été créé : {channel.mention}", ephemeral=True)

# --- ÉVÉNEMENTS & TÂCHES ---
@tasks.loop(minutes=10)
async def update_stats():
    for guild in bot.guilds:
        members_count = sum(1 for m in guild.members if not m.bot)
        bots_count = sum(1 for m in guild.members if m.bot)
        
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

# --- COMMANDES ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    embed = discord.Embed(
        title="Vérification",
        description="Clique sur le bouton ci-dessous pour démarrer la vérification.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=VerifyView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="Support",
        description="Clique ci-dessous pour ouvrir un ticket.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TicketView())

threading.Thread(target=run_web_server, daemon=True).start()

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
