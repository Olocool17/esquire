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
import discord.utils
from discord.ext import commands

log = loghandler.get_logger(__name__)
discordlog = loghandler.get_logger('discord')

ffmpeg_options = {
    'options': '-vn',
    "before_options":
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}

config = jsonhandler.JsonHandler('config.json')


def is_music_channel(ctx):
    return str(ctx.channel) == config.get('music_channel') or str(
        ctx.channel) in config.get('music_channel')


class Esquire(commands.Bot):
    def __init__(self):
        self.command_prefix = config.get('command_prefixes')
        super(Esquire, self).__init__(self.command_prefix)
        self.exit_signal = None
        self.add_cog(BasicCommands(self))
        self.add_cog(MusicCommands(self))
        self.initialise()

    def initialise(self):
        try:
            self.loop.run_until_complete(self.start(config.get('bot_token')))
        except discord.errors.LoginFailure:
            log.critical(
                f"Could not login the bot because the wrong credentials were passed. Are you sure the bot_token {config.get('bot_token')} is correct?"
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
                    channel) in config.get('allowed_text_channels'):
                await channel.send("Esquire initialised.")
        await self.bot.change_presence(status=discord.Status.idle,
                                       activity=None)

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
        self.playlist_message = None

    @commands.command()
    async def connect(self, ctx):
        connect_channel = ctx.author.voice.channel
        if connect_channel != None:
            if ctx.voice_client is None:
                await connect_channel.connect()
            else:
                await ctx.voice_client.move_to(connect_channel)
        self.voiceclient = ctx.voice_client

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def play(self, ctx, *, query):
        playlistitem = await PlaylistItem.yt_populate(query,
                                                      loop=self.bot.loop)
        self.playlist.append(playlistitem)
        await self.playlist[-1].calculate_start_end(self.playlist)
        if len(self.playlist) == 1:
            await self.playlist_message_send(ctx)
            await self.playback()
        else:
            await self.playlist_message_update()

    @play.before_invoke
    async def ensure_connection(self, ctx):
        if ctx.voice_client is None:
            await self.connect(ctx)

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def skip(self, ctx):
        self.voiceclient.stop()

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def stop(self, ctx):
        self.playlist = self.playlist[0:1:]
        self.voiceclient.stop()

    async def playlist_message_update(self):
        embed = discord.Embed(title='Now Playing',
                              description=self.playlist[0].title)
        embed.set_thumbnail(url=self.playlist[0].thumbnail)
        if len(self.playlist) > 1:
            for i, pitem in enumerate(self.playlist[1:]):
                embed.add_field(name=str(i + 1).zfill(3),
                                value=pitem.title,
                                inline=False)
        await self.playlist_message.edit(embed=embed, content=None)

    async def playlist_message_send(self, ctx):
        self.playlist_message = await ctx.send(content='...')

    async def playlist_message_delete(self):
        await self.playlist_message.delete()

    async def playback(self):
        if len(self.playlist) == 0:
            await self.bot.change_presence(status=discord.Status.idle,
                                           activity=None)
            await self.playlist_message_delete()
            return
        await self.playlist_message_update()
        playing_activity = discord.Activity(type=discord.ActivityType.playing,
                                            name=self.playlist[0].title,
                                            details="Playing a song",
                                            state="Playing a song")
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=playing_activity)
        self.voiceclient.play(self.playlist[0].audio_source,
                              after=self.after_playback_async)

    def after_playback_async(self, error):
        fut = asyncio.run_coroutine_threadsafe(self.after_playback(),
                                               self.bot.loop)
        try:
            fut.result()
        except:
            pass

    async def after_playback(self):
        del self.playlist[0]
        await self.playback()


class PlaylistItem:
    def __init__(self, title, thumbnail, duration, upload_date, audio_source):
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration
        self.upload_date = upload_date
        self.audio_source = audio_source
        self.start = None
        self.end = None

    async def calculate_start_end(self, playlist):
        self.start = sum([plitem.duration + 1 for plitem in playlist[:-1:]])
        self.end = self.start + self.duration

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
        thumbnail = data['thumbnail']
        duration = data['duration']  #in seconds
        upload_date = data['upload_date']  #YYYYDDMM
        formats = data['formats']
        for f in formats:
            if f['format_id'] == '140':
                audiostream_url = f['url']
                break
        audio_source = discord.FFmpegPCMAudio(audiostream_url,
                                              **ffmpeg_options)
        return cls(title, thumbnail, duration, upload_date, audio_source)
