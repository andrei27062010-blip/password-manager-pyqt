import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel

# Пока что будем использовать заглушки для окон.
# В дальнейшем эти классы будут импортироваться из ui/login_window.py и ui/main_window.py

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер паролей: Вход")
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()
        self.label = QLabel("Это заглушка окна входа.")
        self.button = QPushButton("Войти (заглушка)")
        self.button.clicked.connect(self._on_login_stub)

        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def _on_login_stub(self):
        print("Нажата кнопка 'Войти' в заглушке LoginWindow.")
        # В реальной версии здесь будет проверка пароля и открытие MainWindow

class MainWindow(QWidget): # Пока QWidget, потом будет QMainWindow
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер паролей: Основное окно (заглушка)")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()
        self.label = QLabel("Это заглушка основного окна.")
        self.add_button = QPushButton("Добавить (заглушка)")
        self.add_button.clicked.connect(self._on_add_stub)
        self.delete_button = QPushButton("Удалить (заглушка)")
        self.delete_button.clicked.connect(self._on_delete_stub)

        layout.addWidget(self.label)
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def _on_add_stub(self):
        print("Нажата кнопка 'Добавить' в заглушке MainWindow.")

    def _on_delete_stub(self):
        print("Нажата кнопка 'Удалить' в заглушке MainWindow.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()

    # Пока что для демонстрации можно открыть и главное окно
    # main_window = MainWindow()
    # main_window.show() # Закомментируем, чтобы не показывать два окна одновременно на старте

    sys.exit(app.exec())
