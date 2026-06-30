import discord
from discord.ext import commands, tasks

from config import CHANNEL_ID, SUMMARY_TIME
from data_fetcher import get_lte_data
from utils.formatter import build_alert_embed, build_all_clear_embed, build_embed


class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._was_alerted = False
        self.daily_summary.start()
        self.alert_check.start()

    def cog_unload(self):
        self.daily_summary.stop()
        self.alert_check.stop()

    async def _channel(self) -> discord.TextChannel | None:
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(CHANNEL_ID)
            except Exception:
                return None
        return channel

    @tasks.loop(time=SUMMARY_TIME)
    async def daily_summary(self):
        channel = await self._channel()
        if channel is None:
            return
        data = await get_lte_data()
        embed = build_embed(data)
        await channel.send(embed=embed)

    @daily_summary.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def alert_check(self):
        channel = await self._channel()
        if channel is None:
            return
        data = await get_lte_data()
        is_overloaded = data.used_percent >= 90

        if is_overloaded and not self._was_alerted:
            embed = build_alert_embed(data)
            await channel.send(embed=embed)
            self._was_alerted = True
        elif not is_overloaded and self._was_alerted:
            embed = build_all_clear_embed(data.used_percent, data.remaining_gb)
            await channel.send(embed=embed)
            self._was_alerted = False

    @alert_check.before_loop
    async def before_alert(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduler(bot))
