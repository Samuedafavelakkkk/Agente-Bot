import discord
from discord.ext import commands, tasks
from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import threading
import subprocess
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import asyncio
import random
from datetime import datetime, timedelta

# Configurações iniciais
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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Desativa o comando help padrão
BOT_INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=1334637379734081608&permissions=8&scope=bot"
COMMUNITY_SERVER = "https://discord.gg/eZwKHyxHCV"

DISCORD_BOT_TOKEN = "MTMzNDYzNzM3OTczNDA4MTYwOA.G4QtNC.xXzq74lzPcys8DdsNr7dSeQXd-2SRvwxkStCdk"  # Coloque seu token aqui

# Variáveis para controle de shutdown
shutdown_in_progress = False
shutdown_reason = ""
shutdown_mention = False

# Variáveis de sorteio
giveaway_active = False
giveaway_name = ""
giveaway_end_time = None
giveaway_channel = None
giveaway_recompensa = ""
giveaway_dm = False
giveaway_participants = []

# Decorator para login requerido
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Comandos do Bot
@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await ctx.send(f'{member} foi banido!')
    else:
        await ctx.send("Você não tem permissão para banir membros!")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    if ctx.author.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await ctx.send(f'{member} foi kickado!')
    else:
        await ctx.send("Você não tem permissão para kickar membros!")

@bot.command()
async def ticket(ctx, titulo: str, botao: str):
    embed = discord.Embed(title=titulo, color=0x00ff00)
    embed.add_field(name="Clique no botão abaixo para abrir um ticket", value="\u200b")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('📩')

