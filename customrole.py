import discord
from discord.ext import commands
import database

class CustomRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Structure: { "guild_id": { "child_role_id": "parent_role_id" } }
        self.role_links = database.load_data()

    # --- CÁC CÂU LỆNH (PREFIX: kb.) ---

    @commands.command(name="link")
    @commands.has_permissions(manage_roles=True)
    async def link_roles(self, ctx, child_role: discord.Role, parent_role: discord.Role):
        """Liên kết: Nếu user KHÔNG CÓ parent_role thì sẽ BỊ GỠ child_role.
        Cú pháp: kb.link <role_bị_phụ_thuộc> <role_điều_kiện>
        """
        guild_id = str(ctx.guild.id)
        if guild_id not in self.role_links:
            self.role_links[guild_id] = {}

        self.role_links[guild_id][str(child_role.id)] = str(parent_role.id)
        
        if database.save_data(self.role_links):
            await ctx.send(f"✅ **Đã liên kết thành công!**\nNếu thành viên không có {parent_role.mention}, họ sẽ tự động bị gỡ {child_role.mention}.")
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi lưu vào Database!")

    @commands.command(name="unlink")
    @commands.has_permissions(manage_roles=True)
    async def unlink_roles(self, ctx, child_role: discord.Role):
        """Hủy liên kết của một role phụ thuộc.
        Cú pháp: kb.unlink <role_bị_phụ_thuộc>
        """
        guild_id = str(ctx.guild.id)
        if guild_id in self.role_links and str(child_role.id) in self.role_links[guild_id]:
            del self.role_links[guild_id][str(child_role.id)]
            database.save_data(self.role_links)
            await ctx.send(f"✅ Đã hủy liên kết cho role {child_role.mention}.")
        else:
            await ctx.send("❌ Role này chưa được thiết lập liên kết nào.")

    @commands.command(name="list")
    async def list_links(self, ctx):
        """Xem danh sách các liên kết role trong server."""
        guild_id = str(ctx.guild.id)
        links = self.role_links.get(guild_id, {})
        
        if not links:
            return await ctx.send("⚠️ Server này chưa thiết lập liên kết role nào.")

        embed = discord.Embed(title="🔗 Danh sách liên kết Role ngầm", color=discord.Color.blue())
        for child_id, parent_id in links.items():
            child_role = ctx.guild.get_role(int(child_id))
            parent_role = ctx.guild.get_role(int(parent_id))
            
            child_name = child_role.mention if child_role else f"ID: {child_id}"
            parent_name = parent_role.mention if parent_role else f"ID: {parent_id}"
            
            embed.add_field(
                name=f"Role: {child_name}", 
                value=f"Yêu cầu phải có: {parent_name}", 
                inline=False
            )
        await ctx.send(embed=embed)

    # --- SỰ KIỆN TỰ ĐỘNG CHECK VÀ GỠ ROLE ---

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Nếu danh sách role không thay đổi thì bỏ qua
        if before.roles == after.roles:
            return

        guild_id = str(after.guild.id)
        guild_links = self.role_links.get(guild_id, {})
        if not guild_links:
            return

        # Tập hợp danh sách Role ID hiện tại của user
        user_role_ids = {str(role.id) for role in after.roles}
        roles_to_remove = []

        for child_id_str, parent_id_str in guild_links.items():
            # Nếu user có Role chỉ định (child) NHƯNG LẠI KHÔNG CÓ Role bắt buộc (parent)
            if child_id_str in user_role_ids and parent_id_str not in user_role_ids:
                role_obj = after.guild.get_role(int(child_id_str))
                if role_obj:
                    roles_to_remove.append(role_obj)

        # Tiến hành gỡ role nếu vi phạm điều kiện
        if roles_to_remove:
            try:
                await after.remove_roles(*roles_to_remove, reason="Liên kết ngầm: Thiếu role bắt buộc")
                print(f"[AUTO-REMOVE] Đã gỡ {len(roles_to_remove)} role từ user {after.display_name}")
            except discord.Forbidden:
                print(f"[LỖI] Bot không đủ quyền (hoặc Vị trí Role của Bot thấp hơn Role cần gỡ) đối với server {after.guild.name}.")
            except Exception as e:
                print(f"[LỖI] Không thể gỡ role: {e}")

async def setup(bot):
    await bot.add_cog(CustomRole(bot))
          
