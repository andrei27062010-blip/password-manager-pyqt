import sys
from PySide6.QtWidgets import (
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
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QClipboard

from ui.login_window import Ui_Form as Ui_LoginWindowBase
from ui.main_window import Ui_MainWindow as Ui_MainWindowBase

from database import DatabaseManager
from crypto import CryptoService
import os
import json
import base64

MASTER_CONFIG_FILE = "master_config.json"  # Файл для хранения хеша мастер-пароля и соли


# --- Вспомогательная функция для работы с файлом конфигурации мастер-пароля ---
def load_master_config():
    if os.path.exists(MASTER_CONFIG_FILE):
        with open(MASTER_CONFIG_FILE, "r") as f:
            config = json.load(f)
            return base64.b64decode(config["master_hash_b64"]), base64.b64decode(
                config["key_salt_b64"]
            )
    return None, None


def save_master_config(master_hash: bytes, key_salt: bytes):
    config = {
        "master_hash_b64": base64.b64encode(master_hash).decode("utf-8"),
        "key_salt_b64": base64.b64encode(key_salt).decode("utf-8"),
    }
    with open(MASTER_CONFIG_FILE, "w") as f:
        json.dump(config, f)


# --- Класс для диалога добавления/редактирования пароля (без изменений) ---
class PasswordDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить/Редактировать запись")
        self.setGeometry(200, 200, 350, 250)

        self.record = record
        self.original_password_hash = None

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Сервис:"))
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("Название сервиса (например, Google)")
        layout.addWidget(self.service_input)

        layout.addWidget(QLabel("Логин:"))
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Имя пользователя или email")
        layout.addWidget(self.login_input)

        layout.addWidget(QLabel("Пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Оставьте пустым, чтобы не менять")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        layout.addWidget(QLabel("Заметки (опционально):"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Дополнительные заметки")
        layout.addWidget(self.notes_input)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        if self.record:
            self.service_input.setText(self.record[1])  # service
            self.login_input.setText(self.record[2])  # login
            self.notes_input.setText(self.record[5] if self.record[5] else "")  # notes

    def get_data(self):
        return (
            self.service_input.text(),
            self.login_input.text(),
            self.password_input.text(),  # Если пароль не меняется, это будет пустая строка
            self.notes_input.text(),
        )


# --- Основные окна ---
class LoginWindow(QWidget, Ui_LoginWindowBase):
    login_successful = Signal(bytes)  # Передаем производный мастер-ключ

    def __init__(self, db_manager: DatabaseManager, crypto_service: CryptoService):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Менеджер паролей: Вход")

        self.db_manager = db_manager
        self.crypto_service = crypto_service

        self.master_hash = None
        self.master_key_salt_for_derived_key = (
            None  # Соль для генерации AES-ключа из мастер-пароля
        )

        # Пытаемся загрузить мастер-данные из файла
        self.master_hash, self.master_key_salt_for_derived_key = load_master_config()

        # Если мастер-пароль еще не установлен (первый запуск)
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

    def _on_set_master_password(self):
        entered_password = self.password_input.text()
        if not entered_password:
            QMessageBox.warning(self, "Ошибка", "Мастер-пароль не может быть пустым.")
            return

        new_key_salt = self.crypto_service.generate_salt()
        new_master_hash = self.crypto_service.hash_password(entered_password)

        save_master_config(new_master_hash, new_key_salt)  # Сохраняем в файл!

        QMessageBox.information(
            self, "Успех", "Мастер-пароль успешно установлен! Теперь войдите."
        )
        # Обновляем состояние окна, чтобы оно действовало как обычное окно входа
        self.master_hash = new_master_hash
        self.master_key_salt_for_derived_key = new_key_salt
        self.password_input.clear()
        self.password_input.setPlaceholderText("Введите мастер-пароль")
        self.login_button.setText("Войти")
        self.login_button.clicked.disconnect(self._on_set_master_password)
        self.login_button.clicked.connect(self._on_login)

    def _on_login(self):
        entered_password = self.password_input.text()
        print(f"DEBUG: Введен пароль: '{entered_password}'")
        if not entered_password:
            QMessageBox.warning(
                self, "Ошибка входа", "Пожалуйста, введите мастер-пароль."
            )
            return

        if self.crypto_service.verify_password(entered_password, self.master_hash):
            print("DEBUG: Мастер-пароль верен.")
            try:
                derived_key = self.crypto_service.derive_key(
                    entered_password, self.master_key_salt_for_derived_key
                )
                print("DEBUG: Ключ шифрования успешно получен.")
                self.login_successful.emit(derived_key)
                self.close()
            except Exception as e:
                print(f"DEBUG: Ошибка при генерации ключа: {e}")
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось сгенерировать ключ: {e}"
                )
        else:
            print("DEBUG: Мастер-пароль неверен.")
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
        print("DEBUG: MainWindow инициализируется.")

        self.db_manager = db_manager
        self.crypto_service = crypto_service

        if master_key_derived:
            try:
                self.crypto_service.set_master_key(master_key_derived)
                print("DEBUG: Мастер-ключ для CryptoService установлен.")
            except Exception as e:
                print(f"DEBUG: Ошибка при установке мастер-ключа: {e}")
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось установить ключ шифрования: {e}"
                )
        else:
            print("DEBUG: Ключ шифрования не был передан в MainWindow.")
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
        self.passwords_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.passwords_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.passwords_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self._load_passwords()
        print("DEBUG: MainWindow инициализация завершена.")

    def _load_passwords(self):
        print("DEBUG: Загрузка паролей...")
        self.db_manager.connect()
        try:
            records = self.db_manager.get_all()
            print(f"DEBUG: Получено записей из БД: {len(records)}")
        except Exception as e:
            print(f"DEBUG: Ошибка при получении записей из БД: {e}")
            records = []
        finally:
            self.db_manager.close()

        self.passwords_table.setRowCount(0)
        if records:
            self.passwords_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                item_service = QTableWidgetItem(record[1])  # Service
                item_login = QTableWidgetItem(record[2])  # Login
                item_password = QTableWidgetItem(
                    "**********"
                )  # Пароль всегда маскируем в таблице
                item_notes = QTableWidgetItem(
                    record[5] if record[5] else ""
                )  # Notes (может быть None)

                item_service.setData(Qt.UserRole, record[0])  # ID
                item_service.setData(Qt.UserRole + 1, record[3])  # encrypted_password
                item_service.setData(Qt.UserRole + 2, record[4])  # salt

                self.passwords_table.setItem(row_idx, 0, item_service)
                self.passwords_table.setItem(row_idx, 1, item_login)
                self.passwords_table.setItem(row_idx, 2, item_password)
                self.passwords_table.setItem(row_idx, 3, item_notes)
        else:
            print("DEBUG: Записей в БД нет.")

        self.passwords_table.resizeColumnsToContents()
        self.passwords_table.horizontalHeader().setStretchLastSection(True)
        print("DEBUG: Загрузка паролей завершена.")

    def _on_add(self):
        print("DEBUG: Кнопка 'Добавить' нажата.")
        dialog = PasswordDialog(self)
        if dialog.exec() == QDialog.Accepted:
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
                except Exception as e:
                    print(f"DEBUG: Ошибка при добавлении записи: {e}")
                    QMessageBox.critical(
                        self, "Ошибка", f"Не удалось добавить запись: {e}"
                    )
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Сервис, логин и пароль обязательны для заполнения."
                )

    def _on_edit(self):
        print("DEBUG: Кнопка 'Редактировать' нажата.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self,
                "Редактирование",
                "Пожалуйста, выберите запись для редактирования.",
            )
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.UserRole)
        # encrypted_password_db = self.passwords_table.item(selected_row, 0).data(Qt.UserRole + 1) # Больше не нужно
        salt_db = self.passwords_table.item(selected_row, 0).data(Qt.UserRole + 2)

        self.db_manager.connect()
        full_record = self.db_manager.get_by_id(
            record_id
        )  # (id, service, login, encrypted_password, salt, notes)
        self.db_manager.close()

        if not full_record:
            QMessageBox.critical(self, "Ошибка", "Запись не найдена в базе данных.")
            return

        dialog = PasswordDialog(
            self, record=full_record
        )  # Передаем всю запись в диалог
        if dialog.exec() == QDialog.Accepted:
            new_service, new_login, new_password_plain, new_notes = dialog.get_data()
            if new_service and new_login:
                new_encrypted_password = full_record[
                    3
                ]  # Берем старый зашифрованный пароль
                new_salt = full_record[4]  # Берем старую соль для записи

                if (
                    new_password_plain
                ):  # Если введен новый пароль, шифруем его с новой солью
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
            else:
                QMessageBox.warning(
                    self, "Ошибка", "Сервис и логин обязательны для заполнения."
                )

    def _on_delete(self):
        print("DEBUG: Кнопка 'Удалить' нажата.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self, "Удаление", "Пожалуйста, выберите запись для удаления."
            )
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db_manager.connect()
            if self.db_manager.delete_by_id(record_id):
                self.db_manager.close()
                self._load_passwords()
                QMessageBox.information(self, "Успех", "Запись успешно удалена.")
            else:
                self.db_manager.close()
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить запись.")

    def _on_copy_password(self):
        print("DEBUG: Кнопка 'Копировать пароль' нажата.")
        selected_row = self.passwords_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(
                self,
                "Копирование",
                "Пожалуйста, выберите запись для копирования пароля.",
            )
            return

        record_id = self.passwords_table.item(selected_row, 0).data(Qt.UserRole)
        encrypted_password = self.passwords_table.item(selected_row, 0).data(
            Qt.UserRole + 1
        )

        if not encrypted_password:
            QMessageBox.critical(
                self, "Ошибка", "Не удалось получить зашифрованный пароль."
            )
            return

        try:
            decrypted_password = self.crypto_service.decrypt_data(encrypted_password)
            QApplication.clipboard().setText(decrypted_password)
            QMessageBox.information(
                self, "Копирование", "Пароль успешно скопирован в буфер обмена."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка дешифрования",
                f"Не удалось дешифровать пароль. Возможно, неверный мастер-пароль или ошибка: {e}",
            )


if __name__ == "__main__":
    print("DEBUG: Приложение запускается.")
    app = QApplication(sys.argv)

    db_manager = DatabaseManager()
    crypto_service = CryptoService()

    db_manager.connect()
    if db_manager.conn:
        db_manager.create_table()
    db_manager.close()
    print("DEBUG: База данных инициализирована.")

    login_window = LoginWindow(db_manager, crypto_service)
    
    app.main_window = None 
    
    def on_login_success(derived_key):
        print("DEBUG: Вход успешен, открываем MainWindow.")
        app.main_window = MainWindow(db_manager, crypto_service, derived_key) # Теперь это атрибут app
        app.main_window.show()
        
    login_window.login_successful.connect(on_login_success)

    login_window.show()
    print("DEBUG: LoginWindow показан.")

    sys.exit(app.exec())
    print("DEBUG: Приложение завершено.")
