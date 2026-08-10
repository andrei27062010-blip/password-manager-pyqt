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
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            self.conn = None
            self.cursor = None

    def close(self):
        if self.conn:
            self.conn.close()

    def create_table(self): # ИЗМЕНЕНО: снова только одна таблица passwords
        if not self.cursor:
            print("No database connection. Cannot create table.")
            return

        try:
            # Таблица для паролей сервисов (с шифрованием)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    login TEXT NOT NULL,
                    encrypted_password BLOB NOT NULL, /* Теперь BLOB для зашифрованных байтов */
                    salt BLOB NOT NULL,              /* Новое поле для соли КАЖДОЙ записи пароля сервиса */
                    notes TEXT
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

    # --- Методы CRUD для паролей сервисов (без изменений в сигнатурах) ---
    def add_record(self, service: str, login: str, encrypted_password: bytes, salt: bytes, notes: str):
        if not self.cursor:
            print("No database connection. Cannot add record.")
            return False
        try:
            self.cursor.execute(
                "INSERT INTO passwords (service, login, encrypted_password, salt, notes) VALUES (?, ?, ?, ?, ?)",
                (service, login, encrypted_password, salt, notes)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding record: {e}")
            return False

    def get_all(self):
        if not self.cursor:
            print("No database connection. Cannot get records.")
            return []
        try:
            self.cursor.execute("SELECT id, service, login, encrypted_password, salt, notes FROM passwords")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting records: {e}")
            return []

    def get_by_id(self, record_id: int):
        if not self.cursor:
            print("No database connection. Cannot get record by ID.")
            return None
        try:
            self.cursor.execute("SELECT id, service, login, encrypted_password, salt, notes FROM passwords WHERE id = ?", (record_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error getting record by ID: {e}")
            return None

    def update_record(self, record_id: int, service: str, login: str, encrypted_password: bytes, salt: bytes, notes: str):
        if not self.cursor:
            print("No database connection. Cannot update record.")
            return False
        try:
            self.cursor.execute(
                "UPDATE passwords SET service = ?, login = ?, encrypted_password = ?, salt = ?, notes = ? WHERE id = ?",
                (service, login, encrypted_password, salt, notes, record_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating record: {e}")
            return False

    def delete_by_id(self, record_id: int):
        if not self.cursor:
            print("No database connection. Cannot delete record.")
            return False
        try:
            self.cursor.execute("DELETE FROM passwords WHERE id = ?", (record_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting record: {e}")
            return False