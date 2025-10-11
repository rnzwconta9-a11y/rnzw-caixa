import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import sys

# Add the parent directory of 'bot' to sys.path for proper module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from bot.utils import db

# Carrega as variáveis de ambiente do arquivo .env no diretório raiz do projeto
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, ".env"))

async def setup_database_and_prizes():
    print("DEBUG: Iniciando setup_database_and_prizes...")
    # db.init_db() is now called in main() before bot.start()
    print("DEBUG: Database initialized.")

    prizes = await db.get_all_prizes()
    if not prizes:
        print("DEBUG: Nenhum prêmio encontrado, adicionando prêmios iniciais.")
        mystery_box = await db.get_mystery_box_by_name("Caixa Padrão")
        if not mystery_box:
            print("DEBUG: Caixa Padrão não encontrada, criando...")
            box_id = await db.add_mystery_box("Caixa Padrão", "Uma caixa misteriosa padrão.", 10.0)
            print(f"DEBUG: Caixa Padrão criada com ID: {box_id}")
        else:
            box_id = mystery_box[0]
            print(f"DEBUG: Caixa Padrão existente com ID: {box_id}")

        prizes_to_add = [
            (box_id, "Perdeu", "Comum"),
            (box_id, "Painel iOS 1 hora", "Raro"),
            (box_id, "Holograma Android", "Épico"),
            (box_id, "Auxílio iOS", "Incomum"),
            (box_id, "Auxílio Android", "Incomum"),
            (box_id, "Gire novamente", "Raro"),
            (box_id, "Painel iOS 1 dia", "Lendário"),
            (box_id, "Seja revendedor", "Mítico"),
            (box_id, "Vaga", "Mítico")
        ]
        for box_id, name, rarity in prizes_to_add:
            await db.add_prize(box_id, name, rarity)
        print("DEBUG: Prêmios iniciais adicionados ao banco de dados.")
    else:
        print("DEBUG: Prêmios já existem no banco de dados.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Needed for getting user info
intents.presences = True # Needed for presence updates about presence updates to resolve PrivilegedIntentsRequired for Presence Intent

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    print(f"DEBUG: Message from {message.author}: {message.content}")
    try:
        await bot.process_commands(message)

    except Exception as e:
        print(f"DEBUG: Erro ao processar comando: {e}")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await setup_database_and_prizes()

@bot.event
async def on_command_error(ctx, error):
    print(f"DEBUG: Erro no comando {ctx.command}: {error}")
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Comando não encontrado. Digite `!help` para ver os comandos disponíveis.")
    else:
        await ctx.send(f"Ocorreu um erro: {error}")

@bot.command()
async def hello(ctx):
    await ctx.send("Olá!")

@bot.command(name="testdb")
async def test_db(ctx):
    user = await db.get_user_by_discord_id(str(ctx.author.id))
    if user:
        await ctx.send(f"Usuário {user[2]} (ID: {user[1]}) encontrado no DB.")
    else:
        await db.add_user(str(ctx.author.id), ctx.author.name)
        await ctx.send(f"Usuário {ctx.author.name} adicionado ao DB.")

from bot.cogs.mystery_box import MysteryBox

async def load_extensions():
    print("DEBUG: Adicionando cog MysteryBox diretamente.")
    await bot.add_cog(MysteryBox(bot))







async def main():
    async with bot:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("Erro: O token do Discord não foi encontrado. Verifique o arquivo .env.")
            return
        await db.init_db() # Ensure DB is initialized before starting the bot and loading cogs
        await load_extensions()
        await bot.start(token)



if __name__ == "__main__":
    asyncio.run(main())

