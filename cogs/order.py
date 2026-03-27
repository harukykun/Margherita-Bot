import discord
import asyncio
import json
import os
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

ORDER_ROLE_ID = 1462496903974617121
STAFF_ROLE_ID = 1462487968705937418
CATEGORY_ID = 1462493567669768395
DATA_DIR = "/data" if os.path.exists("/data") else "."
DATA_FILE = os.path.join(DATA_DIR, "order_data.json")

IMAGE_URL = "https://cdn.discordapp.com/attachments/1446129455440466066/1462511900129624186/this-game-always-delivers-with-the-npcs-v0-bq90k5gfl78e1.webp?ex=696e75d9&is=696d2459&hm=e492205c0de6cd2b053dc508f50c736e20533959613b9e168bec2646ed503470&"

def load_order_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"orders": {}}
    return {"orders": {}}

def save_order_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_order(channel_id, user_id, accepted=False, accepted_by=None):
    data = load_order_data()
    data["orders"][str(channel_id)] = {
        "user_id": user_id,
        "accepted": accepted,
        "accepted_by": accepted_by
    }
    save_order_data(data)

def update_order(channel_id, accepted=None, accepted_by=None):
    data = load_order_data()
    if str(channel_id) in data["orders"]:
        if accepted is not None:
            data["orders"][str(channel_id)]["accepted"] = accepted
        if accepted_by is not None:
            data["orders"][str(channel_id)]["accepted_by"] = accepted_by
        save_order_data(data)

def remove_order(channel_id):
    data = load_order_data()
    if str(channel_id) in data["orders"]:
        del data["orders"][str(channel_id)]
        save_order_data(data)

def get_order(channel_id):
    data = load_order_data()
    return data["orders"].get(str(channel_id))


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
        self.play_time = TextInput(
            label="Thời gian thường xuyên vào game",
            style=discord.TextStyle.short,
            placeholder="VD: 18h-22h hàng ngày, trưa 12h-14h,...",
            required=True,
            max_length=200
        )
        self.add_item(self.account_status)
        self.add_item(self.play_time)

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

        add_order(order_channel.id, interaction.user.id)

        order_embed = discord.Embed(
            title="Order Mới",
            color=discord.Color.gold()
        )
        order_embed.add_field(name="Người Order", value=f"{interaction.user.mention} ({interaction.user.display_name})", inline=False)
        order_embed.add_field(name="Hiện Trạng Account", value=self.account_status.value, inline=False)
        order_embed.add_field(name="Thời Gian Thường Vào Game", value=self.play_time.value, inline=False)
        order_embed.set_footer(text=f"User ID: {interaction.user.id}")
        order_embed.timestamp = discord.utils.utcnow()

        accept_view = AcceptOrderView(interaction.user.id, order_channel.id)
        staff_mention = f"<@&{STAFF_ROLE_ID}>"
        await order_channel.send(content=staff_mention, embed=order_embed, view=accept_view)

        await interaction.response.send_message(
            f"🍕 Qua kênh {order_channel.mention} nhé!",
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

    @discord.ui.button(label="Nhận Order", style=discord.ButtonStyle.green, emoji="✅", custom_id="accept_order_btn")
    async def accept_order(self, interaction: discord.Interaction, button: Button):
        if not self.has_staff_role(interaction.user):
            await interaction.response.send_message("Chỉ có Cooker mới có thể nhận Order", ephemeral=True)
            return

        self.accepted = True
        self.accepted_by = interaction.user.id

        update_order(self.channel_id, accepted=True, accepted_by=interaction.user.id)

        self.clear_items()
        
        complete_view = CompleteOrderView(self.order_user_id, self.channel_id)
        for item in complete_view.children:
            self.add_item(item)

        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"👌🏿 Cooker <@{interaction.user.id}> đã nhận order từ <@{self.order_user_id}>! Hãy cung cấp thông tin cụ thể acc để Cooker nắm rõ tình hình.\n **TUYỆT ĐỐI KHÔNG GỬI TÀI KHOẢN/MẬT KHẨU Ở ĐÂY**")


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
            await interaction.channel.send(f"👌🏿 <@{self.order_user_id}> Order đã được xử lý: **Cứu thành công**")
        else:
            await interaction.channel.send(f"<@{self.order_user_id}> 💀 Acc này hết cứu rút ống thở thôi.")

        remove_order(self.channel_id)

        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Cứu thành công", style=discord.ButtonStyle.green, emoji="✅", custom_id="success_order_btn")
    async def success_button(self, interaction: discord.Interaction, button: Button):
        if not self.has_staff_role(interaction.user):
            await interaction.response.send_message("❌ Bạn không có quyền thực hiện thao tác này!", ephemeral=True)
            return
        await self.complete_order(interaction, success=True)

    @discord.ui.button(label="Hết cứu", style=discord.ButtonStyle.red, emoji="💀", custom_id="failed_order_btn")
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

    @commands.Cog.listener()
    async def on_ready(self):
        data = load_order_data()
        for channel_id, order_info in list(data["orders"].items()):
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                remove_order(channel_id)
                continue
            
            if order_info["accepted"]:
                view = CompleteOrderView(order_info["user_id"], int(channel_id))
            else:
                view = AcceptOrderView(order_info["user_id"], int(channel_id))
            self.bot.add_view(view)

    @commands.command()
    async def setup_order(self, ctx):
        embed = discord.Embed(
            title="#TICKET",
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
    bot.add_view(AcceptOrderView(0, 0))
    bot.add_view(CompleteOrderView(0, 0))
    await bot.add_cog(OrderSystem(bot))
