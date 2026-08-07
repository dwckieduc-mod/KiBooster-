import asyncio
import discord
from discord.ext import commands
import database

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = database.load_data()

    # --- 1. LỆNH CẤU HÌNH ROLE BOOSTER DÙNG CHUNG ---

    @commands.command(name="booster")
    @commands.has_permissions(manage_roles=True)
    async def set_booster_role(self, ctx, booster_role: discord.Role):
        """Thiết lập Role Booster cố định cho server.
        Cú pháp: kb.booster <id_role_booster> hoặc mention @Role
        """
        guild_id = str(ctx.guild.id)
        if "booster_roles" not in self.db:
            self.db["booster_roles"] = {}

        self.db["booster_roles"][guild_id] = str(booster_role.id)
        
        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            await ctx.send(
                f"✅ **Đã cài đặt Role Booster chung cho Server!**\n"
                f"- **Role Booster:** {booster_role.mention} (ID: `{booster_role.id}`)\n"
                f"📌 Từ bây giờ bạn chỉ cần dùng `kb.link <role_custom> <user>`."
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi lưu vào Database Gist!")

    # --- 2. LỆNH LIÊN KẾT ROLE CUSTOM ---

    @commands.command(name="link")
    @commands.has_permissions(manage_roles=True)
    async def link_roles(self, ctx, child_role: discord.Role, member: discord.Member):
        """Liên kết Role Custom cho một User.
        Cú pháp: kb.link <id_role_custom> <id_user> (Hoặc tag @Role @User)
        """
        guild_id = str(ctx.guild.id)
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)

        # Kiểm tra xem Server đã set Role Booster chưa
        if not booster_role_id:
            return await ctx.send(
                "⚠️ **Server chưa thiết lập Role Booster chung!**\n"
                "Vui lòng dùng lệnh `kb.booster <id_role_booster>` trước 1 lần duy nhất."
            )

        if guild_id not in self.db["links"]:
            self.db["links"][guild_id] = {}

        self.db["links"][guild_id][str(child_role.id)] = {
            "user_id": str(member.id)
        }
        
        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            booster_role = ctx.guild.get_role(int(booster_role_id))
            booster_text = booster_role.mention if booster_role else f"ID `{booster_role_id}`"
            
            await ctx.send(
                f"✅ **Đã liên kết Role Custom thành công!**\n"
                f"- **Role Custom:** {child_role.mention} (ID: `{child_role.id}`)\n"
                f"- **Chủ sở hữu:** {member.mention} (ID: `{member.id}`)\n"
                f"- **Yêu cầu:** Có Role Booster ({booster_text})"
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi lưu vào Database Gist!")

    @commands.command(name="unlink")
    @commands.has_permissions(manage_roles=True)
    async def unlink_roles(self, ctx, child_role: discord.Role):
        """Hủy liên kết của một Role Custom."""
        guild_id = str(ctx.guild.id)
        if guild_id in self.db["links"] and str(child_role.id) in self.db["links"][guild_id]:
            del self.db["links"][guild_id][str(child_role.id)]
            await asyncio.to_thread(database.save_data, self.db)
            await ctx.send(f"✅ Đã hủy liên kết cho role {child_role.mention}.")
        else:
            await ctx.send("❌ Role này chưa được thiết lập liên kết nào.")

    @commands.command(name="list")
    async def list_links(self, ctx):
        """Xem danh sách Role Booster chung và các Role Custom trong server."""
        guild_id = str(ctx.guild.id)
        links = self.db["links"].get(guild_id, {})
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)
        
        booster_role = ctx.guild.get_role(int(booster_role_id)) if booster_role_id else None
        booster_name = booster_role.mention if booster_role else (f"ID: `{booster_role_id}`" if booster_role_id else "❌ *Chưa thiết lập (Dùng kb.booster)*")

        embed = discord.Embed(title="🔗 Danh sách Role Custom", color=discord.Color.blue())
        embed.description = f"⚡ **Role Booster chung:** {booster_name}\n"

        if not links:
            embed.add_field(name="Thông báo", value="Chưa có liên kết role custom nào.", inline=False)
            return await ctx.send(embed=embed)

        for child_id, info in links.items():
            child_role = ctx.guild.get_role(int(child_id))
            user_id = info.get("user_id") if isinstance(info, dict) else None

            owner_member = ctx.guild.get_member(int(user_id)) if user_id else None
            child_name = child_role.mention if child_role else f"ID: `{child_id}`"
            owner_name = owner_member.mention if owner_member else (f"ID: `{user_id}`" if user_id else "Không xác định")
            
            embed.add_field(
                name=f"Role Custom: {child_name} ", 
                value=f"👤 **Chủ sở hữu:** {owner_name}", 
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="restore")
    @commands.has_permissions(manage_roles=True)
    async def restore_roles(self, ctx, member: discord.Member = None):
        """Quét và cấp lại Role Custom cho đúng chủ sở hữu nếu họ có Role Booster."""
        guild_id = str(ctx.guild.id)
        guild_links = self.db["links"].get(guild_id, {})
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)

        if not booster_role_id:
            return await ctx.send("⚠️ Server chưa thiết lập Role Booster chung (`kb.booster`).")

        if not guild_links:
            return await ctx.send("⚠️ Chưa có thiết lập liên kết role nào.")

        target_members = [member] if member else ctx.guild.members
        restored_count = 0

        for target in target_members:
            user_id = str(target.id)
            user_role_ids = {str(r.id) for r in target.roles}
            to_add = []

            # Người này phải có Role Booster mới được cấp
            if booster_role_id in user_role_ids:
                for child_id_str, info in guild_links.items():
                    owner_user_id = info.get("user_id") if isinstance(info, dict) else None
                    
                    if owner_user_id == user_id and child_id_str not in user_role_ids:
                        role_obj = ctx.guild.get_role(int(child_id_str))
                        if role_obj:
                            to_add.append(role_obj)

            if to_add:
                try:
                    await target.add_roles(*to_add, reason="Khôi phục role bằng kb.restore")
                    restored_count += len(to_add)
                except discord.Forbidden:
                    pass

        if member:
            await ctx.send(f"✅ Đã kiểm tra và cấp bổ sung {restored_count} role cho {member.mention}.")
        else:
            await ctx.send(f"✅ Đã quét toàn server và cấp bổ sung {restored_count} role.")

    # --- 3. SỰ KIỆN THEO DÕI TỰ ĐỘNG GỠ / CẤP ROLE ---

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_role_ids = {str(r.id) for r in before.roles}
        after_role_ids = {str(r.id) for r in after.roles}

        if before_role_ids == after_role_ids:
            return

        guild_id = str(after.guild.id)
        guild_links = self.db["links"].get(guild_id, {})
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)

        if not guild_links or not booster_role_id:
            return

        roles_to_remove = []
        roles_to_add = []
        user_id = str(after.id)

        for child_id_str, info in guild_links.items():
            owner_user_id = info.get("user_id") if isinstance(info, dict) else None

            if not owner_user_id:
                continue

            if user_id == owner_user_id:
                # 1. ĐÚNG CHỦ SỞ HỮU:
                # Có Role Booster -> Thêm Role Custom (nếu chưa có)
                if booster_role_id in after_role_ids and child_id_str not in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_add.append(role_obj)
                
                # Mất Role Booster -> Gỡ Role Custom (nếu đang có)
                elif booster_role_id not in after_role_ids and child_id_str in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_remove.append(role_obj)
            else:
                # 2. KHÔNG PHẢI CHỦ SỞ HỮU:
                # Nếu lỡ nhầm cấp Role Custom này cho người khác -> Tự động gỡ
                if child_id_str in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_remove.append(role_obj)

        # Cấp Role
        if roles_to_add:
            try:
                await after.add_roles(*roles_to_add, reason="Liên kết ngầm: Có Role Booster")
                print(f"[AUTO-ADD] Đã thêm {len(roles_to_add)} role cho {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Quyền của Bot thấp hơn Role cần thêm")
            except Exception as e:
                print(f"[LỖI ADD] {e}")

        # Gỡ Role
        if roles_to_remove:
            try:
                await after.remove_roles(*roles_to_remove, reason="Liên kết ngầm: Mất Role Booster hoặc không đúng chủ sở hữu")
                print(f"[AUTO-REMOVE] Đã gỡ {len(roles_to_remove)} role từ {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Quyền của Bot thấp hơn Role cần gỡ")
            except Exception as e:
                print(f"[LỖI REMOVE] {e}")

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
    
