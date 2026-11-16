import sys
import csv
import os
import json
import base64
import secrets
import string
import logging # <-- ДОБАВЛЕНО для логирования

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QTableWidget,
    QAbstractItemView,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QMessageBox,
    QTableWidgetItem,
    QListWidget,
    QListWidgetItem,
    QInputDialog,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QClipboard

from ui.login_window import Ui_Form as Ui_LoginWindowBase
from ui.main_window import Ui_MainWindow as Ui_MainWindowBase
from theme import WhiteNightsTheme 
from database import DatabaseManager
from crypto import CryptoService
from csv_transfer import read_csv, write_csv

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
# Создаем папку для логов, если ее нет
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "password_manager.log")
logging.basicConfig(
    level=logging.INFO, # Уровень логирования: INFO (информация), DEBUG (отладка), WARNING (предупреждения), ERROR (ошибки), CRITICAL (критические ошибки)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'), # Логирование в файл
        logging.StreamHandler(sys.stdout) # Логирование в консоль
    ]
)
logger = logging.getLogger(__name__)
# --- КОНЕЦ НАСТРОЙКИ ЛОГГИРОВАНИЯ ---

MASTER_CONFIG_FILE = "master_config.json"


def load_master_config():
    if os.path.exists(MASTER_CONFIG_FILE):
        try:
            with open(MASTER_CONFIG_FILE, "r") as f:
                config = json.load(f)
                return base64.b64decode(config["master_hash_b64"]), base64.b64decode(
                    config["key_salt_b64"]
                )
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка чтения master_config.json: {e}")
            return None, None
    return None, None


def save_master_config(master_hash: bytes, key_salt: bytes):
    try:
        config = {
            "master_hash_b64": base64.b64encode(master_hash).decode("utf-8"),
            "key_salt_b64": base64.b64encode(key_salt).decode("utf-8"),
        }
        with open(MASTER_CONFIG_FILE, "w") as f:
            json.dump(config, f)
        logger.info("Мастер-конфигурация успешно сохранена.")
    except IOError as e:
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось сохранить master_config.json: {e}")


