import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load token từ file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") 

# Cấu hình Intents
intents = discord.Intents.default()
intents = discord.Intents.all()
intents.members = True
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Tự động load tất cả các file .py trong thư mục cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Đã load extension: {filename}")
                except Exception as e:
                    print(f"Không thể load {filename}: {e}")
    
        print("Đang đồng bộ lệnh Slash Command...")
        try:
            # Đồng bộ các lệnh app_commands (Slash Commands) với Discord
            synced = await self.tree.sync()
            print(f"Đã đồng bộ {len(synced)} lệnh.")
        except Exception as e:
            print(f"Lỗi đồng bộ lệnh: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

async def main():
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    if not TOKEN:
        print("Lỗi: Chưa tìm thấy DISCORD_TOKEN trong file .env")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass