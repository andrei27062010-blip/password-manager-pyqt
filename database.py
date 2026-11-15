import sqlite3


class DatabaseManager:
    def __init__(self, db_name="passwords.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            self.conn = None
            self.cursor = None

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    @staticmethod
    def _normalize(value: str) -> str:
        """Убирает пробелы по краям и приводит текст к нижнему регистру."""
        return value.strip().casefold()

    def create_table(self):
        if not self.cursor:
            print("No database connection. Cannot create tables.")
            return

        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    login TEXT NOT NULL,
                    encrypted_password BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    notes TEXT,
                    service_normalized TEXT,
                    login_normalized TEXT,
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    is_favorite INTEGER NOT NULL DEFAULT 0
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
            if "category_id" not in columns:
                self.cursor.execute(
                    "ALTER TABLE passwords ADD COLUMN category_id INTEGER "
                    "REFERENCES categories(id) ON DELETE SET NULL"
                )
            if "is_favorite" not in columns:
                self.cursor.execute(
                    "ALTER TABLE passwords ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0"
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
            print(f"Error creating tables: {e}")
            raise

    def is_duplicate(self, service: str, login: str, exclude_id: int = None) -> bool:
        """Проверяет пару «сервис + логин», не учитывая регистр и пробелы по краям."""
        if not self.cursor:
            raise sqlite3.Error("No database connection.")

        normalized_service = self._normalize(service)
        normalized_login = self._normalize(login)
        query = """
            SELECT 1 FROM passwords
            WHERE service_normalized = ? AND login_normalized = ?
        """
        params = [normalized_service, normalized_login]
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        self.cursor.execute(query, params)
        return self.cursor.fetchone() is not None

    def add_category(self, name: str):
        if not self.cursor:
            return None
        normalized_name = name.strip()
        if not normalized_name:
            return None
        try:
            self.cursor.execute("SELECT name FROM categories")
            existing_names = [row[0] for row in self.cursor.fetchall()]
            if any(self._normalize(existing) == self._normalize(normalized_name)
                   for existing in existing_names):
                return None
            self.cursor.execute(
                "INSERT INTO categories (name) VALUES (?)", (normalized_name,)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error as e:
            print(f"Error adding category: {e}")
            return None

    def get_categories(self):
        if not self.cursor:
            return []
        try:
            self.cursor.execute("SELECT id, name FROM categories ORDER BY name COLLATE NOCASE")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting categories: {e}")
            return []

    def delete_category(self, category_id: int):
        """Удаляет категорию, оставляя её пароли без категории."""
        if not self.cursor:
            return False
        try:
            self.cursor.execute(
                "UPDATE passwords SET category_id = NULL WHERE category_id = ?",
                (category_id,)
            )
            self.cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error deleting category: {e}")
            return False

    def get_passwords(self, category_id=None, favorites_only=False, search_text=""):
        """Возвращает записи с учётом выбранной категории и поискового запроса."""
        if not self.cursor:
            return []
        query = """
            SELECT id, service, login, encrypted_password, salt, notes,
                   category_id, is_favorite
            FROM passwords
            WHERE 1 = 1
        """
        params = []
        if favorites_only:
            query += " AND is_favorite = 1"
        elif category_id is not None:
            query += " AND category_id = ?"
            params.append(category_id)

        search_text = search_text.strip()
        if search_text:
            pattern = f"%{search_text}%"
            query += " AND (service LIKE ? COLLATE NOCASE "
            query += "OR login LIKE ? COLLATE NOCASE OR notes LIKE ? COLLATE NOCASE)"
            params.extend((pattern, pattern, pattern))

        query += " ORDER BY service COLLATE NOCASE, login COLLATE NOCASE"
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting passwords: {e}")
            return []

    def get_by_id(self, record_id: int):
        if not self.cursor:
            return None
        try:
            self.cursor.execute(
                """
                SELECT id, service, login, encrypted_password, salt, notes,
                       category_id, is_favorite
                FROM passwords WHERE id = ?
                """,
                (record_id,)
            )
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error getting record by ID: {e}")
            return None

    def add_record(
        self, service: str, login: str, encrypted_password: bytes,
        salt: bytes, notes: str, category_id=None, is_favorite=False
    ):
        if not self.cursor:
            return False
        try:
            if self.is_duplicate(service, login):
                return False
            self.cursor.execute(
                """
                INSERT INTO passwords (
                    service, login, encrypted_password, salt, notes,
                    service_normalized, login_normalized, category_id, is_favorite
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service, login, encrypted_password, salt, notes,
                    self._normalize(service), self._normalize(login),
                    category_id, int(bool(is_favorite))
                )
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error adding record: {e}")
            return False

    def update_record(
        self, record_id: int, service: str, login: str,
        encrypted_password: bytes, salt: bytes, notes: str,
        category_id=None, is_favorite=False
    ):
        if not self.cursor:
            return False
        try:
            if self.is_duplicate(service, login, exclude_id=record_id):
                return False
            self.cursor.execute(
                """
                UPDATE passwords
                SET service = ?, login = ?, encrypted_password = ?, salt = ?,
                    notes = ?, service_normalized = ?, login_normalized = ?,
                    category_id = ?, is_favorite = ?
                WHERE id = ?
                """,
                (
                    service, login, encrypted_password, salt, notes,
                    self._normalize(service), self._normalize(login),
                    category_id, int(bool(is_favorite)), record_id
                )
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error updating record: {e}")
            return False

    def set_favorite(self, record_id: int, is_favorite: bool):
        if not self.cursor:
            return False
        try:
            self.cursor.execute(
                "UPDATE passwords SET is_favorite = ? WHERE id = ?",
                (int(bool(is_favorite)), record_id)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error updating favorite status: {e}")
            return False

    def delete_by_id(self, record_id: int):
        if not self.cursor:
            return False
        try:
            self.cursor.execute("DELETE FROM passwords WHERE id = ?", (record_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error deleting record: {e}")
            return False
