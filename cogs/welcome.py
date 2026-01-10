import discord
import random
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_messages = [
            "Chào mừng {member} đến với tiệm Pizza gọi pizza dứa hoặc bị doot deet <a:kcsalami:1457413393366384869> ",
            "Rất vui được gặp bro, {member}! Hy vọng bro sẽ thích pizza dứa ở đây<:cheemthanhlich:1443896875127144448> ",
            "Hãy cứ là chính mình nhé, {member}! Dù bro có là Fembi thì ae Pizza vẫn luôn chào đón bro <:ChisaScary:1451015932376776845> ",
            "Này {member}, qua đây doot deet đê <a:kcsalami:1457413393366384869>"
        ]

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel_id = 1397176401668472842
        channel = member.guild.get_channel(channel_id)
        
        if channel:
            random_text = random.choice(self.welcome_messages)
            content = random_text.format(member=member.mention)
            message = await channel.send(content)
async def setup(bot):
    await bot.add_cog(Welcome(bot))