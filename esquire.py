import sys
import os
import io
import asyncio
import loghandler
import tempfile
import typing
import random

import exceptions
from wobbify import wobbifystring
from wobbify import wobbifytxt
import jsonhandler

import discord
from discord.ext import commands

log = loghandler.get_logger(__name__)


class Argboolparse(commands.Converter):
    def __init__(self, keyword):
        self.keyword = keyword

    async def convert(self, ctx, argument):
        return argument == self.keyword


class Esquire(commands.Bot):
    def __init__(self):
        self.config = jsonhandler.JsonHandler('config.json')
        self.command_prefix = self.config.get('command_prefixes')
        super(Esquire, self).__init__(self.command_prefix)
        self.add_cog(BasicCommands(self))
        self.initialise()

    def initialise(self):
        try:
            self.loop.run_until_complete(
                self.start(self.config.get('bot_token')))
        except discord.errors.LoginFailure:
            log.critical(
                f"Could not login the bot because the wrong credentials were passed. Are you sure the bot_token {self.config.get('bot_token')} is correct?"
            )
        except discord.errors.HTTPException as e:
            log.critical("HTTP request failed, error code: " + e.code)
        except discord.errors.GatewayNotFound:
            log.critical(
                "Gateway connection could not be established. The Discord API is probably experiencing an outage."
            )
        except discord.errors.ConnectionClosed as e:
            log.critical("Gateway connection has been closed: " + e.reason)
        except RuntimeError:
            pass
        finally:
            self.quit()

    def cleanup(self):
        self.loop.run_until_complete(self.close())
        try:
            tasks = asyncio.all_tasks()
            pending = asyncio.gather(*tasks)
            pending.cancel()
            pending.exception()
        except:
            pass
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        self.loop.close()

    def quit(self):
        log.info("Cleaning up...")
        try:
            self.cleanup()
        except:
            log.warn("Encountered an error in cleanup.")
        finally:
            raise exceptions.ExitSignal


class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for channel in self.bot.get_all_channels():
            if isinstance(channel, discord.TextChannel) and str(
                    channel) in self.bot.config.get('allowed_text_channels'):
                await channel.send("Esquire initialised.")

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("ENEMY ARN DETECTED")

    @commands.command()
    async def wobbify(self, ctx, *args):
        if len(ctx.message.attachments) != 0:
            for a in ctx.message.attachments:
                if a.filename[-4:] == '.txt':
                    txtbytes = await a.read()
                    wobbifiedtxtbytes = wobbifytxt(txtbytes)
                    wobbifiedfile = discord.File(fp=wobbifiedtxtbytes,
                                                 filename=a.filename[:-4] +
                                                 '_wobbified.txt')
                    await ctx.send(file=wobbifiedfile)
        else:
            argstr = " ".join(args)
            await ctx.send(wobbifystring(argstr))

    @commands.command()
    async def deletelast(self,
                         ctx,
                         member: typing.Optional[discord.Member] = None,
                         covert: Argboolparse('covert') = False):

        messages = ctx.history().filter(lambda x: not x.author.bot)
        if member != None:
            async for m in messages:
                if (m.author == member and m != ctx.message):
                    message = m
                    break
        else:
            messages = await messages.flatten()
            message = messages[1]
        await message.delete()
        if covert:
            await ctx.message.delete()
        else:
            await ctx.send("NOTHING TO SEE HERE. MOVE ALONG.")