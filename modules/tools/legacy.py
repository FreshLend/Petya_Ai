import discord

@bot.tree.command(name="connect", description="Подключить бота к голосовому каналу")
async def connect(interaction: discord.Interaction, disconnect: bool = False):
    await interaction.response.defer()
    if disconnect:
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send("Отключился от голосового канала!")
        else:
            await interaction.followup.send("Бот не подключен к голосовому каналу!")
    else:
        if interaction.user.voice:
            await interaction.user.voice.channel.connect(timeout=60.0)
            await interaction.followup.send("Подключился к голосовому каналу!")
        else:
            await interaction.followup.send("Вы не находитесь в голосовом канале!")