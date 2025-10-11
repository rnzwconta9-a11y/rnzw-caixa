import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
from bot.utils import db

import uuid
MYSTERY_BOX_IMAGE_URL = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2x2aG93dG52eGZ1ZzJ0eW92Y290Ym53d254bW93Y3R5eG96Y252eCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l0MYzYgJ0w2XyqGys/giphy.gif"

class MysteryBoxView(View):
    def __init__(self, chosen_prize, ctx, user_id, username):
        super().__init__(timeout=300)
        self.chosen_prize = chosen_prize
        self.ctx = ctx
        self.user_id = user_id
        self.username = username

    @discord.ui.button(label="Girar", style=discord.ButtonStyle.green)
    async def spin_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("Esta caixa é para outra pessoa!", ephemeral=True)
            return

        button.disabled = True
        await interaction.response.edit_message(view=self)

        # Simulate roulette animation
        messages = [
            "A caixa está girando...",
            "Quase lá...",
            "E o prêmio é..."
        ]
        for msg in messages:
            embed = discord.Embed(
                title="Caixa Misteriosa",
                description=msg,
                color=discord.Color.gold()
            )
            embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed)
            await asyncio.sleep(1.0) # 1 segundo por mensagem para um total de 3 segundos de animação

        # Reveal the prize
        final_embed = discord.Embed(
            title="Parabéns!",
            description=f"{self.ctx.author.mention}! Você abriu a caixa e ganhou: **{self.chosen_prize[2]}** ({self.chosen_prize[4]})!",
            color=discord.Color.green()
        )
        final_embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        await interaction.followup.edit_message(message_id=interaction.message.id, embed=final_embed, view=None)


