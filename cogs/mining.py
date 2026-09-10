import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from .db import Database

db = Database()

active_miners = {}

class MineView(discord.ui.View):
    def __init__(self, user, bet, winnings, stage):
        super().__init__(timeout=60.0)
        self.user = user
        self.bet = bet
        self.winnings = winnings
        self.stage = stage

    async def on_timeout(self):
        active_miners.pop(self.user.id, None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't interfere with someone else's mine!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        active_miners.pop(self.user.id, None)
        new_bal = db.update_balance(self.user.id, self.winnings)
        db.update_mine_funds(-self.winnings) 
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
                active_miners.pop(self.user.id, None)
                new_bal = db.update_balance(self.user.id, new_winnings)
                db.update_mine_funds(-new_winnings) 
                msg = f"**AMAZING!!!!** You beat the impossible odds and survived the deepest depths!\nYou won **{new_winnings} Chuds** and your new balance is **{new_bal}**."
                await interaction.edit_original_response(content=msg, view=None)
            else:
                next_view = MineView(self.user, self.bet, new_winnings, self.stage + 1)
                msg = f"**Great!** You found more valuables! You currently have **{new_winnings} Chuds**.\nKeep going? The caves are getting unstable..."
                await interaction.edit_original_response(content=msg, view=next_view)
        else:
            active_miners.pop(self.user.id, None)
            await interaction.edit_original_response(content=f"**THE WEST HAS FALLEN.** You got greedy and were buried. You lost **{self.bet} Chuds**.", view=None)


class MiningCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cancel_active_mines(self):
        for user_id, session in active_miners.items():
            db.update_balance(user_id, session['bet'])
            db.update_mine_funds(-session['bet'])

            view = session['view']
            if view:
                for item in view.children:
                    item.disabled = True
                try:
                    await session['interaction'].edit_original_response(
                        content="**System Restarting.** The caves collapsed during maintenance. Your bet has been fully refunded.",
                        view=view
                    )
                except:
                    pass
        active_miners.clear()

    @app_commands.command(name="coalstatus", description="Check how many Chuds are currently stored in the reserves of the mine.")
    async def coalstatus(self, interaction: discord.Interaction):
        funds = db.get_mine_funds()
        max_bet = int(funds * 0.05)
        await interaction.response.send_message(f"**The Coal Mine Reserves**\nCurrent Pool: **{funds} Chuds**\nCurrent Max Bet: **{max_bet} Chuds**\nMaximum bet is 5% of the total reserves.")

    @app_commands.command(name="coalmine", description="Gamble your Chuds. Max bet scales with the global reserve.")
    async def coalmine(self, interaction: discord.Interaction, bet: int):
        if interaction.user.id in active_miners:
            await interaction.response.send_message("You are already in the mines! Finish your current run before starting a new one.", ephemeral=True)
            return

        mine_funds = db.get_mine_funds()
        max_bet = int(mine_funds * 0.05)  

        if bet <= 0:
            await interaction.response.send_message("You must bet at least 1 Chud.", ephemeral=True)
            return
        if bet > max_bet:
            await interaction.response.send_message(f"The mining corporation limits investments to a maximum of **{max_bet} Chuds** based on current reserves.", ephemeral=True)
            return
            
        current_balance = db.get_balance(interaction.user.id)
        if current_balance < bet:
            await interaction.response.send_message(f"You don't have enough Chuds! Your current balance is **{current_balance}**.", ephemeral=True)
            return

        active_miners[interaction.user.id] = {'bet': bet, 'interaction': interaction, 'view': None}
        
        db.update_balance(interaction.user.id, -bet)
        db.update_mine_funds(bet)
        
        await interaction.response.send_message("*Beginning to dig in the coal mines, hoping to find something...*")
        await asyncio.sleep(2.0)

        roll = random.randint(1, 100)
        if roll <= 50:
            winnings = bet * 2
            view = MineView(interaction.user, bet, winnings, stage=2)

            active_miners[interaction.user.id]['view'] = view

            await interaction.edit_original_response(
                content=f"**Good!** You found some gems worth **{winnings} Chuds**.\nDo you want to cash out, or risk losing it to dig deeper?",
                view=view
            )
        else:
            active_miners.pop(interaction.user.id, None)
            await interaction.edit_original_response(content=f"**Epic Fail.** You hit a dead end immediately and lost your **{bet} Chuds**.")

async def setup(bot):
    await bot.add_cog(MiningCommands(bot))