@bot.command()
async def ajuda(ctx):
    embed = discord.Embed(title="Comandos do Bot", color=0x7289da)
    embed.add_field(name="!ban @usuário", value="Bane um membro", inline=False)
    embed.add_field(name="!kick @usuário", value="Expulsa um membro", inline=False)
    embed.add_field(name="!ticket [título] [botão]", value="Cria painel de tickets", inline=False)
    embed.add_field(name="!botinvite", value="Mostra o link de convite do bot", inline=False)
    embed.add_field(name="!botserver", value="Mostra o servidor da comunidade", inline=False)
    embed.add_field(name="!sorteio [nome] [dias]", value="Cria um sorteio", inline=False)
    embed.add_field(name="!setsorteioglobal [canal]", value="Define o canal de sorteio", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def botinvite(ctx):
    await ctx.send(f"Convite do bot: {BOT_INVITE_URL}")

@bot.command()
async def botserver(ctx):
    await ctx.send(f"Entre em nosso servidor: {COMMUNITY_SERVER}  Status do bot: [Cique aqui!](http://192.168.0.197:5000)")

# Comando para iniciar sorteio
@bot.command()
async def sorteio(ctx, nome: str, dias: int):
    global giveaway_active, giveaway_name, giveaway_end_time, giveaway_participants  # Declarar variáveis globais
    if giveaway_active:
        await ctx.send(f"Já há um sorteio ativo: {giveaway_name}")
        return
    
    giveaway_active = True
    giveaway_name = nome
    giveaway_end_time = datetime.utcnow() + timedelta(days=dias)
    giveaway_participants.clear()  # Limpa participantes anteriores
    await ctx.send(f"Sorteio '{nome}' iniciado! O sorteio vai durar {dias} dias até {giveaway_end_time.strftime('%Y-%m-%d %H:%M:%S')}.")

# Comando para definir o canal de sorteio
@bot.command()
async def setsorteioglobal(ctx, canal: discord.TextChannel):
    global giveaway_channel  # Declarar giveaway_channel como global aqui
    giveaway_channel = canal
    await ctx.send(f"Canal de sorteio definido para {canal.mention}.")

# Comando para os participantes entrarem no sorteio
@bot.command()
async def participar(ctx):
    global giveaway_active, giveaway_name, giveaway_end_time, giveaway_participants  # Declarar variáveis globais
    if not giveaway_active:
        await ctx.send("Nenhum sorteio ativo no momento!")
        return

    if datetime.utcnow() > giveaway_end_time:
        await ctx.send(f"O sorteio '{giveaway_name}' já terminou!")
        giveaway_active = False
        return

    if ctx.author not in giveaway_participants:
        giveaway_participants.append(ctx.author)
        await ctx.send(f"{ctx.author.mention} entrou no sorteio '{giveaway_name}'!")
    else:
        await ctx.send(f"{ctx.author.mention}, você já está participando do sorteio!")

# Função para escolher o vencedor do sorteio
async def pick_winner():
    global giveaway_active, giveaway_name, giveaway_end_time, giveaway_participants, giveaway_channel, giveaway_recompensa, giveaway_dm  # Declarar todas as variáveis globais
    if giveaway_active and datetime.utcnow() > giveaway_end_time:
        winner = random.choice(giveaway_participants)
        await giveaway_channel.send(f"O vencedor do sorteio '{giveaway_name}' é: {winner.mention}!")

        # Envia DM ao ganhador, se for configurado
        if giveaway_dm:
            await winner.send(f"Parabéns, você ganhou o sorteio '{giveaway_name}'! Sua recompensa: {giveaway_recompensa}")
        
        # Resetar sorteio
        giveaway_active = False
        giveaway_name = ""
        giveaway_end_time = None
        giveaway_participants.clear()

# Função para agendar a verificação do sorteio
@tasks.loop(seconds=60)
async def check_giveaway():
    await pick_winner()

check_giveaway.start()

# Rota para o comando de ajuda no painel de administração
@app.route('/execute_command', methods=['POST'])
@login_required
def execute_command():
    data = request.get_json()
    command = data.get('command')

    if not command:
        return jsonify({'output': 'Nenhum comando fornecido.'})

    # Comando ajuda-prompt
    if command == "ajuda-prompt":
        help_message = """
        Comandos disponíveis no painel de administração:
        - shutdown-bot <tempo> <motivo> <mention> : Desliga o bot com o motivo e tempo. Exemplo: 10minutos 'Manutenção' true
        - prompt-help : Mostra essa mensagem
        - serverban <invite> <motivo> <permanente> : Banir um servidor com motivo e duração (se temporário)
        - central-logs : Mostra os logs da central onde o bot foi executado
        - sorteio-global <nome> <recompensa> <ir_na_DM> : Define um sorteio global
        """
        return jsonify({'output': help_message})

    # Comando para iniciar sorteio global
    if command.startswith("sorteio-global"):
        try:
            args = command.split(" ")
            nome = args[1]
            recompensa = args[2]
            ir_na_dm = args[3].lower() == "true" if len(args) > 3 else False
            global giveaway_recompensa, giveaway_dm
            giveaway_recompensa = recompensa
            giveaway_dm = ir_na_dm
            return jsonify({'output': f"Sorteio global '{nome}' configurado com recompensa: {recompensa}, DM para ganhador: {ir_na_dm}"})
        except Exception as e:
            return jsonify({'output': f"Erro ao processar sorteio global: {str(e)}"})

    # Comando shutdown-bot
    if command.startswith("shutdown-bot"):
        try:
            args = command.split(" ")
            tempo = args[1]
            motivo = args[2]
            mention = args[3].lower() == "true"
            global shutdown_in_progress, shutdown_reason, shutdown_mention
            shutdown_in_progress = True
            shutdown_reason = motivo
            shutdown_mention = mention
            return jsonify({'output': f"Bot será desligado em {tempo} por motivo: {motivo}. Mencionar: {mention}"})
        except Exception as e:
            return jsonify({'output': f"Erro ao processar shutdown: {str(e)}"})

    # Executa o comando no terminal
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        output = str(e)

    return jsonify({'output': output})

# Rotas Web
@app.route('/')
def index():
    bot_status = "Online" if bot.is_ready() else "Offline"
    return render_template('index.html', bot_status=bot_status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password) and user.is_admin:
            session['user_id'] = user.id
            return redirect(url_for('admin_panel'))
        return "Credenciais inválidas!"
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_panel():
    bot_status = "Online" if bot.is_ready() else "Offline"
    return render_template('admin.html', bot_status=bot_status)

# Inicialização
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def run_bot():
    asyncio.run(bot.start(DISCORD_BOT_TOKEN))

if __name__ == '__main__':
    init_db()
    
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_bot)
    
    flask_thread.start()
    bot_thread.start()
    
    flask_thread.join()
    bot_thread.join()
