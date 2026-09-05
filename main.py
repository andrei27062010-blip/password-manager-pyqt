import sys
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
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QClipboard

from ui.login_window import Ui_Form as Ui_LoginWindowBase
from ui.main_window import Ui_MainWindow as Ui_MainWindowBase
from theme import WhiteNightsTheme 
from database import DatabaseManager
from crypto import CryptoService

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
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить/Редактировать запись")
        self.setGeometry(200, 200, 450, 300)
        


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
        self.password_input.textChanged.connect(self._on_password_changed) # <-- ПОДКЛЮЧАЕМ СЛОТ ДЛЯ ОЦЕНКИ
        password_group_layout.addWidget(self.password_input, 1)

        self.generate_password_button = QPushButton("Сгенерировать")
        self.generate_password_button.setFixedWidth(150) # Фиксируем ширину кнопки
        password_group_layout.addWidget(self.generate_password_button)
        
        main_layout.addLayout(password_group_layout)

        self.password_strength_label = QLabel("Надежность:") # <-- МЕТКА ДЛЯ ОЦЕНКИ НАДЕЖНОСТИ
        self.password_strength_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.password_strength_label)

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
            # При редактировании не показываем пароль, но можем оценить его надежность, если он был изменен
            self._on_password_changed(self.password_input.text())


    def get_data(self):
        return (
            self.service_input.text(),
            self.login_input.text(),
            self.password_input.text(),
            self.notes_input.text(),
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
        logger.info("Пароль успешно сгенерирован и вставлен в поле.")
        self._on_password_changed(generated_password) # Сразу оценим сгенерированный пароль

    def _on_password_changed(self, password: str): # <-- МЕТОД ОЦЕНКИ НАДЕЖНОСТИ
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
    def __init__(
        self,
        db_manager: DatabaseManager,
        crypto_service: CryptoService,
        master_key_derived: bytes = None,
    ):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Менеджер паролей: Основное окно")
        logger.info("MainWindow инициализируется.")

        self.db_manager = db_manager
        self.crypto_service = crypto_service

        if master_key_derived:
            try:
                self.crypto_service.set_master_key(master_key_derived)
                logger.info("Мастер-ключ для CryptoService установлен.")
            except Exception as e:
                logger.critical(f"Ошибка при установке мастер-ключа: {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось установить ключ шифрования: {e}"
                )
        else:
            logger.critical("Ключ шифрования не был передан в MainWindow.")
            QMessageBox.critical(
                self,
                "Ошибка",
                "Ключ шифрования не был передан. Дешифрование невозможно.",
            )

        self.add_button.clicked.connect(self._on_add)
        self.edit_button.clicked.connect(self._on_edit)
        self.delete_button.clicked.connect(self._on_delete)
        self.copy_password_button.clicked.connect(self._on_copy_password)

        self.passwords_table.setColumnCount(4)
        self.passwords_table.setHorizontalHeaderLabels(
            ["Сервис", "Логин", "Пароль", "Заметки"]
        )
        self.passwords_table.verticalHeader().setVisible(False)
        self.passwords_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.passwords_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.passwords_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self._load_passwords()
        logger.info("MainWindow инициализация завершена.")

    def _load_passwords(self):
        logger.info("Загрузка паролей...")
        self.db_manager.connect()
        try:
            records = self.db_manager.get_all()
            logger.info(f"Получено записей из БД: {len(records)}")
        except Exception as e:
            logger.error(f"Ошибка при получении записей из БД: {e}", exc_info=True)
            records = []
        finally:
            self.db_manager.close()

        self.passwords_table.setRowCount(0)
        if records:
            self.passwords_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                item_service = QTableWidgetItem(record[1])
                item_login = QTableWidgetItem(record[2])
                item_password = QTableWidgetItem("**********")
                item_notes = QTableWidgetItem(
                    record[5] if record[5] else ""
                )

                item_service.setData(Qt.ItemDataRole.UserRole, record[0])
                item_service.setData(Qt.ItemDataRole.UserRole + 1, record[3])
                item_service.setData(Qt.ItemDataRole.UserRole + 2, record[4])

                self.passwords_table.setItem(row_idx, 0, item_service)
                self.passwords_table.setItem(row_idx, 1, item_login)
                self.passwords_table.setItem(row_idx, 2, item_password)
                self.passwords_table.setItem(row_idx, 3, item_notes)
        else:
            logger.info("Записей в БД нет.")

        self.passwords_table.horizontalHeader().setStretchLastSection(True)
        logger.info("Загрузка паролей завершена.")

    def _on_add(self):
        logger.info("Нажата кнопка 'Добавить'.")
        dialog = PasswordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            service, login, password_plain, notes = dialog.get_data()
            if service and login and password_plain:
                try:
                    record_salt = self.crypto_service.generate_salt()
                    encrypted_password = self.crypto_service.encrypt_data(
                        password_plain
                    )

                    self.db_manager.connect()
                    self.db_manager.add_record(
                        service, login, encrypted_password, record_salt, notes
                    )
                    self.db_manager.close()
                    self._load_passwords()
                    QMessageBox.information(self, "Успех", "Запись успешно добавлена!")
                    logger.info(f"Запись успешно добавлена для сервиса: {service}")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении записи: {e}", exc_info=True)
                    QMessageBox.critical(
                        self, "Ошибка", f"Не удалось добавить запись: {e}"
                    )
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Сервис, логин и пароль обязательны для заполнения."
                )
                logger.warning("Попытка добавить запись с незаполненными обязательными полями.")

    def _on_edit(self):
        logger.info("Нажата кнопка 'Редактировать'.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self,
                "Редактирование",
                "Пожалуйста, выберите запись для редактирования.",
            )
            logger.warning("Попытка редактирования без выбора записи.")
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        # salt_db больше не нужен напрямую здесь, его получим из full_record
        
        self.db_manager.connect()
        full_record = self.db_manager.get_by_id(record_id)
        self.db_manager.close()

        if not full_record:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена в базе данных.")
            logger.error(f"Запись с ID {record_id} не найдена в БД для редактирования.")
            return

        dialog = PasswordDialog(
            self, record=full_record
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_service, new_login, new_password_plain, new_notes = dialog.get_data()
            if new_service and new_login:
                new_encrypted_password = full_record[3]
                new_salt = full_record[4]

                if new_password_plain:
                    new_salt = self.crypto_service.generate_salt()
                    new_encrypted_password = self.crypto_service.encrypt_data(
                        new_password_plain
                    )

                self.db_manager.connect()
                self.db_manager.update_record(
                    record_id,
                    new_service,
                    new_login,
                    new_encrypted_password,
                    new_salt,
                    new_notes,
                )
                self.db_manager.close()
                self._load_passwords()
                QMessageBox.information(self, "Успех", "Запись успешно обновлена!")
                logger.info(f"Запись с ID {record_id} успешно обновлена для сервиса: {new_service}")
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Сервис и логин обязательны для заполнения."
                )
                logger.warning(f"Попытка обновить запись {record_id} с незаполненными обязательными полями.")


    def _on_delete(self):
        logger.info("Нажата кнопка 'Удалить'.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self, "Удаление", "Пожалуйста, выберите запись для удаления."
            )
            logger.warning("Попытка удаления без выбора записи.")
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить выбранную запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.connect()
            if self.db_manager.delete_by_id(record_id):
                self.db_manager.close()
                self._load_passwords()
                QMessageBox.information(self, "Успех", "Запись успешно удалена.")
                logger.info(f"Запись с ID {record_id} успешно удалена.")
            else:
                self.db_manager.close()
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить запись.")
                logger.error(f"Не удалось удалить запись с ID {record_id}.")

    def _on_copy_password(self):
        logger.info("Нажата кнопка 'Копировать пароль'.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self,
                "Копирование",
                "Пожалуйста, выберите запись для копирования пароля.",
            )
            logger.warning("Попытка копирования без выбора записи.")
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        encrypted_password = self.passwords_table.item(selected_row, 0).data(
            Qt.ItemDataRole.UserRole + 1
        )

        if not encrypted_password:
            QMessageBox.critical(
                self, "Ошибка", "Не удалось получить зашифрованный пароль."
            )
            logger.error(f"Не удалось получить зашифрованный пароль для записи ID {record_id}.")
            return

        try:
            decrypted_password = self.crypto_service.decrypt_data(encrypted_password)
            QApplication.clipboard().setText(decrypted_password)
            QMessageBox.information(
                self, "Копирование", "Пароль успешно скопирован в буфер обмена."
            )
            logger.info(f"Пароль для записи ID {record_id} успешно скопирован в буфер обмена.")
        except Exception as e:
            logger.error(f"Ошибка дешифрования пароля для записи ID {record_id}: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Ошибка дешифрования",
                f"Не удалось дешифровать пароль. Возможно, неверный мастер-пароль или ошибка: {e}",
            )


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
        app.main_window = MainWindow(db_manager, crypto_service, derived_key)
        app.main_window.show()
        login_window.close() # Закрываем окно входа после успешного логина
        
    login_window.login_successful.connect(on_login_success)

    login_window.show()
    logger.info("LoginWindow показан.")

    sys.exit(app.exec())
    logger.info("Приложение завершено.")