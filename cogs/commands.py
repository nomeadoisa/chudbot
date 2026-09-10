import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import psutil
import os
from .db import Database

role_id = 1466979676139557082 
threshold = 70

db = Database()

class ChudCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.now()

    @app_commands.command(name="chudometer", description="Rates how chuddy someone is today (0-100%).")
    async def chudometer(self, interaction: discord.Interaction, target: discord.Member = None):
        target = target or interaction.user
        today = datetime.date.today().isoformat()
        
        db.cursor.execute('SELECT date, score FROM ratings WHERE user_id = ?', (target.id,))
        result = db.cursor.fetchone()
        
        if result:
            last_date, previous_score = result
            if last_date == today:
                await interaction.response.send_message(
                    f"{target.mention} has already been rated today! They are **{previous_score}%** chuddy.", 
                    ephemeral=True
                )
                return

        score = random.randint(0, 100)
        
        db.cursor.execute('''
            REPLACE INTO ratings (user_id, date, score) 
            VALUES (?, ?, ?)
        ''', (target.id, today, score))
        db.conn.commit()
        
        response_msg = f"The Chudometer determines that {target.mention} is **{score}%** chuddy today."

        if score >= threshold:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await target.add_roles(role)
                    response_msg += f"\n\nThey surpassed the threshold and earned the **{role.name}** role."
                except discord.Forbidden:
                    response_msg += "\n\n*(I couldn't assign the role! Make sure my Bot role is placed HIGHER than the Chud role in server settings).*"

        await interaction.response.send_message(response_msg)
        
        new_tier, leveled_up = db.award_xp(target.id, 150)
        if leveled_up:
            await interaction.channel.send(f"{interaction.user.mention} is now a Tier {new_tier} Chud.")

    @app_commands.command(name="chudboard", description="Shows the highest chud scores of the day.")
    async def chudboard(self, interaction: discord.Interaction):
        today = datetime.date.today().isoformat()
        
        db.cursor.execute('SELECT user_id, score FROM ratings WHERE date = ? ORDER BY score DESC', (today,))
        todays_scores = db.cursor.fetchall()
        
        if not todays_scores:
            await interaction.response.send_message("No one has used the chudometer today.")
            return

        leaderboard = "**Today's Top Chuds**\n"
        for rank, (user_id, score) in enumerate(todays_scores, start=1):
            leaderboard += f"{rank}. <@{user_id}> - **{score}%**\n"

        await interaction.response.send_message(leaderboard)

    @app_commands.command(name="unchud", description="Resets a user's chud-rating and removes their role.")
    @app_commands.default_permissions(administrator=True)
    async def unchud(self, interaction: discord.Interaction, target: discord.Member):
        db.cursor.execute('DELETE FROM ratings WHERE user_id = ?', (target.id,))
        db.conn.commit()
        
        role = interaction.guild.get_role(role_id)
        msg = f"{target.mention}'s chud status has been completely cleared for today."
        
        if role and role in target.roles:
            try:
                await target.remove_roles(role)
                msg += f" The **{role.name}** role was removed."
            except discord.Forbidden:
                msg += " *(Failed to remove role due to permissions).*"
                
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="stats", description="Shows bot runtime, memory, and next reset time.")
    async def stats(self, interaction: discord.Interaction):
        uptime_delta = datetime.datetime.now() - self.start_time
        uptime_str = str(uptime_delta).split('.')[0] 

        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 ** 2)

        now = datetime.datetime.now().astimezone()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        midnight_ts = int(midnight.timestamp())
        tz_name = now.tzname()

        stats_msg = (
            f"**Bot Statistics**\n"
            f"**Uptime:** {uptime_str}\n"
            f"**Memory Usage:** {mem_mb:.2f} MB\n"
            f"**Server Timezone:** {tz_name}\n"
            f"**Next Daily Reset:** <t:{midnight_ts}:R> (which is <t:{midnight_ts}:t> your time)"
        )
        
        await interaction.response.send_message(stats_msg)

    @app_commands.command(name="profile", description="Check your current Tier and Chuds balance.")
    async def profile(self, interaction: discord.Interaction):
        result = db.get_profile(interaction.user.id)
        
        if not result:
            await interaction.response.send_message("You don't have a profile yet! Use `/chudometer` to earn some XP.", ephemeral=True)
            return
            
        balance, xp, tier = result
        
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Profile", color=discord.Color.blue())
        embed.add_field(name="Level", value=f"**Tier {tier} Chud**", inline=False)
        embed.add_field(name="Experience", value=f"{xp} XP", inline=True)
        embed.add_field(name="Wallet", value=f"{balance} Chuds", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ChudCommands(bot))