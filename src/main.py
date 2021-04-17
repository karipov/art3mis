import json, pathlib
from datetime import datetime, time, timedelta
import asyncio
import logging
import argparse

import pytz
from discord.ext import commands, tasks
from discord import FFmpegPCMAudio, Activity, ActivityType


parser = argparse.ArgumentParser(description="LDR discord bot artemis")
parser.add_argument("--config", dest="config", default="files/config_testing.json")
args = parser.parse_args()

PROJECT_FOLDER = pathlib.Path.cwd()
CONFIG = json.load(open(PROJECT_FOLDER.joinpath(args.config), "r"))
REPLIES = json.load(open(PROJECT_FOLDER.joinpath("files/replies.json"), "r"))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
            filename=PROJECT_FOLDER.joinpath("files/discord.log"),
            encoding="utf-8",
            mode="w"
        )
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot = commands.Bot(command_prefix="!")
bot.remove_command('help')


# HELPER FUNCTIONALITY
def seconds_until(hours: int, minutes: int, locale: str = "Europe/Zurich") -> str:
    """ Calculates seconds until given time in given time zone """
    timezone = pytz.timezone(locale)
    given_time = time(hours, minutes)  # time is naive but provided by user with locale so OK

    # localizing current time from utc but making it naive so everything is naive
    now = pytz.utc.localize(datetime.utcnow()).astimezone(timezone).replace(tzinfo=None)
    following = datetime.combine(now, given_time)

    # if past execution time for today, move to tomorrow
    if (following - now).days < 0:
        following = datetime.combine(now + timedelta(days=1), given_time)

    return (following - now).total_seconds()


# TASKS
@tasks.loop(hours=24)
async def job(params: dict):
    sleep_time = seconds_until(**params)
    await asyncio.sleep(sleep_time)
    
    # join voice channel
    channel = bot.get_channel(CONFIG["AUDIO"])
    voice = await channel.connect()

    voice.play(FFmpegPCMAudio(PROJECT_FOLDER.joinpath("files/nudge.mp3")))

    while voice.is_playing():
        await asyncio.sleep(1)

    await voice.disconnect()


# BOT EVENTS
@bot.event
async def on_ready():
    logger.info("Bot online!")
    await bot.change_presence(activity=Activity(
        type=ActivityType.listening, name="!help for commands and info!")
    )


# BOT COMMANDS
@bot.command()
async def alarm(ctx, intime: str, locale: str = "Europe/Zurich"):
    try:
        params = dict()
        params["hours"], params["minutes"] = map(int, intime.split(":"))
        params["locale"] = locale

        if locale not in pytz.all_timezones:
            raise KeyError("timezone invalid")

    except ValueError:
        await ctx.send(REPLIES["TIME_ERR"].format(intime))
        return
    except KeyError:
        await ctx.send(REPLIES["LOCALE_ERR"].format(locale))

    task = job.get_task()
    if task and not task.done():
        job.restart(params)
    else:
        job.start(params)
    
    logger.info(f"alarm set for {intime} and locale {locale} by {ctx.author.name}")

    await ctx.send(REPLIES["ALARM_SET"].format(intime, locale))

@bot.command()
async def help(ctx):
    logger.info(f"help by {ctx.author.name}") 
    await ctx.send(REPLIES["HELP"])

@bot.command()
async def code(ctx):
    logger.info(f"code by {ctx.author.name}") 
    await ctx.send(REPLIES["CODE"])


bot.run(CONFIG["TOKEN"])