class PublicMysteryBoxView(View):
    def __init__(self, bot, channel_id):
        super().__init__(timeout=None) # Persistent view
        self.bot = bot
        self.channel_id = channel_id
        self.add_item(discord.ui.Button(label="COMPRAR KEY", style=discord.ButtonStyle.link, url="https://discord.gg/kgxxb9S59k")) # Replace with actual Discord invite link

    @discord.ui.button(label="TESTE", style=discord.ButtonStyle.blurple, custom_id="test_button")
    async def test_button(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        username = interaction.user.name

        # Ensure user exists in DB
        user = await db.get_user_by_discord_id(user_id)
        if not user:
            await db.add_user(user_id, username)
            user = await db.get_user_by_discord_id(user_id) # Re-fetch user after adding

        if await db.has_used_test_key(user_id):
            await interaction.response.send_message("Você já usou seu teste grátis!", ephemeral=True)
            return

        await db.record_test_key_usage(user_id)

        mystery_box = await db.get_mystery_box_by_name("Caixa Padrão")
        if not mystery_box:
            await interaction.response.send_message("Nenhuma caixa misteriosa disponível no momento.", ephemeral=True)
            return
        box_id = mystery_box[0]

        # Get or create the 100.00 prize
        test_prize = await db.get_or_create_prize(box_id, "100.00 de Crédito", "Comum", 100.00)

        # Initial response to the button click
        await interaction.response.send_message("Iniciando seu teste grátis!", ephemeral=True)

        # Create initial embed for the mystery box reveal
        embed = discord.Embed(
            title="Caixa Misteriosa - Teste",
            description="A caixa está girando...",
            color=discord.Color.blue()
        )
        embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        embed.set_footer(text="Boa sorte!")

        # Send the initial message to the channel where the button was clicked
        message = await interaction.channel.send(embed=embed)

        # Simulate roulette animation
        messages = [
            "A caixa está girando...",
            "Quase lá...",
            "E o prêmio é..."
        ]
        for msg_text in messages:
            embed.description = msg_text
            await message.edit(embed=embed)
            await asyncio.sleep(1.0) # 1 segundo por mensagem para um total de 3 segundos de animação

        # Reveal the prize
        final_embed = discord.Embed(
            title="Parabéns!",
            description=f"{interaction.user.mention}! Você abriu a caixa de teste e ganhou: **{test_prize[2]}**!",
            color=discord.Color.green()
        )
        final_embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        await message.edit(embed=final_embed, view=None)

        # Record the prize won
        await db.record_prize_won(user[0], test_prize[0], "TEST_KEY")

    @discord.ui.button(label="GIRAR", style=discord.ButtonStyle.green, custom_id="spin_button_public")
    async def spin_button_public(self, interaction: discord.Interaction, button: Button):
        # This button will trigger a modal for key input, or directly open if no key is needed.
        # For now, let's assume it will open a modal for key input.
        await interaction.response.send_modal(KeyInputModal())



class MysteryBox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="openbox")
    async def open_mystery_box(self, ctx, key_code: str = None):
        print(f"Comando !openbox recebido de {ctx.author.name} ({ctx.author.id})")
        user_id = str(ctx.author.id)
        username = ctx.author.name

        # Ensure user exists in DB
        user = await db.get_user_by_discord_id(user_id)
        if not user:
            await db.add_user(user_id, username)

        # For now, let's assume there's only one mystery box (Caixa Padrão) with ID 1
        # In a more complex system, users might specify which box to open
        mystery_box = await db.get_mystery_box_by_name("Caixa Padrão")
        print(f"Verificando caixa misteriosa: {mystery_box}")
        if not mystery_box:
            await ctx.send("Nenhuma caixa misteriosa disponível no momento.")
            print("DEBUG: Erro: Nenhuma caixa misteriosa disponível.")
            return
        box_id = mystery_box[0]
        print(f"DEBUG: ID da caixa misteriosa: {box_id}")

        prizes = await db.get_prizes_by_box_id(box_id)
        print(f"DEBUG: Prêmios recuperados para a caixa {box_id}: {prizes}")
        if not prizes:
            await ctx.send("Esta caixa misteriosa não tem prêmios configurados.")
            print("DEBUG: Erro: Caixa misteriosa sem prêmios configurados.")
            return

        if key_code:
            key = await db.get_key_by_code(key_code)
            if not key or key[4] == 1: # key[4] is 'used' status
                await ctx.send("Chave inválida ou já utilizada.")
                print(f"DEBUG: Chave inválida ou utilizada: {key_code}")
                return
            if key[2] != box_id: # key[2] is box_id
                await ctx.send("Esta chave não é para esta caixa misteriosa.")
                print(f"DEBUG: Chave {key_code} não corresponde à caixa {box_id}.")
                return
            
            await db.use_key(key_code, user[0]) # user[0] is user id
            print(f"DEBUG: Chave {key_code} utilizada por {username}.")
        else:
            if not key_code:
                await ctx.send("Você precisa de uma chave para abrir a caixa misteriosa. Use `!openbox <sua_chave>`.")
                print("DEBUG: Nenhuma chave fornecida.")
                return

        # Create initial embed for the mystery box
        embed = discord.Embed(
            title="Caixa Misteriosa",
            description="Uma caixa misteriosa aguarda para ser aberta!",
            color=discord.Color.blue()
        )
        embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        embed.set_footer(text="Use a chave para revelar seu prêmio!")
        await ctx.send(embed=embed)

        # Now proceed with the prize logic


        print(f"DEBUG: Prêmios disponíveis para sorteio: {len(prizes)}")
        # Prize distribution logic based on preferences
        # Order of chances: perder, painel iOS 1 hora, holograma Android, auxílio iOS, auxílio Android, gire novamente, painel iOS 1 dia, seja revendedor, vaga.
        # Assign probabilities (these are example values and should be refined)
        prize_weights = {
            "Perdeu": 0.40,
            "Painel iOS 1 hora": 0.20,
            "Holograma Android": 0.10,
            "Auxílio iOS": 0.08,
            "Auxílio Android": 0.07,
            "Gire novamente": 0.05,
            "Painel iOS 1 dia": 0.04,
            "Seja revendedor": 0.03,
            "Vaga": 0.03
        }

        available_prizes = []
        weights = []
        for prize in prizes:
            prize_name = prize[2] # prize[2] is the name of the prize
            if prize_name in prize_weights:
                available_prizes.append(prize)
                weights.append(prize_weights[prize_name])
        print(f"DEBUG: Prêmios elegíveis para sorteio: {len(available_prizes)}")

        if not available_prizes:
            await ctx.send("Não há prêmios válidos para sortear nesta caixa.")
            print("DEBUG: Erro: Não há prêmios válidos para sortear.")
            return

        # Normalize weights if they don\'t sum to 1
        total_weight = sum(weights)
        print(f"DEBUG: Pesos dos prêmios: {weights}, Soma total: {total_weight}")
        if total_weight != 1.0:
            normalized_weights = [w / total_weight for w in weights]
            print(f"DEBUG: Pesos normalizados: {normalized_weights}")
        else:
            normalized_weights = weights

        chosen_prize = random.choices(available_prizes, weights=normalized_weights, k=1)[0]
        print(f"DEBUG: Prêmio escolhido: {chosen_prize[2]}")

        # Create initial embed with spin button
        embed = discord.Embed(
            title="Caixa Misteriosa",
            description="Clique em 'Girar' para revelar seu prêmio!",
            color=discord.Color.blue()
        )
        embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        embed.set_footer(text="Boa sorte!")

        view = MysteryBoxView(chosen_prize, ctx, user_id, username)
        await ctx.send(embed=embed, view=view)
        print("DEBUG: Embed inicial com botão 'Girar' enviado.")





    @commands.command(name="generatekey")
    @commands.has_permissions(administrator=True)
    async def generate_key(self, ctx, box_name: str, quantity: int):
        if quantity <= 0:
            await ctx.send("A quantidade de chaves deve ser maior que zero.")
            return

        mystery_box = await db.get_mystery_box_by_name(box_name)
        if not mystery_box:
            await ctx.send(f"Caixa misteriosa ‘{box_name}’ não encontrada.")
            return
        box_id = mystery_box[0]

        generated_keys = []
        for _ in range(quantity):
            key_code = str(uuid.uuid4()).upper()
            await db.add_key(key_code, box_id)
            generated_keys.append(key_code)
        
        keys_str = "\n".join(generated_keys)
        await ctx.send(f"Foram geradas {quantity} chaves para a caixa ‘{box_name}’:\n```\n{keys_str}\n```")

    @commands.command(name="setboxchannel")
    @commands.has_permissions(administrator=True)
    async def set_box_channel(self, ctx, channel: discord.TextChannel):
        await db.set_config("mystery_box_channel_id", str(channel.id))
        await ctx.send(f"Canal da caixa misteriosa definido para {channel.mention}.")

    @commands.command(name="displaybox")
    @commands.has_permissions(administrator=True)
    async def display_box(self, ctx):
        channel_id = await db.get_config("mystery_box_channel_id")
        if not channel_id:
            await ctx.send("Por favor, defina o canal da caixa misteriosa primeiro usando `!setboxchannel #canal`.")
            return

        target_channel = self.bot.get_channel(int(channel_id))
        if not target_channel:
            await ctx.send("Não consegui encontrar o canal configurado. Por favor, verifique a configuração.")
            return

        embed = discord.Embed(
            title="Caixa Misteriosa Oficial",
            description="Desvende os mistérios e ganhe prêmios incríveis!",
            color=discord.Color.purple()
        )
        embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        embed.add_field(name="Como Jogar", value="Use uma chave para girar a caixa e revelar seu prêmio. Chaves podem ser compradas ou obtidas em eventos.", inline=False)
        embed.set_footer(text="Clique em \'Girar\' ou \'Teste\' abaixo!")

        view = PublicMysteryBoxView(self.bot, target_channel.id)
        message = await target_channel.send(embed=embed, view=view)
        await db.set_config("mystery_box_message_id", str(message.id))
        await ctx.send(f"Caixa misteriosa exibida em {target_channel.mention}.")

