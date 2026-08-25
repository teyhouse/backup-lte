import time

import aiohttp
import discord
from discord.ext import commands

from config import BOT_TOKEN, GUILD_ID, LOG_LEVEL
from utils.logger import get_logger, setup_logging

logger = get_logger("main")

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


def _run() -> None:
    bot = LteBot(command_prefix="/", intents=intents)

    while True:
        try:
            bot.run(BOT_TOKEN, log_handler=None)
        except (discord.LoginFailure, discord.PrivilegedIntentsRequired) as e:
            logger.critical("Unrecoverable error: %s", e)
            return
        except (discord.ConnectionClosed, OSError, aiohttp.ClientError) as e:
            logger.error("Connection lost: %s — retrying in 30s", e)
            time.sleep(30)
            continue
        except Exception as e:
            logger.exception("Unexpected crash: %s — retrying in 30s", e)
            time.sleep(30)
            continue
        break


if __name__ == "__main__":
    setup_logging(LOG_LEVEL)
    _run()
