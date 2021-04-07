import sys
import os
import io
import asyncio
import logging
import tempfile

import exceptions
from wobbify import wobbifystring
from wobbify import wobbifytxt
import jsonhandler

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Esquire(commands.Bot):
    async def __init__(self):
        self.config = jsonhandler.JsonHandler('config.json')
        self.command_prefix = self.config.get('command_prefixes')
        super(Esquire, self).__init__(self.command_prefix)
        self.commandsinit()
        await self.initialise()

    def commandsinit(self):
        @self.event
        async def on_ready():
            for channel in self.get_all_channels():
                if isinstance(channel, discord.TextChannel) and str(
                        channel) in self.config.get('allowed_text_channels'):
                    await channel.send("Esquire initialised.")

        @self.command()
        async def hello(ctx):
            await ctx.send("ENEMY ARN DETECTED")

        @self.command()
        async def wobbify(ctx, *args):
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

        @self.command()
        async def deletelast(ctx, *args):
            author = None
            covert = False
            listargs = list(args)
            try:
                if "covert" in listargs:
                    covert = True
                    listargs.remove('covert')
            except:
                log.error(f"Argument parsing error for {ctx.message}")
                return
            try:
                author = listargs[0]
            except:
                pass

            if await self.checkifowner(ctx):
                messages = ctx.history().filter(lambda x: not x.author.bot)
                if author != None:
                    async for m in messages:
                        if (m.author.name == author and m != ctx.message):
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

        @self.command()
        async def shutdown(ctx):
            self.close()
            asyncio.sleep(3)
            sys.exit(0)

    async def checkifowner(self, ctx):
        if await self.is_owner(ctx.author):
            return True
        await ctx.send("NICE TRY. INSECT")
        return False

    def initialise(self):
        try:
            self.loop.run_until_complete(
                self.start(self.config.get('bot_token')))
        except discord.errors.LoginFailure:
            log.critical(
                f"Could not login the bot because the wrong credentials were passed. Are you sure the bot_token {self.config.get('bot_token')} is correct?"
            )
            self.quit()
        except discord.errors.HTTPException as e:
            log.critical("HTTP request failed, error code: " + e.code)
        except discord.errors.GatewayNotFound:
            log.critical(
                "Gateway connection could not be established. The Discord API is probably experiencing an outage."
            )
        except discord.errors.ConnectionClosed as e:
            log.critical("Gateway connection has been closed: " + e.reason)
        finally:
            self.quit()

    def cleanup(self):
        try:
            self.loop.run_until_complete(self.close())
        except:
            pass
        tasks = asyncio.all_tasks()
        pending = asyncio.gather(*tasks)
        try:
            pending.cancel()
        except:
            pass
        self.loop.close()

    def quit(self):
        try:
            self.cleanup()
        except:
            log.warn("Encountered an error in cleanup.")
        finally:
            raise exceptions.ExitSignal
