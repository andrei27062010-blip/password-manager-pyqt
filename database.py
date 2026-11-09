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

    @staticmethod
    def _normalize(value: str) -> str:
        """Убирает пробелы по краям и приводит текст к нижнему регистру."""
        return value.strip().casefold()

    def create_table(self):
        if not self.cursor:
            print("No database connection. Cannot create table.")
            return

        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    login TEXT NOT NULL,
                    encrypted_password BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    notes TEXT,
                    service_normalized TEXT,
                    login_normalized TEXT
                )
            """)

            self.cursor.execute("PRAGMA table_info(passwords)")
            columns = {row[1] for row in self.cursor.fetchall()}
            if "service_normalized" not in columns:
                self.cursor.execute(
                    "ALTER TABLE passwords ADD COLUMN service_normalized TEXT"
                )
            if "login_normalized" not in columns:
                self.cursor.execute(
                    "ALTER TABLE passwords ADD COLUMN login_normalized TEXT"
                )

            self.cursor.execute("SELECT id, service, login FROM passwords")
            for record_id, service, login in self.cursor.fetchall():
                self.cursor.execute(
                    """
                    UPDATE passwords
                    SET service_normalized = ?, login_normalized = ?
                    WHERE id = ?
                    """,
                    (self._normalize(service), self._normalize(login), record_id)
                )

            try:
                self.cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_passwords_service_login
                    ON passwords(service_normalized, login_normalized)
                """)
            except sqlite3.IntegrityError:
                print(
                    "Duplicate service/login pairs already exist. "
                    "The application will prevent adding new duplicates."
                )

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error creating table: {e}")

    def is_duplicate(self, service: str, login: str, exclude_id: int = None) -> bool:
        """Проверяет пару «сервис + логин», не учитывая регистр и пробелы по краям."""
        if not self.cursor:
            print("No database connection. Cannot check duplicate.")
            return False

        normalized_service = self._normalize(service)
        normalized_login = self._normalize(login)
        try:
            self.cursor.execute(
                "SELECT id, service_normalized, login_normalized FROM passwords"
            )
            for record_id, stored_service, stored_login in self.cursor.fetchall():
                if exclude_id is not None and record_id == exclude_id:
                    continue
                if stored_service == normalized_service and stored_login == normalized_login:
                    return True
            return False
        except sqlite3.Error as e:
            print(f"Error checking duplicate: {e}")
            raise

    # --- Методы CRUD для паролей сервисов (без изменений в сигнатурах) ---
    def add_record(self, service: str, login: str, encrypted_password: bytes, salt: bytes, notes: str):
        if not self.cursor:
            print("No database connection. Cannot add record.")
            return False
        try:
            if self.is_duplicate(service, login):
                return False
            self.cursor.execute(
                """
                INSERT INTO passwords (
                    service, login, encrypted_password, salt, notes,
                    service_normalized, login_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service, login, encrypted_password, salt, notes,
                    self._normalize(service), self._normalize(login)
                )
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
            if self.is_duplicate(service, login, exclude_id=record_id):
                return False
            self.cursor.execute(
                """
                UPDATE passwords
                SET service = ?, login = ?, encrypted_password = ?, salt = ?, notes = ?,
                    service_normalized = ?, login_normalized = ?
                WHERE id = ?
                """,
                (
                    service, login, encrypted_password, salt, notes,
                    self._normalize(service), self._normalize(login), record_id
                )
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