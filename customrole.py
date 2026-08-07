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
        """Thiết lập Role Booster cố định cho server."""
        guild_id = str(ctx.guild.id)
        if "booster_roles" not in self.db:
            self.db["booster_roles"] = {}

        self.db["booster_roles"][guild_id] = str(booster_role.id)
        
        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            embed = discord.Embed(
                title="✅ Cài Đặt Role Booster Thành Công",
                description=(
                    f"⚡ **Role Booster chung:** {booster_role.mention} (ID: `{booster_role.id}`)\n\n"
                    f"📌 *Từ bây giờ bạn chỉ cần gõ lệnh:* `kb.link <id_role_custom> <id_user>`"
                ),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Lỗi Hệ Thống",
                description="Đã xảy ra lỗi khi lưu dữ liệu vào Database!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    # --- 2. LỆNH LIÊN KẾT ROLE CUSTOM ---

    @commands.command(name="link")
    @commands.has_permissions(manage_roles=True)
    async def link_roles(self, ctx, child_role: discord.Role, member: discord.Member):
        """Liên kết Role Custom cho một User."""
        guild_id = str(ctx.guild.id)
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)

        if not booster_role_id:
            embed = discord.Embed(
                title="⚠️ Chưa Thiết Lập Role Booster",
                description="Server chưa thiết lập Role Booster chung!\nVui lòng dùng lệnh `kb.booster <id_role_booster>` trước.",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        if guild_id not in self.db["links"]:
            self.db["links"][guild_id] = {}

        self.db["links"][guild_id][str(child_role.id)] = {
            "user_id": str(member.id)
        }
        
        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            booster_role = ctx.guild.get_role(int(booster_role_id))
            booster_text = booster_role.mention if booster_role else f"ID `{booster_role_id}`"
            
            embed = discord.Embed(
                title="✅ Liên Kết Role Custom Thành Công",
                color=discord.Color.green()
            )
            embed.add_field(name="🎭 Role Custom", value=f"{child_role.mention} (ID: `{child_role.id}`)", inline=False)
            embed.add_field(name="👤 Chủ Sở Hữu", value=f"{member.mention} (ID: `{member.id}`)", inline=False)
            embed.add_field(name="⚡ Yêu Cầu", value=f"Có Role Booster ({booster_text})", inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Lỗi Hệ Thống",
                description="Đã xảy ra lỗi khi lưu vào Database!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="unlink")
    @commands.has_permissions(manage_roles=True)
    async def unlink_roles(self, ctx, child_role: discord.Role):
        """Hủy liên kết của một Role Custom."""
        guild_id = str(ctx.guild.id)
        if guild_id in self.db["links"] and str(child_role.id) in self.db["links"][guild_id]:
            del self.db["links"][guild_id][str(child_role.id)]
            await asyncio.to_thread(database.save_data, self.db)
            
            embed = discord.Embed(
                title="✅ Hủy Liên Kết Thành Công",
                description=f"Đã gỡ bỏ cài đặt liên kết cho role {child_role.mention}.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Lỗi Thực Thi",
                description=f"Role {child_role.mention} chưa từng được thiết lập liên kết nào.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="list")
    async def list_links(self, ctx):
        """Xem danh sách Role Booster chung và các Role Custom trong server."""
        guild_id = str(ctx.guild.id)
        links = self.db["links"].get(guild_id, {})
        booster_role_id = self.db.get("booster_roles", {}).get(guild_id)
        
        booster_role = ctx.guild.get_role(int(booster_role_id)) if booster_role_id else None
        booster_name = booster_role.mention if booster_role else (f"ID: `{booster_role_id}`" if booster_role_id else "❌ *Chưa thiết lập (Dùng kb.booster)*")

        embed = discord.Embed(title="🔗 Danh Sách Role Custom", color=discord.Color.blue())
        embed.description = f"⚡ **Role Booster chung:** {booster_name}\n"

        if not links:
            embed.add_field(name="Thông báo", value="Chưa có liên kết role custom nào.", inline=False)
            return await ctx.send(embed=embed)

        for child_id, info in links.items():
            child_role = ctx.guild.get_role(int(child_id))
            user_id = info.get("user_id") if isinstance(info, dict) else None

            owner_member = ctx.guild.get_member(int(user_id)) if user_id else None
            
            title_text = child_role.name if child_role else f"Role ID: {child_id}"
            child_mention = child_role.mention if child_role else f"`{child_id}`"
            owner_mention = owner_member.mention if owner_member else (f"`{user_id}`" if user_id else "Không xác định")
            
            embed.add_field(
                name=f"📌 {title_text}", 
                value=f"🎭 **Role Custom:** {child_mention}\n👤 **Chủ sở hữu:** {owner_mention}", 
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
            embed = discord.Embed(
                title="⚠️ Chưa Cấu Hình Role Booster",
                description="Server chưa thiết lập Role Booster chung (`kb.booster`).",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        if not guild_links:
            embed = discord.Embed(
                title="⚠️ Chưa Có Dữ Liệu Liên Kết",
                description="Chưa có thiết lập liên kết role custom nào.",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        target_members = [member] if member else ctx.guild.members
        restored_count = 0

        for target in target_members:
            user_id = str(target.id)
            user_role_ids = {str(r.id) for r in target.roles}
            to_add = []

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
            embed = discord.Embed(
                title="✅ Khôi Phục Cá Nhân Thành Công",
                description=f"Đã kiểm tra và cấp bổ sung **{restored_count}** role cho {member.mention}.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Khôi Phục Toàn Server Thành Công",
                description=f"Đã quét toàn bộ server và cấp bổ sung **{restored_count}** role.",
                color=discord.Color.green()
            )
        await ctx.send(embed=embed)

    @commands.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear_all_data(self, ctx):
        """Xóa toàn bộ dữ liệu cài đặt Role của server này."""
        guild_id = str(ctx.guild.id)

        if guild_id in self.db.get("booster_roles", {}):
            del self.db["booster_roles"][guild_id]
            
        if guild_id in self.db.get("links", {}):
            del self.db["links"][guild_id]

        if guild_id in self.db.get("history", {}):
            del self.db["history"][guild_id]

        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            embed = discord.Embed(
                title="🧹 Dọn Dẹp Dữ Liệu Dọn Dẹp",
                description="Đã xóa sạch toàn bộ dữ liệu cài đặt role của server này trên Database!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Lỗi Hệ Thống",
                description="Đã xảy ra lỗi khi cập nhật Database!",
                color=discord.Color.red()
            )
        await ctx.send(embed=embed)

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
                if booster_role_id in after_role_ids and child_id_str not in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_add.append(role_obj)
                
                elif booster_role_id not in after_role_ids and child_id_str in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_remove.append(role_obj)
            else:
                if child_id_str in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_remove.append(role_obj)

        if roles_to_add:
            try:
                await after.add_roles(*roles_to_add, reason="Liên kết ngầm: Có Role Booster")
                print(f"[AUTO-ADD] Đã thêm {len(roles_to_add)} role cho {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Quyền của Bot thấp hơn Role cần thêm")
            except Exception as e:
                print(f"[LỖI ADD] {e}")

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
    
