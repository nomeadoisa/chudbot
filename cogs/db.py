import sqlite3

class Database:
    def __init__(self, db_path='database.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._setup_tables()

    def _setup_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER PRIMARY KEY, date TEXT, score INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, tier INTEGER DEFAULT 1)''')
        self.conn.commit()

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

    def get_profile(self, user_id: int):
        self.cursor.execute('SELECT balance, xp, tier FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()