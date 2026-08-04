import asyncio
import discord
from discord.ext import commands
import database

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = database.load_data()

    # --- CÁC CÂU LỆNH (PREFIX: kb.) ---

    @commands.command(name="link")
    @commands.has_permissions(manage_roles=True)
    async def link_roles(self, ctx, child_role: discord.Role, parent_role: discord.Role):
        """Liên kết: Thiếu parent_role -> Gỡ child_role. Thêm parent_role -> Thêm child_role.
        Cú pháp: kb.link <role_custom> <role_điều_kiện>
        """
        guild_id = str(ctx.guild.id)
        if guild_id not in self.db["links"]:
            self.db["links"][guild_id] = {}

        self.db["links"][guild_id][str(child_role.id)] = str(parent_role.id)
        
        success = await asyncio.to_thread(database.save_data, self.db)
        if success:
            await ctx.send(
                f"✅ **Đã liên kết thành công!**\n"
                f"- Bị gỡ {parent_role.mention} ➔ Tự động gỡ {child_role.mention}.\n"
                f"- Được thêm {parent_role.mention} ➔ Tự động cấp {child_role.mention}."
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi lưu vào Database Gist!")

    @commands.command(name="unlink")
    @commands.has_permissions(manage_roles=True)
    async def unlink_roles(self, ctx, child_role: discord.Role):
        """Hủy liên kết của một role custom."""
        guild_id = str(ctx.guild.id)
        if guild_id in self.db["links"] and str(child_role.id) in self.db["links"][guild_id]:
            del self.db["links"][guild_id][str(child_role.id)]
            await asyncio.to_thread(database.save_data, self.db)
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
                name=f"Role Custom: {child_name}", 
                value=f"Yêu cầu có Role: {parent_name}", 
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="restore")
    @commands.has_permissions(manage_roles=True)
    async def restore_roles(self, ctx, member: discord.Member = None):
        """Quét và cấp lại role custom cho những ai đã có role điều kiện."""
        guild_id = str(ctx.guild.id)
        guild_links = self.db["links"].get(guild_id, {})

        if not guild_links:
            return await ctx.send("⚠️ Chưa có thiết lập liên kết role nào.")

        target_members = [member] if member else ctx.guild.members
        restored_count = 0

        for target in target_members:
            user_role_ids = {str(r.id) for r in target.roles}
            to_add = []

            for child_id_str, parent_id_str in guild_links.items():
                # Nếu có role điều kiện nhưng chưa có role custom -> Cấp bổ sung
                if parent_id_str in user_role_ids and child_id_str not in user_role_ids:
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

    # --- SỰ KIỆN THEO DÕI THAY ĐỔI ROLE ---

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_role_ids = {str(r.id) for r in before.roles}
        after_role_ids = {str(r.id) for r in after.roles}

        # Nếu không có thay đổi về role thì bỏ qua
        if before_role_ids == after_role_ids:
            return

        guild_id = str(after.guild.id)
        guild_links = self.db["links"].get(guild_id, {})
        if not guild_links:
            return

        roles_to_remove = []
        roles_to_add = []

        # Các role vừa được THÊM vào user trong lần update này
        added_role_ids = after_role_ids - before_role_ids

        for child_id_str, parent_id_str in guild_links.items():
            # THƯỜNG HỢP 1: Bị gỡ/không có Role điều kiện -> Gỡ Role Custom
            if child_id_str in after_role_ids and parent_id_str not in after_role_ids:
                role_obj = after.guild.get_role(int(child_id_str))
                if role_obj:
                    roles_to_remove.append(role_obj)

            # TRƯỜNG HỢP 2: Vừa nhận được Role điều kiện -> Thêm Role Custom
            if parent_id_str in added_role_ids:
                if child_id_str not in after_role_ids:
                    role_obj = after.guild.get_role(int(child_id_str))
                    if role_obj:
                        roles_to_add.append(role_obj)

        # Thực thi gỡ role
        if roles_to_remove:
            try:
                await after.remove_roles(*roles_to_remove, reason="Liên kết ngầm: Mất role điều kiện")
                print(f"[AUTO-REMOVE] Đã gỡ {len(roles_to_remove)} role từ {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Quyền của Bot thấp hơn Role cần gỡ tại server {after.guild.name}")
            except Exception as e:
                print(f"[LỖI REMOVE] {e}")

        # Thực thi thêm lại role
        if roles_to_add:
            try:
                await after.add_roles(*roles_to_add, reason="Liên kết ngầm: Đã nhận role điều kiện")
                print(f"[AUTO-ADD] Đã thêm {len(roles_to_add)} role cho {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Quyền của Bot thấp hơn Role cần thêm tại server {after.guild.name}")
            except Exception as e:
                print(f"[LỖI ADD] {e}")

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
        
