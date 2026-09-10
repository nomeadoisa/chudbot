import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = 1547619122056007720 

class ChudBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.load_extension('cogs.commands')
        await self.load_extension('cogs.mining')

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.tree.sync()
        channel = self.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send("Chudbot is online. Hello.")

    async def close(self):
        channel = self.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send("Chudbot is going away for a while. I hope I see you again.")

        mining_cog = self.get_cog('MiningCommands')
        if mining_cog:
            await mining_cog.cancel_active_mines()

        await super().close()

bot = ChudBot()
bot.run(TOKEN)