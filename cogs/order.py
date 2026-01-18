import discord
import asyncio
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

ORDER_ROLE_ID = 1462496903974617121
STAFF_ROLE_ID = 1462487968705937418
CATEGORY_ID = 1462493567669768395

IMAGE_URL = "https://cdn.discordapp.com/attachments/1446129455440466066/1462511900129624186/this-game-always-delivers-with-the-npcs-v0-bq90k5gfl78e1.webp?ex=696e75d9&is=696d2459&hm=e492205c0de6cd2b053dc508f50c736e20533959613b9e168bec2646ed503470&"

class OrderModal(Modal):
    def __init__(self):
        super().__init__(title="Nhập thông tin Order")
        self.account_status = TextInput(
            label="Hiện trạng Account",
            style=discord.TextStyle.paragraph,
            placeholder="Nhập hiện trạng account của bạn...",
            required=True,
            max_length=1000
        )
        self.add_item(self.account_status)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role = interaction.guild.get_role(ORDER_ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
        except:
            pass

        category = interaction.guild.get_channel(CATEGORY_ID)
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        order_role = interaction.guild.get_role(ORDER_ROLE_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        if order_role:
            overwrites[order_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"order-{interaction.user.name}"
        order_channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        order_embed = discord.Embed(
            title="Order Mới",
            color=discord.Color.gold()
        )
        order_embed.add_field(name="Người Order", value=f"{interaction.user.mention} ({interaction.user.display_name})", inline=False)
        order_embed.add_field(name="Hiện Trạng Account", value=self.account_status.value, inline=False)
        order_embed.set_footer(text=f"User ID: {interaction.user.id}")
        order_embed.timestamp = discord.utils.utcnow()

        accept_view = AcceptOrderView(interaction.user.id, order_channel.id)
        staff_mention = f"<@&{STAFF_ROLE_ID}>"
        await order_channel.send(content=staff_mention, embed=order_embed, view=accept_view)

        await interaction.response.send_message(
            f"🍕 Order của bạn đã được tạo tại {order_channel.mention}!",
            ephemeral=True
        )


class AcceptOrderView(View):
    def __init__(self, order_user_id, channel_id):
        super().__init__(timeout=None)
        self.order_user_id = order_user_id
        self.channel_id = channel_id
        self.accepted = False
        self.accepted_by = None

    def has_staff_role(self, member: discord.Member) -> bool:
        return any(role.id == STAFF_ROLE_ID for role in member.roles)

    @discord.ui.button(label="Nhận Order", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_order(self, interaction: discord.Interaction, button: Button):
        if not self.has_staff_role(interaction.user):
            await interaction.response.send_message("Chỉ có Cooker mới có thể nhận Order", ephemeral=True)
            return

        self.accepted = True
        self.accepted_by = interaction.user.id

        self.clear_items()
        
        complete_view = CompleteOrderView(self.order_user_id, self.channel_id)
        for item in complete_view.children:
            self.add_item(item)

        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"👌🏿 Cooker <@{interaction.user.id}> đã nhận order từ <@{self.order_user_id}>! Hãy cung cấp thông tin cụ thể acc của bạn để Cooker nắm rõ tình hình.")


class CompleteOrderView(View):
    def __init__(self, order_user_id, channel_id):
        super().__init__(timeout=None)
        self.order_user_id = order_user_id
        self.channel_id = channel_id
        self.completed = False

    def has_staff_role(self, member: discord.Member) -> bool:
        return any(role.id == STAFF_ROLE_ID for role in member.roles)

    async def complete_order(self, interaction: discord.Interaction, success: bool):
        self.completed = True

        order_user = interaction.guild.get_member(self.order_user_id)
        if order_user:
            role = interaction.guild.get_role(ORDER_ROLE_ID)
            if role and role in order_user.roles:
                try:
                    await order_user.remove_roles(role)
                except:
                    pass

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        if success:
            await interaction.channel.send(f"👌🏿 <@{self.order_user_id}> Order đã được xử lý: **Cứu thành công**\n\nKênh sẽ bị xóa sau 5 giây...")
        else:
            await interaction.channel.send(f"<@{self.order_user_id}> 💀 Acc này hết cứu rút ống thở thôi.\n\nKênh sẽ bị xóa sau 5 giây...")

        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Cứu thành công", style=discord.ButtonStyle.green, emoji="✅")
    async def success_button(self, interaction: discord.Interaction, button: Button):
        if not self.has_staff_role(interaction.user):
            await interaction.response.send_message("❌ Bạn không có quyền thực hiện thao tác này!", ephemeral=True)
            return
        await self.complete_order(interaction, success=True)

    @discord.ui.button(label="Hết cứu", style=discord.ButtonStyle.red, emoji="💀")
    async def failed_button(self, interaction: discord.Interaction, button: Button):
        if not self.has_staff_role(interaction.user):
            await interaction.response.send_message("❌ Bạn không có quyền thực hiện thao tác này!", ephemeral=True)
            return
        await self.complete_order(interaction, success=False)


class OrderButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Order", style=discord.ButtonStyle.green, emoji="🍕", custom_id="order_btn")
    async def order_button(self, interaction: discord.Interaction, button: Button):
        modal = OrderModal()
        await interaction.response.send_modal(modal)


class OrderSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def setup_order(self, ctx):
        embed = discord.Embed(
            title="HỆ THỐNG TICKET",
            color=discord.Color.dark_embed()
        )

        guide_text = (
            "📋 **HƯỚNG DẪN** 🎮\n"
            "✅ Đây là kênh cứu tháp, thuyền và các content endgame Wuwa của tiệm Pizza\n"
            "✅ Hãy bấm vào order đề gửi order cứu acc nhé\n\n"
            "⚠️ **XIN LƯU Ý** 🎮\n"
            "❗ Hãy cung cấp hiện trạng sơ bộ acc của bạn\n"
            "❗ Không cung cấp tài khoản/mật khẩu trong sever này!!"
        )

        embed.description = guide_text
        embed.set_image(url=IMAGE_URL)

        await ctx.send(embed=embed, view=OrderButtonView())


async def setup(bot):
    bot.add_view(OrderButtonView())
    await bot.add_cog(OrderSystem(bot))
