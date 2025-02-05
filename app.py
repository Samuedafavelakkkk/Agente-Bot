import discord
from discord.ext import commands
from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
import os
import threading
import asyncio
import subprocess
from dotenv import load_dotenv

# Carregar variáveis do ambiente
load_dotenv()

# Configuração do Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Configuração do bot Discord
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Variáveis globais para controlar o status do bot
bot_status = "Desconhecido"  # Inicialmente, desconhecido, já que o bot ainda não foi iniciado
error_log = []  # Lista para armazenar logs de erros

# 📌 **Comandos do Bot**
@bot.command()
async def avatar(ctx, user: discord.User = None):
    user = user or ctx.author
    await ctx.send(user.avatar_url)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member} foi banido(a). Motivo: {reason}")

@bot.command()
async def dado(ctx):
    import random
    await ctx.send(f"🎲 Você rolou o número {random.randint(1, 6)}!")

@bot.command()
async def entrar_sorteio(ctx):
    # Este comando pode entrar em um sorteio, como a lógica já foi configurada
    await ctx.send("Você entrou no sorteio!")

@bot.command()
async def ajuda(ctx):
    comandos_info = """
    📜 **Lista de Comandos:**
    🔹 `!ping` → Mostra a latência do bot.
    🔹 `!avatar @usuário` → Mostra o avatar do usuário.
    🔹 `!dado` → Rola um dado de 6 lados.
    🔹 `!moeda` → Cara ou coroa.
    🔹 `!piada` → Conta uma piada.
    🔹 `!sorteio <nome> <dias>` → Cria um sorteio.
    🔹 `!entrar_sorteio` → Entra em um sorteio.
    🔹 `!sortear` → Sorteia um vencedor.
    🔹 `!ban @usuário` → Bane um usuário.
    🔹 `!kick @usuário` → Expulsa um usuário.
    🔹 `!mute @usuário <tempo>` → Silencia um usuário.
    🔹 `!warn @usuário <motivo>` → Dá um aviso a um usuário.
    🔹 `!setup` → Configura o servidor e o canal de suporte.
    🔹 `!botinvite` → Envia o convite do bot.
    """
    await ctx.send(comandos_info)

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} foi expulso(a). Motivo: {reason}")

@bot.command()
async def moeda(ctx):
    import random
    resultado = random.choice(["Cara", "Coroa"])
    await ctx.send(f"🪙 Resultado: {resultado}")

@bot.command()
async def parceriacancelar(ctx, motivo, link_do_servidor):
    # Comando para cancelar uma parceria (lógica a ser ajustada conforme a necessidade)
    await ctx.send(f"Parceria com {link_do_servidor} cancelada. Motivo: {motivo}")

@bot.command()
async def piada(ctx):
    import random
    piadas = [
        "Por que o livro de matemática se suicidou? Porque estava cheio de problemas!",
        "Qual é o cúmulo da rapidez? Correr atrás do prejuízo!",
        "O que é um vegetariano que come carne? Um ex-vegetariano.",
    ]
    await ctx.send(random.choice(piadas))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latência: {round(bot.latency * 1000)}ms")

@bot.command()
async def setparceiros(ctx, link_do_servidor, criador_do_servidor, mensagem_de_divulgacao, midia_opcional=None):
    # Comando para definir um parceiro (lógica a ser ajustada conforme a necessidade)
    await ctx.send(f"Parceiro definido: {link_do_servidor} | Criador: {criador_do_servidor} | Mensagem: {mensagem_de_divulgacao}")

@bot.command()
async def setup(ctx):
    guild = ctx.guild
    cargo_inicial = discord.utils.get(guild.roles, name="Membro")

    if not cargo_inicial:
        cargo_inicial = await guild.create_role(name="Membro")

    await ctx.send(f"Cargo inicial `{cargo_inicial.name}` definido para novos membros.")

    categoria = discord.utils.get(guild.categories, name="Suporte")
    if not categoria:
        categoria = await guild.create_category("Suporte")

    canal_suporte = await guild.create_text_channel("📩-suporte", category=categoria)
    await canal_suporte.set_permissions(guild.default_role, send_messages=False)

    await ctx.send(f"Canal de suporte `{canal_suporte.name}` criado.")

@bot.command()
async def sortear(ctx):
    # Comando de sorteio
    await ctx.send("Sorteio realizado! O vencedor é...")

@bot.command()
async def sorteio(ctx, nome, dias):
    # Comando para iniciar um sorteio
    await ctx.send(f"Sorteio '{nome}' criado para {dias} dias!")


# 📌 **Rodando Flask e Bot**
def run_flask():
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, use_reloader=False)

async def start_bot_and_flask():
    global bot_status
    bot_status = "Ativado"  # Atualiza o status quando o bot é iniciado
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    try:
        await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        bot_status = "Desativado"
        error_log.append(f"Erro ao iniciar o bot: {str(e)}")  # Armazena o erro no log
        raise e

# 📌 **Rotas do Flask**
@app.route("/")
def index():
    global bot_status
    return render_template("index.html", bot_status=bot_status, error_log=error_log)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session["user_id"] = user.id
            return redirect(url_for("admin_dashboard"))
        else:
            error_log.append(f"Tentativa de login falhou para o usuário '{username}'")
            return render_template("login.html", erro="Login inválido. Tente novamente.")

    return render_template("login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html", resposta="")

@app.route("/executar_comando", methods=["POST"])
def executar_comando():
    if "user_id" not in session:
        return redirect(url_for("login"))

    comando = request.form["comando"]
    comandos_permitidos = ["ls", "cat", "echo", "pwd"]

    if comando.split()[0] not in comandos_permitidos:
        return "Comando não permitido!"

    try:
        resultado = subprocess.check_output(comando, shell=True, stderr=subprocess.STDOUT)
        resposta = resultado.decode("utf-8")
    except subprocess.CalledProcessError as e:
        resposta = f"Erro ao executar o comando: {e.output.decode('utf-8')}"
        error_log.append(f"Erro ao executar o comando '{comando}': {resposta}")

    return render_template("admin_dashboard.html", resposta=resposta)

if __name__ == "__main__":
    asyncio.run(start_bot_and_flask())
