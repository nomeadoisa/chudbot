import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import asyncio
from .db import Database

db = Database()
fishing_cooldowns = {}

BOAT_DATA = {
    1: {"name": "Inflatable Pool Float Held Together With Duct Tape", "cost": 0, "weights": [50, 30, 15, 4, 1, 0, 0, 0, 0, 0]},
    2: {"name": "A Shopping Cart Strapped to Four Empty 2-Liters", "cost": 750, "weights": [35, 30, 20, 10, 4, 1, 0, 0, 0, 0]},
    3: {"name": "The Zaltronator", "cost": 3500, "weights": [20, 25, 25, 15, 10, 3, 1, 1, 0, 0]},
    4: {"name": "DEAXS ADVENTURE branded Boat", "cost": 12000, "weights": [10, 15, 20, 20, 15, 10, 5, 3, 1, 1]}
}

ROD_DATA = {
    1: {"name": "Plastic Stick", "cost": 0, "cooldown": 900},
    2: {"name": "Reinforced PVC Rod", "cost": 500, "cooldown": 600},
    3: {"name": "Magnetic Scrap Rod", "cost": 2500, "cooldown": 300},
    4: {"name": "Quantum Radioactive Harpoon", "cost": 8000, "cooldown": 120}
}

LURE_DATA = {
    1: {"name": "No Bait", "cost": 0, "luck": 0},
    2: {"name": "Soggy Bread", "cost": 1000, "luck": 15},
    3: {"name": "Radioactive Poster of Lasdav (The Adventure one)", "cost": 4000, "luck": 30},
    4: {"name": "The Master Bait", "cost": 15000, "luck": 50}
}

FISH_TYPES = [
    ("A Single Wet Sock", 3, 5),
    ("Half-Eaten Gas Station Sushi", 8, 12),
    ("Feral Raccoon Wearing Crocs", 25, 40),
    ("Sentient Vaper Cloud", 50, 75),
    ("Gamer Fuel Canister", 120, 180),
    ("An Entirely Unopened Box of Pizza Rolls (Specifically from like, Lil' Cesars or something)", 220, 310),
    ("The Box", 350, 500),
    ("Just Genuinely a Comically Large Fish", 450, 700),
    ("The Ghost of Harambe", 700, 1050),
    ("The Chud", 1000, 1500)
]

