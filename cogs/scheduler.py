import discord
from discord.ext import commands, tasks

from config import ALERT_THRESHOLD, CHANNEL_ID, SUMMARY_TIME
from data_fetcher import LteData, get_lte_data
from utils.formatter import build_alert_embed, build_all_clear_embed, build_embed
from utils.logger import get_logger

logger = get_logger("scheduler")


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

    async def _try_fetch(self) -> LteData | None:
        try:
            return await get_lte_data()
        except Exception:
            logger.exception("Failed to fetch LTE data")
            return None

    @tasks.loop(time=SUMMARY_TIME)
    async def daily_summary(self):
        try:
            channel = await self._channel()
            if channel is None:
                logger.warning("Daily summary: channel not found")
                return
            data = await self._try_fetch()
            if data is None:
                return
            embed = build_embed(data)
            await channel.send(embed=embed)
            logger.info("Daily summary posted")
        except Exception:
            logger.exception("Daily summary failed")

    @daily_summary.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def alert_check(self):
        try:
            channel = await self._channel()
            if channel is None:
                return
            data = await self._try_fetch()
            if data is None:
                return
            is_overloaded = data.used_percent >= ALERT_THRESHOLD

            if is_overloaded and not self._was_alerted:
                embed = build_alert_embed(data)
                await channel.send(embed=embed)
                self._was_alerted = True
                logger.info("Alert triggered at %.0f%%", data.used_percent)
            elif not is_overloaded and self._was_alerted:
                embed = build_all_clear_embed(data.used_percent, data.remaining_bytes)
                await channel.send(embed=embed)
                self._was_alerted = False
                logger.info("All-clear sent")
        except Exception:
            logger.exception("Alert check failed")

    @alert_check.before_loop
    async def before_alert(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Scheduler(bot))
