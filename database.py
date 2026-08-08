    import sqlite3

    class DatabaseManager:
        def __init__(self, db_name="passwords.db"):
            self.db_name = db_name
            self.conn = None
            self.cursor = None

        def connect(self):
            try:
                self.conn = sqlite3.connect(self.db_name)
                self.cursor = self.conn.cursor()
                print(f"Connected to database: {self.db_name}")
            except sqlite3.Error as e:
                print(f"Error connecting to database: {e}")
                self.conn = None
                self.cursor = None

        def close(self):
            if self.conn:
                self.conn.close()
                print("Database connection closed.")

        def create_table(self):
            if not self.cursor:
                print("No database connection. Cannot create table.")
                return

            try:
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS passwords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service TEXT NOT NULL,
                        login TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        notes TEXT
                    )
                ''')
                self.conn.commit()
                print("Table 'passwords' created or already exists.")
            except sqlite3.Error as e:
                print(f"Error creating table: {e}")

    if __name__ == "__main__":
        db_manager = DatabaseManager()
        db_manager.connect()
        if db_manager.conn:
            db_manager.create_table()
            db_manager.close()
    
