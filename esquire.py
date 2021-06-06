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

import youtube_dl
from requests import get

import discord
from discord.ext import commands

log = loghandler.get_logger(__name__)
discordlog = loghandler.get_logger('discord')

ffmpeg_options = {
    'options': '-vn',
    "before_options":
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}


class Esquire(commands.Bot):
    def __init__(self):
        self.config = jsonhandler.JsonHandler('config.json')
        self.command_prefix = self.config.get('command_prefixes')
        super(Esquire, self).__init__(self.command_prefix)
        self.add_cog(BasicCommands(self))
        self.add_cog(MusicCommands(self))
        self.exit_signal = None
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
        finally:
            if self.exit_signal:
                raise self.exit_signal

    async def cleanup(self):
        try:
            self.loop.run_until_complete(self.loop.close())
        except:
            pass
        try:
            tasks = asyncio.all_tasks()
            pending = asyncio.gather(*tasks)
            pending.cancel()
            pending.exception()
        except:
            pass
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def quit(self):
        self.exit_signal = exceptions.ExitSignal()
        log.info("Cleaning up...")
        try:
            await self.cleanup()
        except:
            log.warn("Encountered an error in cleanup.")


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
        name = ctx.author.name.upper()
        await ctx.send(f"ENEMY {name} DETECTED")

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


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist = []
        self.voiceclient = None

    @commands.command()
    async def connect(self, ctx):
        connect_channel = ctx.author.voice.channel
        if connect_channel != None:
            if ctx.voice_client is None:
                await connect_channel.connect()
            else:
                await ctx.voice_client.move_to(connect_channel)
        self.voiceclient = ctx.voice_client

    @commands.command()
    async def play(self, ctx, *, query):
        playlistitem = await PlaylistItem.yt_populate(query,
                                                      loop=self.bot.loop)
        self.playlist.append(playlistitem)
        if len(self.playlist) == 1:
            await self.playback()

    @play.before_invoke
    async def ensure_connection(self, ctx):
        if ctx.voice_client is None:
            await self.connect(ctx)

    async def playback(self):
        if len(self.playlist) == 0:
            return
        self.voiceclient.play(self.playlist[0].audio_source)
        await asyncio.sleep(self.playlist[0].duration + 1)
        del self.playlist[0]
        await self.playback()


class PlaylistItem:
    def __init__(self, title, thumbnail, duration, upload_date, audio_source):
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration
        self.upload_date = upload_date
        self.audio_source = audio_source

    @classmethod
    async def yt_populate(cls, query, loop=None):
        loop = loop or asyncio.get_event_loop()
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                get(query)
                data = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(query, download=False))
            except:
                data = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(f"ytsearch:{query}",
                                                   download=False))
        if 'entries' in data:
            data = data['entries'][0]
        title = data['title']
        thumbnail = get(data['thumbnail'])
        duration = data['duration']  #in seconds
        upload_date = data['upload_date']  #YYYYDDMM
        formats = data['formats']
        for f in formats:
            if f['format_id'] == '140':
                audiostream_url = f['url']
                break
        print(audiostream_url)
        audio_source = discord.FFmpegPCMAudio(audiostream_url,
                                              **ffmpeg_options)
        return cls(title, thumbnail, duration, upload_date, audio_source)
