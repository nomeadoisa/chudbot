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
active_miners = set()

class MineView(discord.ui.View):
    def __init__(self, user, bet, winnings, stage):
        super().__init__(timeout=60.0)
        self.user = user
        self.bet = bet
        self.winnings = winnings
        self.stage = stage

    async def on_timeout(self):
        active_miners.discard(self.user.id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't interfere with someone else's mine!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        active_miners.discard(self.user.id)
        new_bal = db.update_balance(self.user.id, self.winnings)
        await interaction.response.edit_message(content=f"You safely left the mine with **{self.winnings} Chuds**.\nYour new balance is **{new_bal}**.", view=None)
        self.stop()

    @discord.ui.button(label="Dig Deeper", style=discord.ButtonStyle.blurple)
    async def dig(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="*Digging deeper into the mine...*", view=None)
        await asyncio.sleep(1.5)

        chances = {2: 35, 3: 20, 4: 5} 
        multipliers = {2: 3, 3: 5, 4: 10} 
        
        roll = random.randint(1, 100)

        if roll <= chances[self.stage]:
            new_winnings = self.bet * multipliers[self.stage]
            
            if self.stage == 3:
                next_view = MineView(self.user, self.bet, new_winnings, 4)
                next_view.children[1].label = "Double or Nothing (5% Chance)"
                next_view.children[1].style = discord.ButtonStyle.danger
                msg = f" **AWESOME!!!!** You struck a huge vein! You currently have **{new_winnings} Chuds**.\nDo you cash out, or risk it all on a Double or Nothing?"
                await interaction.edit_original_response(content=msg, view=next_view)
            elif self.stage == 4:
                active_miners.discard(self.user.id)
                new_bal = db.update_balance(self.user.id, new_winnings)
                msg = f"**AMAZING!!!!** You beat the impossible odds and survived the deepest depths!\nYou won **{new_winnings} Chuds** and your new balance is **{new_bal}**."
                await interaction.edit_original_response(content=msg, view=None)
            else:
                next_view = MineView(self.user, self.bet, new_winnings, self.stage + 1)
                msg = f"**Great!** You found more valuables! You currently have **{new_winnings} Chuds**.\nKeep going? The caves are getting unstable..."
                await interaction.edit_original_response(content=msg, view=next_view)
        else:
            active_miners.discard(self.user.id)
            await interaction.edit_original_response(content=f"**THE WEST HAS FALLEN.** You got greedy and were buried. You lost **{self.bet} Chuds**.", view=None)

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
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            leaderboard += f"{rank}. {name} - **{score}%**\n"

        await interaction.response.send_message(leaderboard)

    @app_commands.command(name="coalmine", description="Gamble your Chuds in the coal mines. Will you find gems or get buried in the coal?")
    async def coalmine(self, interaction: discord.Interaction, bet: int):
        if interaction.user.id in active_miners:
            await interaction.response.send_message("You are already in the mines! Finish your current run before starting a new one.", ephemeral=True)
            return
        MAX_BET = 500  
        if bet <= 0:
            await interaction.response.send_message("You must bet at least 1 Chud.", ephemeral=True)
            return
        if bet > MAX_BET:
            await interaction.response.send_message(f"The mining corporation limits investments to a maximum of **{MAX_BET} Chuds** per run.", ephemeral=True)
            return
        current_balance = db.get_balance(interaction.user.id)
        if current_balance < bet:
            await interaction.response.send_message(f"You don't have enough Chuds! Your current balance is **{current_balance}**.", ephemeral=True)
            return

        active_miners.add(interaction.user.id)
        db.update_balance(interaction.user.id, -bet)
        
        await interaction.response.send_message("*Beginning to dig in the coal mines, hoping to find something...*")
        await asyncio.sleep(2.0)

        roll = random.randint(1, 100)
        if roll <= 50:
            winnings = bet * 2
            view = MineView(interaction.user, bet, winnings, stage=2)
            await interaction.edit_original_response(
                content=f"**Good!** You found some gems worth **{winnings} Chuds**.\nDo you want to cash out, or risk losing it to dig deeper?",
                view=view
            )
        else:
            active_miners.discard(interaction.user.id)
            await interaction.edit_original_response(content=f"**Epic Fail.** You hit a dead end immediately and lost your **{bet} Chuds**.")

    @app_commands.command(name="daily", description="Claim your daily Chuds and XP! Rewards scale with your Tier.")
    async def daily(self, interaction: discord.Interaction):
        today = datetime.date.today().isoformat()
        
        if not db.check_and_claim_daily(interaction.user.id, today):
            await interaction.response.send_message("You have already claimed your daily rewards today! Come back tomorrow.", ephemeral=True)
            return
            
        profile = db.get_profile(interaction.user.id)
        tier = profile[2] if profile else 1
        
        chuds_reward = tier * 50
        xp_reward = tier * 25
        
        db.update_balance(interaction.user.id, chuds_reward)
        new_tier, leveled_up = db.award_xp(interaction.user.id, xp_reward)
        
        msg = f"You claimed your daily reward.\n**+{chuds_reward} Chuds**\n**+{xp_reward} XP**"
        
        if leveled_up:
            msg += f"\n\nYou are now a **Tier {new_tier} Chud**."
            
        await interaction.response.send_message(msg)

    @app_commands.command(name="award", description="Give Chuds or XP to a user.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(reward_type=[
        app_commands.Choice(name="Chuds", value="chuds"),
        app_commands.Choice(name="XP", value="xp")
    ])
    async def award(self, interaction: discord.Interaction, target: discord.Member, reward_type: app_commands.Choice[str], amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        if reward_type.value == "chuds":
            new_bal = db.update_balance(target.id, amount)
            await interaction.response.send_message(f"Awarded **{amount} Chuds** to {target.mention}. Their new balance is **{new_bal}**.", ephemeral=True)
        else:
            new_tier, leveled_up = db.award_xp(target.id, amount)
            msg = f"Awarded **{amount} XP** to {target.mention}."
            
            await interaction.response.send_message(msg, ephemeral=True)
            
            if leveled_up:
                await interaction.channel.send(f"{target.mention} is now a **Tier {new_tier} Chud** from an admin grant.")

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