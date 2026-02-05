import discord
import re
import aiohttp
from discord import app_commands
from discord.ext import commands

class EmojiButton(discord.ui.Button):
    def __init__(self, name: str, url: str):
        super().__init__(label="Upload to server", style=discord.ButtonStyle.success)
        self.emoji_name = name
        self.emoji_url = url

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_expressions:
            return await interaction.response.send_message("Bạn không có quyền quản lý emoji!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.emoji_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("Không thể tải hình ảnh từ Discord CDN!", ephemeral=True)
                    img_data = await resp.read()
            
            await interaction.guild.create_custom_emoji(name=self.emoji_name, image=img_data)
            self.disabled = True
            self.label = "Uploaded"
            self.style = discord.ButtonStyle.secondary
            
            await interaction.edit_original_response(view=self.view)
            await interaction.followup.send(f"Đã thêm thành công emoji: **{self.emoji_name}**", ephemeral=True)

        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after if hasattr(e, 'retry_after') else "vài phút"
                await interaction.followup.send(f"Thất bại: Bạn đang bị Discord giới hạn (Rate Limit). Hãy thử lại sau {retry_after} giây.", ephemeral=True)
            else:
                await interaction.followup.send(f"Lỗi hệ thống: {str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Lỗi không xác định: {str(e)}", ephemeral=True)

class EmojiSteal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="emoji", description="Upload emoji từ danh sách")
    async def emoji(self, interaction: discord.Interaction, input: str):
        emoji_regex = r"<(a?):(\w+):(\d+)>"
        matches = re.findall(emoji_regex, input)

        if not matches:
            return await interaction.response.send_message("Không tìm thấy emoji", ephemeral=True)

        embeds = []
        view = discord.ui.View(timeout=None)

        for is_animated, name, emoji_id in matches[:5]:
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"

            embed = discord.Embed(color=0x2b2d31)
            embed.description = (
                f"**Emoji name:** `{name}`\n"
                f"**ID emoji:** `{emoji_id}`\n"
                f"**Emoji link:** [Can be clicked/copied]({url})"
            )
            embed.set_thumbnail(url=url)
            embeds.append(embed)
            
            view.add_item(EmojiButton(name=name, url=url))

        await interaction.response.send_message(embeds=embeds, view=view)

async def setup(bot):
    await bot.add_cog(EmojiSteal(bot))