import discord
from discord.ext import commands, tasks
from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import threading
import os
import asyncio
import random
from datetime import datetime, timedelta

# Configurações do Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Configuração do bot Discord
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Variáveis do sorteio
giveaway_active = False
giveaway_name = ""
giveaway_end_time = None
giveaway_participants = []

# Função de login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin12112013jA":
            session["user_id"] = 1  # Define a sessão como logada
            return redirect(url_for("admin_dashboard"))

    return render_template("login.html")

@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html")

# Comandos gerais
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Comandos do Bot", color=0x7289da)
    embed.add_field(name="📌 Comandos Gerais", value="`!help`, `!ping`, `!avatar @usuário`", inline=False)
    embed.add_field(name="🎲 Diversão", value="`!dado`, `!moeda`, `!piada`", inline=False)
    embed.add_field(name="🎉 Sorteios", value="`!sorteio <nome> <dias>`, `!entrar_sorteio`, `!sortear`", inline=False)
    embed.add_field(name="⚒️ Moderação", value="`!ban @usuário`, `!kick @usuário`, `!atendimentopainel`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 Latência: {round(bot.latency * 1000)}ms")

@bot.command()
async def avatar(ctx, member: discord.Member):
    await ctx.send(f"Aqui está o avatar de {member.mention}: {member.avatar.url}")

# Comandos de diversão
@bot.command()
async def dado(ctx):
    numero = random.randint(1, 6)
    await ctx.send(f"🎲 Você rolou um **{numero}**!")

@bot.command()
async def moeda(ctx):
    resultado = random.choice(["🪙 Cara", "🪙 Coroa"])
    await ctx.send(f"O resultado foi: **{resultado}**!")

@bot.command()
async def piada(ctx):
    piadas = [
        "Por que o livro de matemática ficou triste? Porque tinha muitos problemas!",
        "O que uma impressora disse para a outra? Essa folha é sua ou é impressão minha?",
        "Por que o esqueleto não brigou? Porque ele não tinha estômago para isso!"
    ]
    await ctx.send(random.choice(piadas))

# Comandos de sorteio
@bot.command()
async def sorteio(ctx, nome: str, dias: int):
    global giveaway_active, giveaway_name, giveaway_end_time, giveaway_participants
    if giveaway_active:
        await ctx.send(f"Já há um sorteio ativo: {giveaway_name}")
        return
    
    giveaway_active = True
    giveaway_name = nome
    giveaway_end_time = datetime.utcnow() + timedelta(days=dias)
    giveaway_participants.clear()
    await ctx.send(f"🎉 Sorteio '{nome}' iniciado! Duração: {dias} dias.")

@bot.command()
async def entrar_sorteio(ctx):
    global giveaway_active, giveaway_participants
    if not giveaway_active:
        await ctx.send("Nenhum sorteio ativo no momento!")
        return

    if ctx.author not in giveaway_participants:
        giveaway_participants.append(ctx.author)
        await ctx.send(f"{ctx.author.mention} entrou no sorteio!")
    else:
        await ctx.send("Você já está participando do sorteio!")

@bot.command()
async def sortear(ctx):
    global giveaway_active, giveaway_name, giveaway_participants
    if not giveaway_active:
        await ctx.send("Nenhum sorteio ativo no momento!")
        return

    if len(giveaway_participants) == 0:
        await ctx.send("Nenhum participante no sorteio!")
        return

    winner = random.choice(giveaway_participants)
    await ctx.send(f"🎉 O vencedor do sorteio '{giveaway_name}' é {winner.mention}!")
    giveaway_active = False

# Comandos de moderação
@bot.command()
async def ban(ctx, member: discord.Member, *, reason="Sem motivo informado"):
    if ctx.author.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await ctx.send(f'🚨 {member} foi banido! Motivo: {reason}')
    else:
        await ctx.send("Você não tem permissão para banir membros!")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason="Sem motivo informado"):
    if ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f'👢 {member} foi expulso! Motivo: {reason}')
    else:
        await ctx.send("Você não tem permissão para expulsar membros!")

@bot.command()
async def atendimentopainel(ctx):
    embed = discord.Embed(title="🎫 Painel de Atendimento", description="Clique no botão abaixo para abrir um ticket!", color=0x00ff00)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('📩')

# Função para rodar o Flask
def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Inicializa o bot e Flask no asyncio
async def start_bot_and_flask():
    # Garantir que estamos no contexto da aplicação Flask
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
        
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(start_bot_and_flask())
