import discord
from discord.ext import commands
import database

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # db structure: { "links": {...}, "history": {...} }
        self.db = database.load_data()

    # --- CÁC CÂU LỆNH (PREFIX: kb.) ---

    @commands.command(name="link")
    @commands.has_permissions(manage_roles=True)
    async def link_roles(self, ctx, child_role: discord.Role, parent_role: discord.Role):
        """Liên kết: Nếu KHÔNG CÓ parent_role -> Gỡ child_role. Nếu CÓ LẠI -> Thêm lại child_role.
        Cú pháp: kb.link <role_bị_phụ_thuộc> <role_điều_kiện>
        """
        guild_id = str(ctx.guild.id)
        if guild_id not in self.db["links"]:
            self.db["links"][guild_id] = {}

        self.db["links"][guild_id][str(child_role.id)] = str(parent_role.id)
        
        if database.save_data(self.db):
            await ctx.send(
                f"✅ **Đã liên kết thành công!**\n"
                f"- Nếu thiếu {parent_role.mention} ➔ Tự động gỡ {child_role.mention}.\n"
                f"- Khi có lại {parent_role.mention} ➔ Tự động cấp lại {child_role.mention}."
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi lưu vào Database!")

    @commands.command(name="unlink")
    @commands.has_permissions(manage_roles=True)
    async def unlink_roles(self, ctx, child_role: discord.Role):
        """Hủy liên kết của một role phụ thuộc.
        Cú pháp: kb.unlink <role_bị_phụ_thuộc>
        """
        guild_id = str(ctx.guild.id)
        if guild_id in self.db["links"] and str(child_role.id) in self.db["links"][guild_id]:
            del self.db["links"][guild_id][str(child_role.id)]
            database.save_data(self.db)
            await ctx.send(f"✅ Đã hủy liên kết cho role {child_role.mention}.")
        else:
            await ctx.send("❌ Role này chưa được thiết lập liên kết nào.")

    @commands.command(name="list")
    async def list_links(self, ctx):
        """Xem danh sách các liên kết role trong server."""
        guild_id = str(ctx.guild.id)
        links = self.db["links"].get(guild_id, {})
        
        if not links:
            return await ctx.send("⚠️ Server này chưa thiết lập liên kết role nào.")

        embed = discord.Embed(title="🔗 Danh sách liên kết Role ngầm", color=discord.Color.blue())
        for child_id, parent_id in links.items():
            child_role = ctx.guild.get_role(int(child_id))
            parent_role = ctx.guild.get_role(int(parent_id))
            
            child_name = child_role.mention if child_role else f"ID: {child_id}"
            parent_name = parent_role.mention if parent_role else f"ID: {parent_id}"
            
            embed.add_field(
                name=f"Role phụ thuộc: {child_name}", 
                value=f"Yêu cầu phải có: {parent_name}", 
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="restore")
    @commands.has_permissions(manage_roles=True)
    async def restore_roles(self, ctx, member: discord.Member = None):
        """Khôi phục thủ công role bị gỡ cho 1 người hoặc toàn bộ server.
        Cú pháp: 
          - kb.restore @User (khôi phục cho 1 người)
          - kb.restore (quét và khôi phục toàn server)
        """
        guild_id = str(ctx.guild.id)
        guild_links = self.db["links"].get(guild_id, {})
        guild_history = self.db["history"].get(guild_id, {})

        if not guild_links or not guild_history:
            return await ctx.send("⚠️ Không có lịch sử role bị gỡ nào cần khôi phục.")

        target_members = [member] if member else ctx.guild.members
        restored_count = 0

        for target in target_members:
            user_id = str(target.id)
            user_history = guild_history.get(user_id, [])
            if not user_history:
                continue

            user_role_ids = {str(r.id) for r in target.roles}
            to_add = []

            for child_id_str in list(user_history):
                parent_id_str = guild_links.get(child_id_str)
                # Điều kiện khôi phục: Có parent_role và hiện chưa có child_role
                if parent_id_str and parent_id_str in user_role_ids:
                    role_obj = ctx.guild.get_role(int(child_id_str))
                    if role_obj and role_obj not in target.roles:
                        to_add.append(role_obj)
                    user_history.remove(child_id_str)

            if to_add:
                try:
                    await target.add_roles(*to_add, reason="Khôi phục role thủ công bằng lệnh kb.restore")
                    restored_count += len(to_add)
                except discord.Forbidden:
                    await ctx.send(f"❌ Khuyết quyền thêm role cho {target.mention}")

            self.db["history"][guild_id][user_id] = user_history

        database.save_data(self.db)

        if member:
            await ctx.send(f"✅ Đã kiểm tra và khôi phục {restored_count} role cho {member.mention}.")
        else:
            await ctx.send(f"✅ Đã quét toàn server và khôi phục tổng cộng {restored_count} role.")

    # --- SỰ KIỆN TỰ ĐỘNG GỠ VÀ THÊM LẠI ROLE ---

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles == after.roles:
            return

        guild_id = str(after.guild.id)
        user_id = str(after.id)

        guild_links = self.db["links"].get(guild_id, {})
        if not guild_links:
            return

        if guild_id not in self.db["history"]:
            self.db["history"][guild_id] = {}

        user_history = self.db["history"][guild_id].get(user_id, [])
        user_role_ids = {str(role.id) for role in after.roles}

        roles_to_remove = []
        roles_to_add = []
        history_updated = False

        # 1. TỰ ĐỘNG GỠ ROLE (Nếu mất role điều kiện)
        for child_id_str, parent_id_str in guild_links.items():
            if child_id_str in user_role_ids and parent_id_str not in user_role_ids:
                role_obj = after.guild.get_role(int(child_id_str))
                if role_obj:
                    roles_to_remove.append(role_obj)
                    if child_id_str not in user_history:
                        user_history.append(child_id_str)
                        history_updated = True

        # 2. TỰ ĐỘNG THÊM LẠI ROLE (Khi nhận lại role điều kiện)
        for child_id_str in list(user_history):
            parent_id_str = guild_links.get(child_id_str)
            if parent_id_str:
                # Nếu đã có parent_role trở lại và chưa có child_role
                if parent_id_str in user_role_ids and child_id_str not in user_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_add.append(role_obj)
                        user_history.remove(child_id_str)
                        history_updated = True
                # Trường hợp user được cấp thủ công child_role -> Xóa khỏi lịch sử chờ
                elif child_id_str in user_role_ids:
                    user_history.remove(child_id_str)
                    history_updated = True

        # Cập nhật DB nếu lịch sử thay đổi
        self.db["history"][guild_id][user_id] = user_history
        if history_updated:
            database.save_data(self.db)

        # Thực thi gỡ role
        if roles_to_remove:
            try:
                await after.remove_roles(*roles_to_remove, reason="Liên kết ngầm: Thiếu role bắt buộc")
                print(f"[AUTO-REMOVE] Đã gỡ {len(roles_to_remove)} role từ {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Khuyết quyền gỡ role ở server {after.guild.name}")
            except Exception as e:
                print(f"[LỖI] Gỡ role thất bại: {e}")

        # Thực thi thêm lại role
        if roles_to_add:
            try:
                await after.add_roles(*roles_to_add, reason="Liên kết ngầm: Đã có lại role bắt buộc")
                print(f"[AUTO-ADD] Đã thêm lại {len(roles_to_add)} role cho {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Khuyết quyền cấp lại role ở server {after.guild.name}")
            except Exception as e:
                print(f"[LỖI] Cấp lại role thất bại: {e}")

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
                            