class ShopSelect(discord.ui.Select):
    def __init__(self, upgrade_type: str, current_level: int, data_dict: dict, placeholder_text: str):
        self.upgrade_type = upgrade_type
        self.data_dict = data_dict
        
        options = []
        for lvl, data in data_dict.items():
            if lvl > current_level:
                options.append(discord.SelectOption(
                    label=f"Tier {lvl}: {data['name']}",
                    description=f"Cost: {data['cost']:,} Chuds",
                    value=str(lvl)
                ))
                
        if not options:
            options.append(discord.SelectOption(label="Max Tier Reached", value="max"))
            super().__init__(placeholder=placeholder_text, min_values=1, max_values=1, options=options, disabled=True)
        else:
            super().__init__(placeholder=placeholder_text, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: BoatShopView = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("Not your shop menu!", ephemeral=True)
            return
            
        target_level = int(self.values[0])
        await view.process_purchase(interaction, self.upgrade_type, target_level, self.data_dict)

class BoatShopView(discord.ui.View):
    def __init__(self, user_id, boat_lvl, rod_lvl, lure_lvl):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        
        self.add_item(ShopSelect("boat", boat_lvl, BOAT_DATA, "Select a Vessel to Buy..."))
        self.add_item(ShopSelect("rod", rod_lvl, ROD_DATA, "Select a Rod to Buy..."))
        self.add_item(ShopSelect("lure", lure_lvl, LURE_DATA, "Select Bait to Buy..."))

    async def process_purchase(self, interaction: discord.Interaction, upgrade_type: str, target_level: int, data_dict: dict):
        cost = data_dict[target_level]["cost"]
        name = data_dict[target_level]["name"]
        
        bal = db.get_balance(self.user_id)
        if bal < cost:
            await interaction.response.send_message(f"You don't have enough Chuds. You need **{cost:,} Chuds**.", ephemeral=True)
            return
            
        db.update_balance(self.user_id, -cost)
        
        if upgrade_type == "boat":
            db.update_boat_level(self.user_id, target_level)
        elif upgrade_type == "rod":
            db.update_rod_level(self.user_id, target_level)
        else:
            db.update_lure_level(self.user_id, target_level)

        await interaction.response.edit_message(content=f"You purchased **{name}**.", view=None)

class FishingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fish", description="Cast your line out into the waters to scavenge items and earn XP.")
    async def fish(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.datetime.now().timestamp()
        
        boat_lvl, rod_lvl, lure_lvl = db.get_fishing_stats(user_id)
        cooldown_time = ROD_DATA[rod_lvl]["cooldown"]

        if user_id in fishing_cooldowns and now < fishing_cooldowns[user_id]:
            remaining = int(fishing_cooldowns[user_id] - now)
            await interaction.response.send_message(f"You're tired! Wait {remaining // 60}m {remaining % 60}s before fishing again.", ephemeral=True)
            return
            
        fishing_cooldowns[user_id] = now + cooldown_time
        
        boat_name = BOAT_DATA[boat_lvl]['name']
        rod_name = ROD_DATA[rod_lvl]['name']
        
        suspense_msg = f"You sail into the ocean driving the **{boat_name}** as you cast your **{rod_name}** and hope you get something good..."
        await interaction.response.send_message(suspense_msg)
        
        await asyncio.sleep(2.5)

        weights = BOAT_DATA[boat_lvl]["weights"]
        catch_idx = random.choices(range(10), weights=weights)[0]
        
        luck_chance = LURE_DATA[lure_lvl]["luck"]
        luck_triggered = False
        
        if catch_idx < 9 and random.randint(1, 100) <= luck_chance:
            catch_idx += 1
            luck_triggered = True

        fish = FISH_TYPES[catch_idx]
        db.add_fish(user_id, fish[0], fish[1], fish[2])
        new_tier, leveled_up = db.award_xp(user_id, fish[2])
        
        if fish[0] == "The Chud":
            final_text = f"You caught The Chud. (Worth {fish[1]} Chuds and {fish[2]} XP)"
        else:
            final_text = f"CAUGHT!! You got **{fish[0]}**. (Worth {fish[1]} Chuds and {fish[2]} XP)"

        if luck_triggered:
            final_text += f"\n*Your {LURE_DATA[lure_lvl]['name']} attracted a rarer catch*!"

        msg = f"{suspense_msg}\n\n{final_text}"
        
        if leveled_up:
            msg += f"\nYou are now a **Tier {new_tier} Chud**."
            
        await interaction.edit_original_response(content=msg)

    @app_commands.command(name="inventory", description="Check your caught fish inventory.")
    async def inventory(self, interaction: discord.Interaction):
        fish_list = db.get_inventory(interaction.user.id)
        if not fish_list:
            await interaction.response.send_message("Your fishing bucket is empty! Use `/fish` to catch something.", ephemeral=True)
            return
            
        desc = ""
        total_value = 0
        for _, name, chuds, xp in fish_list:
            desc += f"• {name} (Worth {chuds} Chuds and {xp} XP)\n"
            total_value += chuds
            
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Fishing Haul", description=desc, color=discord.Color.dark_green())
        embed.set_footer(text=f"Total Value: {total_value} Chuds. Use /sellfish to cash out.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sellfish", description="Sell your caught items.")
    @app_commands.describe(fish_name="Leave blank to sell ALL, or type a specific fish name to sell only that type.")
    async def sellfish(self, interaction: discord.Interaction, fish_name: str = None):
        if fish_name:
            total_chuds = db.sell_specific_fish(interaction.user.id, fish_name)
            if total_chuds == 0:
                await interaction.response.send_message(f"You don't have any '{fish_name}' in your bucket to sell.", ephemeral=True)
                return
            new_bal = db.update_balance(interaction.user.id, total_chuds)
            await interaction.response.send_message(f"You successfully sold all your **{fish_name}** for **{total_chuds} Chuds**.Your new balance is **{new_bal}**.")
        else:
            fish_list = db.get_inventory(interaction.user.id)
            if not fish_list:
                await interaction.response.send_message("You have no items in your bucket to sell.", ephemeral=True)
                return
                
            total_chuds = sum(item[2] for item in fish_list)
            db.clear_inventory(interaction.user.id)
            new_bal = db.update_balance(interaction.user.id, total_chuds)
            await interaction.response.send_message(f"You successfully sold your entire catch for **{total_chuds} Chuds**! Your new balance is **{new_bal}**.")

    @app_commands.command(name="boatshop", description="Upgrade your vessel or gear.")
    async def boatshop(self, interaction: discord.Interaction):
        boat_lvl, rod_lvl, lure_lvl = db.get_fishing_stats(interaction.user.id)
        
        embed = discord.Embed(
            title="The Shop", 
            description="Use the dropdown menus below to directly select the tier you want to buy.\nYou do not have to buy all of them. Just the highest tier one you want, for example.",
            color=discord.Color.blue()
        )
        
        boat_desc = ""
        for lvl, data in BOAT_DATA.items():
            status = "Owned" if boat_lvl >= lvl else f"{data['cost']:,} Chuds"
            if lvl == boat_lvl:
                status += " **(Current)**"
            boat_desc += f"**Lvl {lvl}: {data['name']}** - {status}\n"
        embed.add_field(name="Vessels (Better fish drops)", value=boat_desc, inline=False)

        rod_desc = ""
        for lvl, data in ROD_DATA.items():
            status = "Owned" if rod_lvl >= lvl else f"{data['cost']:,} Chuds"
            if lvl == rod_lvl:
                status += " **(Current)**"
            rod_desc += f"**Lvl {lvl}: {data['name']}** ({int(data['cooldown']/60)}m cooldown) - {status}\n"
        embed.add_field(name="Rods (Faster cooldown)", value=rod_desc, inline=False)

        lure_desc = ""
        for lvl, data in LURE_DATA.items():
            status = "Owned" if lure_lvl >= lvl else f"{data['cost']:,} Chuds"
            if lvl == lure_lvl:
                status += " **(Current)**"
            lure_desc += f"**Lvl {lvl}: {data['name']}** ({data['luck']}% luck chance) - {status}\n"
        embed.add_field(name="Bait (Better luck chance)", value=lure_desc, inline=False)

        view = BoatShopView(interaction.user.id, boat_lvl, rod_lvl, lure_lvl)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FishingCommands(bot))