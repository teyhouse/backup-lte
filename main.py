import discord
from discord.ext import commands

from config import BOT_TOKEN, GUILD_ID

intents = discord.Intents.default()


class LteBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.lte_commands")
        await self.load_extension("cogs.scheduler")
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = LteBot(command_prefix="/", intents=intents)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
