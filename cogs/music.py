from discord.ext import commands
import discord

import wavelink
import datetime

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Queue stuff
        self.queue = wavelink.Queue()
        self.queue_ctx: commands.Context = None

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
        print(f'Node: <{node.identifier}> is ready!')

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: wavelink.Player, track: wavelink.YouTubeTrack, reason):
        if not self.queue:
            self.queue_ctx = None
            return
        
        track = self.queue.pop()
        await self.queue_ctx.send(f'**Now playing: {track.title} [{datetime.timedelta(seconds=track.length)}]**')
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
            await ctx.send('**Cannot connect to the voice channel.**')

    @commands.command()
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel"""
        player: wavelink.Player = ctx.voice_client
        if not player:
            return

        await player.disconnect()

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):
        """Play YT track with given query"""
        await ctx.invoke(self.connect)
        vc = ctx.voice_client

        # Check if the player is in the same voice channel as the author
        if ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.send('**You must be in the same voice channel as the player.**')

        track: wavelink.YouTubeTrack = await wavelink.YouTubeTrack.search(query=query, return_first=True)

        if not track:
            return await ctx.send('**No track found with given query.**')

        self.queue.put(track)
        await ctx.send(f'**Added to the queue: {track.title} [{datetime.timedelta(seconds=track.length)}]**')

        self.queue_ctx = ctx
        if not vc.is_playing():
            await self.on_wavelink_track_end(player=vc, track=track, reason=None)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        """Skips track to the next one"""
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing:
            return
        
        await vc.stop()
        await ctx.send(f'**Skipped {self.queue[0].title} [{datetime.timedelta(seconds=self.queue[0].length)}]**')
        await self.on_wavelink_track_end(player=vc, track=self.queue[0], reason=None)

    @commands.command()
    async def queue(self, ctx: commands.Context):
        """Lists all tracks in the queue"""
        if not self.queue:
            await ctx.send('**The queue is empty**')
        for idx, track in enumerate(self.queue):
            await ctx.send(f'{idx + 1}. {track.title} [{datetime.timedelta(seconds=track.length)}]')

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stops track and clears the queue"""
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            return

        await vc.stop()
        await ctx.send(f'**Cleared the queue**')
        await self.queue.clear()


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))