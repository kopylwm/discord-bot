import discord
from discord.ext import commands

import wavelink
import datetime

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Queue stuff
        self.queue: wavelink.Queue = wavelink.Queue()
        self.saved_queue: wavelink.Queue = wavelink.Queue()
        self.queue_ctx: commands.Context = None

        # Loop stuff
        self.loop_var: bool = False
        self.queue_loop_var: bool = False
        self.loop_track: wavelink.YouTubeTrack = None

        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        # Connect to Lavalink nodes
        await self.bot.wait_until_ready()

        await wavelink.NodePool.create_node(bot=self.bot,
                                            host='0.0.0.0',
                                            port=2333,
                                            password='lavalink')

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        # Fire event when a node has finished connecting
        print(f'[lavalink]: node <{node.identifier}> is ready!')

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.YouTubeTrack, reason):
        if self.loop_var:
            return await player.play(self.loop_track)

        if self.queue_loop_var and not self.queue:
            for song in self.saved_queue:
                self.queue.put(song)

        if not self.queue:
            self.queue_ctx = None
            return

        try:
            track = self.queue.get()
        except: return

        await self.queue_ctx.send(embed=self._return_embed('PLAY_TRACK', track=track))
        await player.play(track)

    @commands.command()
    async def connect(self, ctx: commands.Context):
        """Connect to the voice channel"""
        if ctx.voice_client:
            return

        try:
            player: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)

            # Make bot deaf
            await ctx.guild.change_voice_state(channel=ctx.author.voice.channel, self_mute=False, self_deaf=True)
        except:
            await ctx.send(embed=self._return_embed('CONN_FAIL'))

    @commands.command()
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return

        await player.disconnect()

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):
        """Add YT track to the queue and play it"""
        await ctx.invoke(self.connect)
        vc = ctx.voice_client

        # Check if the player is in the same voice channel as the author
        if ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send(embed=self._return_embed('NOT_SAME_VC'))

        track: wavelink.YouTubeTrack = await wavelink.YouTubeTrack.search(query=query, return_first=True)

        if not track:
            return await ctx.send(embed=self._return_embed('NO_TRACK'))

        await ctx.send(embed=self._return_embed('ADD_TRACK', track=track))
        self.queue.put(track)
        self.saved_queue.put(track)
        
        if self.loop_var and self.loop_track is None:
            self.loop_track = self.queue.get()
            await ctx.send(embed=self._return_embed('PLAY_TRACK'))

        self.queue_ctx = ctx
        if not vc.is_playing():
            await self.on_wavelink_track_end(player=vc, track=track, reason=None)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        """Skip current track to the next one"""
        try:
            vc: wavelink.Player = ctx.voice_client
            if not vc.is_playing():
                return await ctx.send(embed=self._return_embed('VC_NOT_PLAY'))

            if ctx.author.voice.channel.id != vc.channel.id:
                return await ctx.send(embed=self._return_embed('NOT_SAME_VC'))
        except: return
        
        await ctx.send(embed=self._return_embed('SKIP'))
        await vc.stop()
        
        if self.loop_var:
            self.loop_track = self.queue.get()
            await ctx.send(embed=self._return_embed('PLAY_TRACK'))

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stop current track and clear the queue"""
        try:
            vc: wavelink.Player = ctx.voice_client
            if ctx.author.voice.channel.id != vc.channel.id:
                return await ctx.send(embed=self._return_embed('NOT_SAME_VC'))
        except: return

        self.loop_var = False

        if self.saved_queue:
            if self.queue:
                self.queue.clear()
            self.saved_queue.clear()

        if vc.is_playing():
            await vc.stop()
        
        await ctx.send(embed=self._return_embed('STOP'))

        self.loop_var = True if self.loop_track else False
        self.loop_track = None

    @commands.command()
    async def queue(self, ctx: commands.Context):
        """List all tracks in the queue"""
        if not self.saved_queue:
            return await ctx.send(embed=self._return_embed('QUEUE_EMPTY'))
        await ctx.send(embed=self._return_embed('QUEUE'))

    @commands.command()
    async def loop(self, ctx: commands.Context):
        """Enable/Disable track loop"""
        await ctx.send(embed=self._return_embed('LOOP'))
        if self.loop_var:
            self.loop_var = False
            self.loop_track = None
            return

        try:
            vc: wavelink.Player = ctx.voice_client
            if vc.is_playing():
                self.loop_track = vc.track
        except: pass

        self.loop_var = True

    @commands.command()
    async def loop_queue(self, ctx: commands.Context):
        """Enable/Disable queue loop"""
        await ctx.send(embed=self._return_embed('QUEUE_LOOP'))
        self.queue_loop_var = False if self.queue_loop_var else True
    
    def _return_embed(self, idx: str, track: wavelink.YouTubeTrack = None) -> discord.Embed:
        """
        Returns a discord.Embed object

        idx:
        'VC_NOT_PLAY' - if the player is not playing anything
        'NOT_SAME_VC' - if the player is in the same voice channel as the author
        'CONN_FAIL' - if player cannot connect to the voice channel
        'NO_TRACK' - if no track was found with given query
        'PLAY_TRACK' - give info about playing track
        'ADD_TRACK' - give info about added track to the queue
        'SKIP' - skip current track
        'STOP' - stop current track and clear the queue
        'QUEUE_EMPTY' - if queue is empty
        'QUEUE' - give info about queue
        'LOOP' - enable/disable track looping
        'QUEUE_LOOP' - enable/disable queue looping
        """
        if idx == 'VC_NOT_PLAY':
            embed = discord.Embed(
                title=None,
                description=':x: **Nothing is playing right now!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'NOT_SAME_VC':
            embed = discord.Embed(
                title=None,
                description=':x: **You must be in the same voice channel as the player!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'CONN_FAIL':
            embed = discord.Embed(
                title=None,
                description=':x: **Cannot connect to the voice channel!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'NO_TRACK':
            embed = discord.Embed(
                title=None,
                description=':x: **No track found with given query!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'PLAY_TRACK':
            track = self.loop_track if track is None else track

            embed = discord.Embed(
                title=':anger: Now playing',
                description=None,
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=track.thumb)
            embed.add_field(name='**Title**', value=track.title, inline=True)
            embed.add_field(name='**Author**', value=track.author, inline=True)
            embed.add_field(name='**Duration**', value=datetime.timedelta(seconds=track.duration), inline=True)
            return embed
        elif idx == 'ADD_TRACK':
            embed = discord.Embed(
                title=':anger: Added to the queue',
                description=None,
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=track.thumb)
            embed.add_field(name='**Title**', value=track.title, inline=True)
            embed.add_field(name='**Author**', value=track.author, inline=True)
            embed.add_field(name='**Duration**', value=datetime.timedelta(seconds=track.duration), inline=True)
            return embed
        elif idx == 'SKIP':
            vc: wavelink.Player = self.queue_ctx.voice_client

            embed = discord.Embed(
                title=':anger: Skipped current track',
                description=None,
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=vc.track.thumb)
            embed.add_field(name='**Title**', value=vc.track.title, inline=True)
            embed.add_field(name='**Author**', value=vc.track.author, inline=True)
            embed.add_field(name='**Duration**', value=datetime.timedelta(seconds=vc.track.duration), inline=True)
            return embed
        elif idx == 'STOP':
            embed = discord.Embed(
                title=None,
                description=':anger: **Stopped current track and cleared the queue!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'QUEUE_EMPTY':
            embed = discord.Embed(
                title=None,
                description=':anger: **The queue is empty!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'QUEUE':
            queue_list: str = '\n'.join([f'**{i + 1}. {song.title}**' for i, song in enumerate(self.saved_queue)])

            embed = discord.Embed(
                title=None,
                description=queue_list,
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'LOOP':
            embed = discord.Embed(
                title=None,
                description=':anger: **Disabled track loop!**' if self.loop_var else ':anger: **Enabled track loop!**',
                color=discord.Color.dark_red()
            )
            return embed
        elif idx == 'QUEUE_LOOP':
            embed = discord.Embed(
                title=None,
                description=':anger: **Disabled queue loop!**' if self.queue_loop_var else ':anger: **Enabled queue loop!**',
                color=discord.Color.dark_red()
            )
            return embed
        # Sadly match case statement is not working for me :(

def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
