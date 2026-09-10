import sqlite3
from unittest import result

class Database:
    def __init__(self, db_path='database.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._setup_tables()

    def _setup_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER PRIMARY KEY, date TEXT, score INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, tier INTEGER DEFAULT 1)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS daily_claims (user_id INTEGER PRIMARY KEY, last_claim TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS server_economy (mine_funds INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS user_boats (user_id INTEGER PRIMARY KEY, boat_level INTEGER DEFAULT 1, rod_level INTEGER DEFAULT 1, lure_level INTEGER DEFAULT 1)''')
        
        try:
            self.cursor.execute('ALTER TABLE user_boats ADD COLUMN lure_level INTEGER DEFAULT 1')
        except sqlite3.OperationalError:
            pass 
            
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS fish_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            fish_name TEXT, 
            chud_value INTEGER, 
            xp_value INTEGER
        )''')
        self.cursor.execute('SELECT mine_funds FROM server_economy')
        if not self.cursor.fetchone():
            self.cursor.execute('INSERT INTO server_economy (mine_funds) VALUES (10000)')
            
        self.conn.commit()

    def get_mine_funds(self):
        self.cursor.execute('SELECT mine_funds FROM server_economy')
        return self.cursor.fetchone()[0]

    def update_mine_funds(self, amount: int):
        current_funds = self.get_mine_funds()
        new_funds = current_funds + amount
        
        if new_funds < 5000:
            new_funds = 5000
            
        self.cursor.execute('UPDATE server_economy SET mine_funds = ?', (new_funds,))
        self.conn.commit()
        return new_funds

    def check_and_claim_daily(self, user_id: int, today: str):
        self.cursor.execute('SELECT last_claim FROM daily_claims WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        if result and result[0] == today:
            return False 
            
        self.cursor.execute('REPLACE INTO daily_claims (user_id, last_claim) VALUES (?, ?)', (user_id, today))
        self.conn.commit()
        return True

    def award_xp(self, user_id: int, amount: int = 10):
        self.cursor.execute('SELECT xp, tier FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        if not result:
            self.cursor.execute('INSERT INTO users (user_id, balance, xp, tier) VALUES (?, 0, ?, 1)', (user_id, amount))
            self.conn.commit()
            return 1, False 
            
        old_xp, old_tier = result
        new_xp = old_xp + amount
        new_tier = min(10, int((new_xp / 1235) ** 0.5) + 1)
        
        self.cursor.execute('UPDATE users SET xp = ?, tier = ? WHERE user_id = ?', (new_xp, new_tier, user_id))
        self.conn.commit()
        return new_tier, new_tier > old_tier
    
    def get_balance(self, user_id: int):
        self.cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def update_balance(self, user_id: int, amount: int):
        self.cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        
        if not result:
            new_balance = max(0, amount)
            self.cursor.execute('INSERT INTO users (user_id, balance, xp, tier) VALUES (?, ?, 0, 1)', (user_id, new_balance))
        else:
            new_balance = max(0, result[0] + amount)
            self.cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
            
        self.conn.commit()
        return new_balance

    def get_profile(self, user_id: int):
        self.cursor.execute('SELECT balance, xp, tier FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()

    def get_fishing_stats(self, user_id: int):
        self.cursor.execute('SELECT boat_level, rod_level, lure_level FROM user_boats WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        if not result:
            self.cursor.execute('INSERT INTO user_boats (user_id, boat_level, rod_level, lure_level) VALUES (?, 1, 1, 1)', (user_id,))
            self.conn.commit()
            return 1, 1, 1
        return result[0], result[1], result[2]

    def update_boat_level(self, user_id: int, level: int):
        self.cursor.execute('UPDATE user_boats SET boat_level = ? WHERE user_id = ?', (level, user_id))
        self.conn.commit()

    def update_rod_level(self, user_id: int, level: int):
        self.cursor.execute('UPDATE user_boats SET rod_level = ? WHERE user_id = ?', (level, user_id))
        self.conn.commit()

    def update_lure_level(self, user_id: int, level: int):
        self.cursor.execute('UPDATE user_boats SET lure_level = ? WHERE user_id = ?', (level, user_id))
        self.conn.commit()

    def add_fish(self, user_id: int, name: str, chuds: int, xp: int):
        self.cursor.execute('INSERT INTO fish_inventory (user_id, fish_name, chud_value, xp_value) VALUES (?, ?, ?, ?)', (user_id, name, chuds, xp))
        self.conn.commit()

    def sell_specific_fish(self, user_id: int, fish_name: str):
        self.cursor.execute('SELECT chud_value FROM fish_inventory WHERE user_id = ? AND LOWER(fish_name) = LOWER(?)', (user_id, fish_name))
        items = self.cursor.fetchall()
        
        if not items:
            return 0
            
        total_value = sum(item[0] for item in items)
        
        self.cursor.execute('DELETE FROM fish_inventory WHERE user_id = ? AND LOWER(fish_name) = LOWER(?)', (user_id, fish_name))
        self.conn.commit()
        
        return total_value

    def get_inventory(self, user_id: int):
        self.cursor.execute('SELECT id, fish_name, chud_value, xp_value FROM fish_inventory WHERE user_id = ?', (user_id,))
        return self.cursor.fetchall()

    def clear_inventory(self, user_id: int):
        self.cursor.execute('DELETE FROM fish_inventory WHERE user_id = ?', (user_id,))
        self.conn.commit()