class PasswordDialog(QDialog):
    def __init__(self, parent=None, record=None, categories=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить/Редактировать запись")
        self.setGeometry(200, 200, 450, 360)
        


        self.record = record

        main_layout = QVBoxLayout()

        main_layout.addWidget(QLabel("Сервис:"))
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("Название сервиса (например, Google)")
        main_layout.addWidget(self.service_input)

        main_layout.addWidget(QLabel("Логин:"))
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Имя пользователя или email")
        main_layout.addWidget(self.login_input)

        # --- ГРУППА ДЛЯ ПОЛЯ ПАРОЛЯ, КНОПКИ ГЕНЕРАЦИИ И ОЦЕНКИ ---
        password_group_layout = QHBoxLayout()
        
        password_label = QLabel("Пароль:")
        password_group_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Оставьте пустым, чтобы не менять")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self._on_password_changed)
        password_group_layout.addWidget(self.password_input, 1)

        self.toggle_password_button = QPushButton("Показать")
        self.toggle_password_button.setFixedWidth(85)
        self.toggle_password_button.clicked.connect(self._toggle_password_visibility)
        password_group_layout.addWidget(self.toggle_password_button)

        self.generate_password_button = QPushButton("Сгенерировать")
        self.generate_password_button.setFixedWidth(150)
        password_group_layout.addWidget(self.generate_password_button)
        
        main_layout.addLayout(password_group_layout)

        self.password_strength_label = QLabel("Надежность:") # <-- МЕТКА ДЛЯ ОЦЕНКИ НАДЕЖНОСТИ
        self.password_strength_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.password_strength_label)

        main_layout.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("Без категории", None)
        for category_id, category_name in (categories or []):
            self.category_combo.addItem(category_name, category_id)
        main_layout.addWidget(self.category_combo)

        main_layout.addWidget(QLabel("Заметки (опционально):"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Дополнительные заметки")
        main_layout.addWidget(self.notes_input)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.generate_password_button.clicked.connect(self._on_generate_password)

        if self.record:
            self.service_input.setText(self.record[1])
            self.login_input.setText(self.record[2])
            self.notes_input.setText(self.record[5] if self.record[5] else "")
            category_index = self.category_combo.findData(self.record[6])
            self.category_combo.setCurrentIndex(max(category_index, 0))
            # При редактировании не показываем пароль, но можем оценить его надежность, если он был изменен
            self._on_password_changed(self.password_input.text())


    def get_data(self):
        return (
            self.service_input.text(),
            self.login_input.text(),
            self.password_input.text(),
            self.notes_input.text(),
            self.category_combo.currentData(),
        )

    def _on_generate_password(self):
        logger.info("Нажата кнопка 'Сгенерировать пароль'.")
        length = 16
        characters = string.ascii_letters + string.digits + string.punctuation
        
        password_chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice(string.punctuation)
        ]
        password_chars += [secrets.choice(characters) for _ in range(length - len(password_chars))]
        secrets.SystemRandom().shuffle(password_chars)
        
        generated_password = "".join(password_chars)
        self.password_input.setText(generated_password)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self.toggle_password_button.setText("Скрыть")
        logger.info("Пароль успешно сгенерирован и показан пользователю.")
        self._on_password_changed(generated_password)

    def _toggle_password_visibility(self):
        """Переключает отображение пароля в поле ввода."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText("Скрыть")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText("Показать")

    def _on_password_changed(self, password: str):
        strength_score = 0
        feedback = []

        # 1. Длина
        length = len(password)
        if length >= 16:
            strength_score += 4
            feedback.append("Длина (16+ символов)")
        elif length >= 12:
            strength_score += 3
            feedback.append("Длина (12-15 символов)")
        elif length >= 8:
            strength_score += 2
            feedback.append("Длина (8-11 символов)")
        else:
            feedback.append("Слишком короткий (< 8 символов)")

        # 2. Разнообразие символов
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in string.punctuation for c in password)

        char_types = sum([has_upper, has_lower, has_digit, has_symbol])

        if char_types == 4:
            strength_score += 4
            feedback.append("Все 4 типа символов")
        elif char_types == 3:
            strength_score += 3
            feedback.append("3 типа символов")
        elif char_types == 2:
            strength_score += 2
            feedback.append("2 типа символов")
        else:
            feedback.append("Мало разнообразия")

        # --- Определение уровня надежности ---
        if length == 0:
            strength_text = "Надежность:"
            color = "gray"
        elif strength_score >= 7:
            strength_text = "Надежность: Отличная"
            color = "green"
        elif strength_score >= 5:
            strength_text = "Надежность: Хорошая"
            color = "lightgreen"
        elif strength_score >= 3:
            strength_text = "Надежность: Средняя"
            color = "orange"
        else:
            strength_text = "Надежность: Слабая"
            color = "red"
        
        self.password_strength_label.setText(f"{strength_text} ({', '.join(f for f in feedback if 'Надежность' not in f)})")
        self.password_strength_label.setStyleSheet(f"font-weight: bold; color: {color};")
        logger.info(f"Пароль оценен: '{strength_text}' (Score: {strength_score}, Length: {length}, Types: {char_types})")


class LoginWindow(QWidget, Ui_LoginWindowBase):
    login_successful = pyqtSignal(bytes)

    def __init__(self, db_manager: DatabaseManager, crypto_service: CryptoService):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Менеджер паролей: Вход")
        logger.info("LoginWindow инициализируется.")

        self.db_manager = db_manager
        self.crypto_service = crypto_service

        self.master_hash = None
        self.master_key_salt_for_derived_key = None

        self.master_hash, self.master_key_salt_for_derived_key = load_master_config()

        if not self.master_hash:
            QMessageBox.information(
                self,
                "Первый запуск",
                "Создайте ваш мастер-пароль. Это будет единственный пароль для доступа.",
            )
            self.password_input.setPlaceholderText("Введите НОВЫЙ мастер-пароль")
            self.login_button.setText("Установить мастер-пароль")
            self.login_button.clicked.connect(self._on_set_master_password)
        else:
            self.password_input.setPlaceholderText("Введите мастер-пароль")
            self.login_button.clicked.connect(self._on_login)
        logger.info("LoginWindow инициализация завершена.")


    def _on_set_master_password(self):
        entered_password = self.password_input.text()
        logger.info(f"Попытка установить мастер-пароль.")
        if not entered_password:
            QMessageBox.warning(self, "Ошибка", "Мастер-пароль не может быть пустым.")
            logger.warning("Попытка установить пустой мастер-пароль.")
            return

        new_key_salt = self.crypto_service.generate_salt()
        new_master_hash = self.crypto_service.hash_password(entered_password)

        save_master_config(new_master_hash, new_key_salt)

        self.master_hash = new_master_hash  # Обновляем после сохранения
        self.master_key_salt_for_derived_key = new_key_salt # Обновляем после сохранения

        QMessageBox.information(
            self, "Успех", "Мастер-пароль успешно установлен! Теперь войдите."
        )
        logger.info("Мастер-пароль успешно установлен.")
        self.password_input.clear()
        self.password_input.setPlaceholderText("Введите мастер-пароль")
        self.login_button.setText("Войти")
        self.login_button.clicked.disconnect(self._on_set_master_password)
        self.login_button.clicked.connect(self._on_login)

    def _on_login(self):
        entered_password = self.password_input.text()
        logger.info(f"Попытка входа. Введен пароль (длина): {len(entered_password)}")
        if not entered_password:
            QMessageBox.warning(
                self, "Ошибка входа", "Пожалуйста, введите мастер-пароль."
            )
            logger.warning("Попытка входа с пустым мастер-паролем.")
            return

        if self.crypto_service.verify_password(entered_password, self.master_hash):
            logger.info("Мастер-пароль верен. Генерируем ключ шифрования.")
            try:
                derived_key = self.crypto_service.derive_key(
                    entered_password, self.master_key_salt_for_derived_key
                )
                logger.info("Ключ шифрования успешно получен.")
                self.login_successful.emit(derived_key)
                self.close()
            except Exception as e:
                logger.error(f"Ошибка при генерации ключа: {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось сгенерировать ключ: {e}"
                )
        else:
            logger.warning("Мастер-пароль неверен.")
            QMessageBox.critical(self, "Ошибка входа", "Неверный мастер-пароль.")
            self.password_input.clear()


class MainWindow(QMainWindow, Ui_MainWindowBase):
    def __init__(self, db_manager, crypto_service, master_key_derived=None, master_password_hash=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Менеджер паролей")
        self.db_manager = db_manager
        self.crypto_service = crypto_service
        self.master_password_hash = master_password_hash

        if master_key_derived:
            try:
                self.crypto_service.set_master_key(master_key_derived)
            except Exception as e:
                logger.critical("Ошибка установки ключа: %s", e, exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Не удалось установить ключ шифрования: {e}")
        else:
            QMessageBox.critical(self, "Ошибка", "Ключ шифрования не был передан.")

        self.add_button.clicked.connect(self._on_add)
        self.edit_button.clicked.connect(self._on_edit)
        self.delete_button.clicked.connect(self._on_delete)
        self.copy_password_button.clicked.connect(self._on_copy_password)
        self.import_export_button.clicked.connect(self._open_import_export)
        self.add_category_button.clicked.connect(self._on_add_category)
        self.delete_category_button.clicked.connect(self._on_delete_category)
        self.category_list.currentItemChanged.connect(self._refresh_passwords)
        self.search_input.textChanged.connect(self._refresh_passwords)
        self.passwords_table.cellClicked.connect(self._on_table_cell_clicked)

        self.passwords_table.setColumnCount(5)
        self.passwords_table.setHorizontalHeaderLabels(["Сервис", "Логин", "Пароль", "Заметки", "★"])
        self.passwords_table.verticalHeader().setVisible(False)
        self.passwords_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.passwords_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.passwords_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.passwords_table.setColumnWidth(4, 48)
        self._load_categories()

    def _open_import_export(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Импорт и экспорт")
        dialog.setMinimumWidth(360)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Переносите пароли между менеджерами с помощью CSV-файла."))
        export_button = QPushButton("Экспортировать в CSV")
        import_button = QPushButton("Импортировать из CSV")
        close_button = QPushButton("Закрыть")
        layout.addWidget(export_button)
        layout.addWidget(import_button)
        layout.addWidget(close_button)
        export_button.clicked.connect(self._export_csv)
        import_button.clicked.connect(self._import_csv)
        close_button.clicked.connect(dialog.accept)
        dialog.exec()

    def _export_csv(self):
        warning = QMessageBox.warning(
            self,
            "Экспорт открытых паролей",
            "CSV-файл будет содержать пароли в открытом виде. Любой человек, "
            "получивший этот файл, сможет их прочитать. Храните его безопасно "
            "и удалите после переноса, если он больше не нужен. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if warning != QMessageBox.StandardButton.Yes:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт паролей", "passwords.csv", "CSV-файлы (*.csv)"
        )
        if not path:
            return
        if not path.casefold().endswith(".csv"):
            path += ".csv"

        if not self.master_password_hash:
            QMessageBox.critical(
                self,
                "Ошибка проверки",
                "Не удалось проверить мастер-пароль. Экспорт отменён.",
            )
            return

        entered_password, accepted = QInputDialog.getText(
            self,
            "Подтверждение владельца",
            "Проверка безопасности: вы действительно владелец хранилища?\\n"
            "Введите мастер-пароль для подтверждения экспорта:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        if not self.crypto_service.verify_password(
            entered_password, self.master_password_hash
        ):
            QMessageBox.warning(
                self,
                "Экспорт отменён",
                "Неверный мастер-пароль. Экспорт не выполнен.",
            )
            return

        self.db_manager.connect()
        try:
            records = self.db_manager.get_passwords()
            categories = dict(self.db_manager.get_categories())
            export_records = []
            for record in records:
                record_id, service, login, encrypted, salt, notes, category_id, favorite = record
                export_records.append({
                    "service": service,
                    "login": login,
                    "password": self.crypto_service.decrypt_data(encrypted),
                    "notes": notes or "",
                    "category": categories.get(category_id, ""),
                    "is_favorite": bool(favorite),
                })
        except Exception as e:
            logger.error("Ошибка подготовки CSV-экспорта: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось подготовить данные: {e}")
            return
        finally:
            self.db_manager.close()

        try:
            write_csv(path, export_records)
        except (OSError, ValueError, csv.Error) as e:
            logger.error("Ошибка записи CSV-файла: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить CSV-файл: {e}")
            return
        QMessageBox.information(
            self, "Экспорт завершён",
            f"Экспортировано записей: {len(export_records)}. Не забудьте защитить CSV-файл."
        )

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт паролей", "", "CSV-файлы (*.csv);;Все файлы (*)"
        )
        if not path:
            return
        try:
            imported_records = read_csv(path)
        except (OSError, UnicodeError, ValueError, csv.Error) as e:
            logger.warning("CSV-файл не прошёл проверку: %s", e)
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось прочитать CSV-файл:\n{e}")
            return

        reply = QMessageBox.question(
            self, "Подтверждение импорта",
            f"В файле найдено записей: {len(imported_records)}.\n"
            "Повторяющиеся пары «сервис + логин» будут пропущены. "
            "Новые категории будут созданы автоматически. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            prepared_records = []
            for record in imported_records:
                prepared = dict(record)
                prepared["encrypted_password"] = self.crypto_service.encrypt_data(record["password"])
                prepared["salt"] = self.crypto_service.generate_salt()
                prepared_records.append(prepared)

            self.db_manager.connect()
            added, skipped = self.db_manager.import_records(prepared_records)
        except Exception as e:
            logger.error("Ошибка импорта CSV: %s", e, exc_info=True)
            QMessageBox.critical(
                self, "Ошибка импорта",
                f"Импорт не выполнен. Данные базы данных не были изменены.\n{e}"
            )
            return
        finally:
            self.db_manager.close()

        self._load_categories()
        QMessageBox.information(
            self, "Импорт завершён",
            f"Добавлено записей: {added}.\nПропущено дубликатов: {skipped}."
        )

    def _database_categories(self):
        self.db_manager.connect()
        try:
            return self.db_manager.get_categories()
        finally:
            self.db_manager.close()

    def _load_categories(self):
        categories = self._database_categories()
        self.category_list.clear()
        all_item = QListWidgetItem("Все")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.category_list.addItem(all_item)
        favorites_item = QListWidgetItem("Избранное  ★")
        favorites_item.setData(Qt.ItemDataRole.UserRole, "favorites")
        self.category_list.addItem(favorites_item)

        if categories:
            separator = QListWidgetItem("Мои категории")
            separator.setFlags(Qt.ItemFlag.NoItemFlags)
            self.category_list.addItem(separator)
            for category_id, name in categories:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, category_id)
                self.category_list.addItem(item)
        self.category_list.setCurrentRow(0)
        self._refresh_passwords()

    def _selected_category(self):
        item = self.category_list.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        if value == "favorites":
            return None, True
        if isinstance(value, int):
            return value, False
        return None, False

    def _refresh_passwords(self, *_args):
        category_id, favorites_only = self._selected_category()
        self.db_manager.connect()
        try:
            records = self.db_manager.get_passwords(
                category_id, favorites_only, self.search_input.text()
            )
        except Exception as e:
            logger.error("Ошибка загрузки паролей: %s", e, exc_info=True)
            records = []
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить пароли: {e}")
        finally:
            self.db_manager.close()

        self.passwords_table.setRowCount(0)
        for row, record in enumerate(records):
            record_id, service, login, encrypted, salt, notes, category_id, favorite = record
            self.passwords_table.insertRow(row)
            service_item = QTableWidgetItem(service)
            service_item.setData(Qt.ItemDataRole.UserRole, record_id)
            service_item.setData(Qt.ItemDataRole.UserRole + 1, encrypted)
            service_item.setData(Qt.ItemDataRole.UserRole + 2, salt)
            service_item.setData(Qt.ItemDataRole.UserRole + 3, category_id)
            service_item.setData(Qt.ItemDataRole.UserRole + 4, bool(favorite))
            self.passwords_table.setItem(row, 0, service_item)
            self.passwords_table.setItem(row, 1, QTableWidgetItem(login))
            self.passwords_table.setItem(row, 2, QTableWidgetItem("**********"))
            self.passwords_table.setItem(row, 3, QTableWidgetItem(notes or ""))
            favorite_item = QTableWidgetItem("★" if favorite else "☆")
            favorite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.passwords_table.setItem(row, 4, favorite_item)
        self.passwords_table.horizontalHeader().setStretchLastSection(True)

    def _on_add_category(self):
        name, accepted = QInputDialog.getText(self, "Новая категория", "Название категории:")
        if not accepted:
            return
        if not name.strip():
            QMessageBox.warning(self, "Категория", "Название категории не может быть пустым.")
            return
        self.db_manager.connect()
        try:
            category_id = self.db_manager.add_category(name)
        finally:
            self.db_manager.close()
        if category_id is None:
            QMessageBox.warning(self, "Категория", "Название категории уже занято или зарезервировано.")
            return
        self._load_categories()
        for index in range(self.category_list.count()):
            item = self.category_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == category_id:
                self.category_list.setCurrentItem(item)
                break

    def _on_delete_category(self):
        item = self.category_list.currentItem()
        category_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not isinstance(category_id, int):
            QMessageBox.information(self, "Удаление категории", "Выберите собственную категорию.")
            return
        reply = QMessageBox.question(
            self, "Удаление категории",
            "Удалить категорию? Пароли сохранятся и останутся в разделе «Все».",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db_manager.connect()
        try:
            deleted = self.db_manager.delete_category(category_id)
        finally:
            self.db_manager.close()
        if not deleted:
            QMessageBox.critical(self, "Ошибка", "Не удалось удалить категорию.")
            return
        self._load_categories()

    def _on_table_cell_clicked(self, row, column):
        if column != 4:
            return
        item = self.passwords_table.item(row, 0)
        record_id = item.data(Qt.ItemDataRole.UserRole)
        new_favorite = not item.data(Qt.ItemDataRole.UserRole + 4)
        self.db_manager.connect()
        try:
            updated = self.db_manager.set_favorite(record_id, new_favorite)
        finally:
            self.db_manager.close()
        if updated:
            self._refresh_passwords()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить избранное.")

    def _dialog_categories(self):
        return self._database_categories()

    def _on_add(self):
        dialog = PasswordDialog(self, categories=self._dialog_categories())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        service, login, password, notes, category_id = dialog.get_data()
        service, login = service.strip(), login.strip()
        if not service or not login or not password:
            QMessageBox.warning(self, "Ошибка", "Сервис, логин и пароль обязательны для заполнения.")
            return
        try:
            encrypted = self.crypto_service.encrypt_data(password)
            salt = self.crypto_service.generate_salt()
            self.db_manager.connect()
            added = self.db_manager.add_record(service, login, encrypted, salt, notes, category_id)
        except Exception as e:
            logger.error("Ошибка добавления записи: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись: {e}")
            return
        finally:
            self.db_manager.close()
        if not added:
            QMessageBox.warning(self, "Повторная запись", "Для этого сервиса уже сохранён такой логин.")
            return
        self._refresh_passwords()
        QMessageBox.information(self, "Успех", "Запись успешно добавлена.")

    def _on_edit(self):
        row = self.passwords_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Редактирование", "Выберите запись для редактирования.")
            return
        record_id = self.passwords_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.db_manager.connect()
        try:
            record = self.db_manager.get_by_id(record_id)
            categories = self.db_manager.get_categories()
        finally:
            self.db_manager.close()
        if not record:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена в базе данных.")
            return

        dialog = PasswordDialog(self, record=record, categories=categories)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        service, login, password, notes, category_id = dialog.get_data()
        service, login = service.strip(), login.strip()
        if not service or not login:
            QMessageBox.warning(self, "Ошибка", "Сервис и логин обязательны для заполнения.")
            return

        encrypted, salt = record[3], record[4]
        try:
            if password:
                encrypted = self.crypto_service.encrypt_data(password)
                salt = self.crypto_service.generate_salt()
            self.db_manager.connect()
            updated = self.db_manager.update_record(
                record_id, service, login, encrypted, salt, notes,
                category_id, bool(record[7])
            )
        except Exception as e:
            logger.error("Ошибка обновления записи: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить запись: {e}")
            return
        finally:
            self.db_manager.close()
        if not updated:
            QMessageBox.warning(self, "Повторная запись", "Не удалось обновить запись. Возможно, такой логин уже существует.")
            return
        self._refresh_passwords()
        QMessageBox.information(self, "Успех", "Запись успешно обновлена.")

    def _on_delete(self):
        row = self.passwords_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Удаление", "Выберите запись для удаления.")
            return
        record_id = self.passwords_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Подтверждение", "Удалить выбранную запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db_manager.connect()
        try:
            deleted = self.db_manager.delete_by_id(record_id)
        finally:
            self.db_manager.close()
        if deleted:
            self._refresh_passwords()
            QMessageBox.information(self, "Успех", "Запись успешно удалена.")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось удалить запись.")

    def _on_copy_password(self):
        row = self.passwords_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Копирование", "Выберите запись для копирования пароля.")
            return
        item = self.passwords_table.item(row, 0)
        record_id = item.data(Qt.ItemDataRole.UserRole)
        encrypted = item.data(Qt.ItemDataRole.UserRole + 1)
        if not encrypted:
            QMessageBox.critical(self, "Ошибка", "Не удалось получить зашифрованный пароль.")
            return
        try:
            decrypted = self.crypto_service.decrypt_data(encrypted)
            QApplication.clipboard().setText(decrypted)
            QMessageBox.information(self, "Копирование", "Пароль скопирован в буфер обмена.")
            logger.info("Пароль записи %s скопирован в буфер обмена.", record_id)
        except Exception as e:
            logger.error("Ошибка дешифрования записи %s: %s", record_id, e, exc_info=True)
            QMessageBox.critical(self, "Ошибка дешифрования", f"Не удалось дешифровать пароль: {e}")


if __name__ == "__main__":
    logger.info("Приложение запускается.")
    app = QApplication(sys.argv)
    app.setStyleSheet(WhiteNightsTheme.get_stylesheet())
    
    db_manager = DatabaseManager()
    crypto_service = CryptoService()

    db_manager.connect()
    if db_manager.conn:
        db_manager.create_table()
    db_manager.close()
    logger.info("База данных инициализирована.")

    login_window = LoginWindow(db_manager, crypto_service)
    
    app.main_window = None # Сохраняем ссылку на главное окно, чтобы сборщик мусора не удалил его
    
    def on_login_success(derived_key):
        logger.info("Вход успешен, открываем MainWindow.")
        app.main_window = MainWindow(
            db_manager, crypto_service, derived_key, login_window.master_hash
        )
        app.main_window.show()
        login_window.close() # Закрываем окно входа после успешного логина
        
    login_window.login_successful.connect(on_login_success)

    login_window.show()
    logger.info("LoginWindow показан.")

    sys.exit(app.exec())
    logger.info("Приложение завершено.")