async def setup(bot):
    print("MysteryBox cog setup function called.")

    await bot.add_cog(MysteryBox(bot))

    # Add persistent view if the message exists
    channel_id = await db.get_config("mystery_box_channel_id")
    message_id = await db.get_config("mystery_box_message_id")
    if channel_id and message_id:
        bot.add_view(PublicMysteryBoxView(bot, int(channel_id)))




class KeyInputModal(Modal, title="Inserir Chave"): 
    key_code_input = TextInput(label="Código da Chave", placeholder="Digite sua chave aqui...", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        key_code = self.key_code_input.value.strip()
        user_id = str(interaction.user.id)
        username = interaction.user.name

        # Ensure user exists in DB
        user = await db.get_user_by_discord_id(user_id)
        if not user:
            await db.add_user(user_id, username)
            user = await db.get_user_by_discord_id(user_id) # Re-fetch user after adding

        mystery_box = await db.get_mystery_box_by_name("Caixa Padrão")
        if not mystery_box:
            await interaction.response.send_message("Nenhuma caixa misteriosa disponível no momento.", ephemeral=True)
            return
        box_id = mystery_box[0]

        key = await db.get_key_by_code(key_code)
        if not key or key[4] == 1: # key[4] is 'used' status
            await interaction.response.send_message("Chave inválida ou já utilizada.", ephemeral=True)
            return
        if key[2] != box_id: # key[2] is box_id
            await interaction.response.send_message("Esta chave não é para esta caixa misteriosa.", ephemeral=True)
            return
        
        await db.use_key(key_code, user[0]) # user[0] is user id

        prizes = await db.get_prizes_by_box_id(box_id)
        if not prizes:
            await interaction.response.send_message("Esta caixa misteriosa não tem prêmios configurados.", ephemeral=True)
            return

        prize_weights = {
            "Perdeu": 0.40,
            "Painel iOS 1 hora": 0.20,
            "Holograma Android": 0.10,
            "Auxílio iOS": 0.08,
            "Auxílio Android": 0.07,
            "Gire novamente": 0.05,
            "Painel iOS 1 dia": 0.04,
            "Seja revendedor": 0.03,
            "Vaga": 0.03
        }

        available_prizes = []
        weights = []
        for prize in prizes:
            prize_name = prize[2]
            if prize_name in prize_weights:
                available_prizes.append(prize)
                weights.append(prize_weights[prize_name])

        if not available_prizes:
            await interaction.response.send_message("Não há prêmios válidos para sortear nesta caixa.", ephemeral=True)
            return

        total_weight = sum(weights)
        if total_weight != 1.0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = weights

        chosen_prize = random.choices(available_prizes, weights=normalized_weights, k=1)[0]

        # Initial response to the modal submission
        await interaction.response.send_message("Sua chave foi validada! Preparando para girar...", ephemeral=True)

        # Create initial embed for the mystery box reveal
        embed = discord.Embed(
            title="Caixa Misteriosa",
            description="A caixa está girando...",
            color=discord.Color.blue()
        )
        embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        embed.set_footer(text="Boa sorte!")

        # Send the initial message to the channel where the button was clicked
        message = await interaction.channel.send(embed=embed)

        # Simulate roulette animation
        messages = [
            "A caixa está girando...",
            "Quase lá...",
            "E o prêmio é..."
        ]
        for msg_text in messages:
            embed.description = msg_text
            await message.edit(embed=embed)
            await asyncio.sleep(1.0) # 1 segundo por mensagem para um total de 3 segundos de animação

        # Reveal the prize
        final_embed = discord.Embed(
            title="Parabéns!",
            description=f"{interaction.user.mention}! Você abriu a caixa e ganhou: **{chosen_prize[2]}** ({chosen_prize[3]})!",
            color=discord.Color.green()
        )
        final_embed.set_image(url=MYSTERY_BOX_IMAGE_URL)
        await message.edit(embed=final_embed, view=None)

        # Record the prize won
        await db.record_prize_won(user[0], chosen_prize[0], key_code)






    @commands.command(name="generatekeydiscord")
    @commands.has_permissions(administrator=True)
    async def generate_key_discord(self, ctx, box_name: str, quantity: int):
        if quantity <= 0:
            await ctx.send("A quantidade de chaves deve ser maior que zero.")
            return

        mystery_box = await db.get_mystery_box_by_name(box_name)
        if not mystery_box:
            await ctx.send(f"Caixa misteriosa ‘{box_name}’ não encontrada.")
            return
        box_id = mystery_box[0]

        generated_keys = []
        for _ in range(quantity):
            key_code = str(uuid.uuid4()).upper()
            await db.add_key(key_code, box_id)
            generated_keys.append(key_code)
        
        keys_str = "\n".join(generated_keys)
        await ctx.send(f"Foram geradas {quantity} chaves para a caixa ‘{box_name}’:\n```\n{keys_str}\n```")

