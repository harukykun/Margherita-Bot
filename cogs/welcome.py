import discord
import random
import time
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_messages = [
            "Chào mừng {member} đến với tiệm Pizza gọi pizza dứa hoặc bị doot deet <a:kcsalami:1457413393366384869> ",
            "Rất vui được gặp bro, {member}! Hy vọng bro sẽ thích pizza dứa ở đây<:cheemthanhlich:1443896875127144448> ",
            "Hãy cứ là chính mình nhé, {member}! Dù bro có là Fembi thì ae Pizza vẫn luôn chào đón bro <:ChisaScary:1451015932376776845> ",
        ]

        self.welcome_times = {}
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        
        current_time = time.time()
        if member.id in self.welcome_times:
            if current_time - self.welcome_times[member.id] < 10:
                return
        self.welcome_times[member.id] = current_time
        
        channel_id = 1397176401668472842
        channel = member.guild.get_channel(channel_id)
        if channel:
            random_text = random.choice(self.welcome_messages)
            content = random_text.format(member=member.mention)
            await channel.send(content)
            to_remove = [mid for mid, t in self.welcome_times.items() if current_time - t > 60]
            for mid in to_remove:
                del self.welcome_times[mid]

async def setup(bot):
    await bot.add_cog(Welcome(bot))

async def teardown(bot):
    await bot.remove_cog("Welcome")