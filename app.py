import discord
from discord.ext import commands
from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
import random
import os
from PIL import Image, ImageDraw, ImageFont
import io
import threading
import asyncio

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

bot = commands.Bot(command_prefix="!", intents=intents)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Função para gerar o CAPTCHA
def generate_captcha():
    captcha_text = str(random.randint(1000, 9999))
    img = Image.new('RGB', (100, 40), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    except IOError:
        font = ImageFont.load_default()
    
    d.text((10, 10), captcha_text, font=font, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)

    return captcha_text, buf

captcha_text = ""
captcha_image = None

# Formulário de login
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    captcha = StringField('Digite o código', validators=[DataRequired()])

# Rota de login
@app.route("/", methods=["GET", "POST"])
def login():
    global captcha_text, captcha_image
    form = LoginForm()

    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        captcha_response = form.captcha.data
        
        if captcha_response == captcha_text:
            if username == "admin" and password == "admin12112013jA":
                session["user_id"] = 1
                return redirect(url_for("admin_dashboard"))
            else:
                return "Credenciais inválidas", 403
        else:
            return "Captcha incorreto", 403

    captcha_text, captcha_image = generate_captcha()

    return render_template("login.html", form=form, captcha_image=captcha_image)

@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

# Comandos gerais do bot
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Comandos do Bot", color=0x7289da)
    embed.add_field(name="📌 Comandos Gerais", value="`!help`, `!ping`, `!avatar @usuário`", inline=False)
    embed.add_field(name="🎲 Diversão", value="`!dado`, `!moeda`, `!piada`", inline=False)
    embed.add_field(name="🎉 Sorteios", value="`!sorteio <nome> <dias>`, `!entrar_sorteio`, `!sortear`", inline=False)
    embed.add_field(name="⚒️ Moderação", value="`!ban @usuário`, `!kick @usuário`, `!warn @usuário <motivo>`, `!banpainel`", inline=False)
    await ctx.send(embed=embed)

# Função para rodar o Flask
def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Inicializa o bot e Flask
async def start_bot_and_flask():
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
        
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    await bot.start(DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(start_bot_and_flask())
