import asyncio

from spotipy.exceptions import SpotifyException
import loghandler
import random

import exceptions
import wobbify
import jsonhandler
import loghandler

import yt_dlp as youtube_dl
from requests import get
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import discord
import discord.utils
from discord.ext import commands

log = loghandler.get_logger(__name__)
dlog = loghandler.get_logger('discord')

ffmpeg_options = {
    'options': '-vn',
    "before_options":
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}

config = jsonhandler.JsonHandler('config.json')

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=config.get('spotify_client_id'),
    client_secret=config.get('spotify_client_secret')))


def is_music_channel(ctx):
    return str(ctx.channel) in config.get('music_channel')


class Esquire(commands.Bot):
    def __init__(self):
        self.command_prefix = config.get('command_prefixes')
        intents = discord.Intents.default()
        intents.message_content = True
        super(Esquire, self).__init__(self.command_prefix, intents=intents)
        self.exit_signal = None
        self.run(config.get('bot_token'), log_handler=loghandler.log_handler, log_formatter=loghandler.log_formatter)
        if self.exit_signal:
            raise self.exit_signal

    async def close(self):
        log.info("Closing down!")
    
    async def setup_hook(self):
        await self.add_cog(BasicCommands(self))
        await self.add_cog(MusicCommands(self))

    def quit(self):
        self.exit_signal = exceptions.ExitSignal()


class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
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
                    wobbifiedtxtbytes = wobbify.wobbifytxt(txtbytes)
                    wobbifiedfile = discord.File(fp=wobbifiedtxtbytes,
                                                 filename=a.filename[:-4] +
                                                 '_wobbified.txt')
                    await ctx.send(file=wobbifiedfile)
        else:
            argstr = " ".join(args)
            await ctx.send(wobbify.wobbifystring(argstr))


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlistmanagers = []
        self.playlist_messages = []

    @commands.Cog.listener()
    async def on_message(self, message):
        is_playlist_message = message.content == '...' and message.author.bot
        if str(message.channel) in config.get(
                'music_channel') and not is_playlist_message:
            await message.delete(delay=3)

    @commands.command()
    async def connect(self, ctx):
        try:
            connect_channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                await connect_channel.connect()
            elif ctx.voice_client.channel != connect_channel:
                await ctx.voice_client.move_to(connect_channel)
            self.playlistmanagers.append(PlaylistManager(ctx))
        except:
            await ctx.send(
                "You're not in a channel, you doofus! How am I supposed to know where to connect?!"
            )

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def play(self, ctx, *, query):
        plmanager = PlaylistManager.retrieve_playlist_manager(
            ctx, self.playlistmanagers)
        if plmanager != None:
            await plmanager.queue(query, next=False)

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def playnext(self, ctx, *, query):
        plmanager = PlaylistManager.retrieve_playlist_manager(
            ctx, self.playlistmanagers)
        await plmanager.queue(query, next=True)

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def playspotify(self, ctx, url, amount=10, shuffle=''):
        shufflebool = False if shuffle == '' else True
        plmanager = PlaylistManager.retrieve_playlist_manager(
            ctx, self.playlistmanagers)
        await plmanager.queue_spotify(url, amount, shufflebool)

    @playspotify.before_invoke
    @playnext.before_invoke
    @play.before_invoke
    async def ensure_connection(self, ctx):
        await self.connect(ctx)

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def skip(self, ctx):
        ctx.voice_client.stop()

    @commands.command(pass_context=True)
    @commands.check(is_music_channel)
    async def stop(self, ctx):
        plmanager = PlaylistManager.retrieve_playlist_manager(
            ctx, self.playlistmanagers)
        plmanager.playlist = plmanager.playlist[0:1:]
        ctx.voice_client.stop()


class PlaylistManager:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.textchannel = ctx.channel
        self.guild = ctx.guild
        self.voiceclient = ctx.voice_client
        self.playlist = []
        self.playlist_message = None

    async def queue(self, query, next=False):
        playlistitem = await PlaylistItem.yt_populate(query,
                                                      loop=self.bot.loop)
        if next:
            self.playlist.insert(1, playlistitem)
        else:
            self.playlist.append(playlistitem)
        if len(self.playlist) == 1:
            await self.playlist_message_send()
            await self.playback()
        else:
            await self.playlist_message_update()

    async def queue_spotify(self, url, amount=10, shuffle=False):
        try:
            playlist = sp.playlist_items(url, additional_types=['track'])
        except SpotifyException:
            log.warning(
                "Error retrieving the playlist from Spotify. The Spotify API might be down, or the provided URL might not be a playlist."
            )
            return
        tracks = playlist['items']
        while playlist['next']:
            playlist = sp.next(playlist)
            tracks.extend(playlist['items'])
        if shuffle:
            random.shuffle(tracks)
        for i in range(min(amount, len(tracks))):
            title = tracks[i]['track']['name']
            artist = tracks[i]['track']['artists'][0]['name']
            await self.queue(artist + ' ' + title)

    async def playback(self):
        if len(self.playlist) == 0:
            await self.voiceclient.disconnect()
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
                              after=self.after_playback)

    def after_playback(self, error):
        del self.playlist[0]
        asyncio.run_coroutine_threadsafe(self.playback(), self.bot.loop)

    async def playlist_message_update(self):
        embed = discord.Embed(title='Now Playing',
                              description=self.playlist[0].title,
                              colour=discord.Colour.red())
        embed.set_thumbnail(url=self.playlist[0].thumbnail)
        playlistduration = sum([plitem.duration for plitem in self.playlist])
        duration_s = str(playlistduration % 60)
        duration_m = str((playlistduration % 3600) // 60)
        duration_h = str(playlistduration // 3600)
        embed.set_footer(
            text=f"Total duration: {duration_h}h{duration_m}m{duration_s}s")
        if len(self.playlist) > 1:
            for i, pitem in enumerate(self.playlist[1:]):
                embed.add_field(name=str(i + 1).zfill(3),
                                value=pitem.title,
                                inline=False)
        await self.playlist_message.edit(embed=embed, content=None)

    async def playlist_message_send(self):
        self.playlist_message = await self.textchannel.send(content='...')

    async def playlist_message_delete(self):
        await self.playlist_message.delete()

    @classmethod
    def retrieve_playlist_manager(cls, ctx, playlistmanagers_list):
        for plmanager in playlistmanagers_list:
            if ctx.voice_client == plmanager.voiceclient:
                return plmanager


class PlaylistItem:
    def __init__(self, title, thumbnail, duration, upload_date, audio_source):
        self.title = title
        self.thumbnail = thumbnail
        self.duration = duration
        self.upload_date = upload_date
        self.audio_source = audio_source
        self.start = None
        self.end = None

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
            try:
                data = data['entries'][0]
            except:
                log.warning(
                    f"YTDL found no search results for query \'{query}\'")
        title = data['title']
        thumbnail = data['thumbnail']
        duration = data['duration']  #in seconds
        upload_date = data['upload_date']  #YYYYDDMM
        formats = data['formats']
        for f in formats:
            if f['format_id'] == '140':
                audiostream_url = f['url']
                break
        audio_source = discord.FFmpegOpusAudio(audiostream_url,
                                               **ffmpeg_options)
        return cls(title, thumbnail, duration, upload_date, audio_source)
