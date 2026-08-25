import discord
from discord import app_commands
from discord.ext import commands

from config import OWNER_ID
from data_fetcher import get_lte_data
from utils.formatter import build_embed
from utils.logger import get_logger

logger = get_logger("lte_commands")


class LteCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lte", description="Show current LTE data usage")
    async def lte_data(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != OWNER_ID:
            await interaction.followup.send(
                "❌ You are not authorized to use this command.",
                ephemeral=True,
            )
            return

        try:
            data = await get_lte_data()
        except Exception:
            logger.exception("Failed to fetch data for /lte")
            await interaction.followup.send(
                "Could not fetch data. Try again later.",
                ephemeral=True,
            )
            return

        embed = build_embed(data)
        await interaction.followup.send(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(LteCommands(bot))
