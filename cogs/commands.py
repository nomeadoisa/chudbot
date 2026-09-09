import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import sqlite3

role_id = 1466979676139557082 
threshold = 70

class ChudCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('database.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER PRIMARY KEY,
                date TEXT,
                score INTEGER
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="chudometer", description="Rates how chuddy someone is today (0-100%).")
    async def chudometer(self, interaction: discord.Interaction, target: discord.Member = None):
        target = target or interaction.user
        today = datetime.date.today().isoformat()
        
        self.cursor.execute('SELECT date, score FROM ratings WHERE user_id = ?', (target.id,))
        result = self.cursor.fetchone()
        
        if result:
            last_date, previous_score = result
            if last_date == today:
                await interaction.response.send_message(
                    f"{target.mention} has already been rated today! They are **{previous_score}%** chuddy.", 
                    ephemeral=True
                )
                return

        score = random.randint(0, 100)
        
        self.cursor.execute('''
            REPLACE INTO ratings (user_id, date, score) 
            VALUES (?, ?, ?)
        ''', (target.id, today, score))
        self.conn.commit()
        
        response_msg = f"The Chudometer determines that {target.mention} is **{score}%** chuddy today."

        if score >= CHUD_THRESHOLD:
            role = interaction.guild.get_role(CHUD_ROLE_ID)
            if role:
                try:
                    await target.add_roles(role)
                    response_msg += f"\n\nThey surpassed the threshold and earned the **{role.name}** role!"
                except discord.Forbidden:
                    response_msg += "\n\n*(I couldn't assign the role! Make sure my Bot role is placed HIGHER than the Chud role in server settings).*"

        await interaction.response.send_message(response_msg)

    @app_commands.command(name="chudboard", description="Shows the highest chud scores of the day.")
    async def chudboard(self, interaction: discord.Interaction):
        today = datetime.date.today().isoformat()
        
        self.cursor.execute('SELECT user_id, score FROM ratings WHERE date = ? ORDER BY score DESC', (today,))
        todays_scores = self.cursor.fetchall()
        
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
        self.cursor.execute('DELETE FROM ratings WHERE user_id = ?', (target.id,))
        self.conn.commit()
        
        role = interaction.guild.get_role(CHUD_ROLE_ID)
        msg = f"{target.mention}'s chud status has been completely cleared for today."
        
        if role and role in target.roles:
            try:
                await target.remove_roles(role)
                msg += f" The **{role.name}** role was removed."
            except discord.Forbidden:
                msg += " *(Failed to remove role due to permissions).*"
                
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChudCommands(bot))
