# Form implementation generated from reading ui file 'ui/main_window.ui'
# Generated with PyQt6 UI code generator.

from PyQt6 import QtCore, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1100, 540)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)

        self.sidebar_layout = QtWidgets.QVBoxLayout()
        self.sidebar_title = QtWidgets.QLabel("Разделы")
        self.sidebar_layout.addWidget(self.sidebar_title)
        self.category_list = QtWidgets.QListWidget(parent=self.centralwidget)
        self.category_list.setMinimumWidth(160)
        self.category_list.setMaximumWidth(220)
        self.sidebar_layout.addWidget(self.category_list)

        self.add_category_button = QtWidgets.QPushButton("＋ Создать категорию", parent=self.centralwidget)
        self.sidebar_layout.addWidget(self.add_category_button)
        self.delete_category_button = QtWidgets.QPushButton("Удалить категорию", parent=self.centralwidget)
        self.sidebar_layout.addWidget(self.delete_category_button)
        self.main_layout.addLayout(self.sidebar_layout)

        self.content_layout = QtWidgets.QVBoxLayout()
        self.search_input = QtWidgets.QLineEdit(parent=self.centralwidget)
        self.search_input.setPlaceholderText("Поиск по сервису, логину и заметкам...")
        self.content_layout.addWidget(self.search_input)

        self.passwords_table = QtWidgets.QTableWidget(parent=self.centralwidget)
        self.passwords_table.setObjectName("passwords_table")
        self.content_layout.addWidget(self.passwords_table, 1)

        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Добавить", parent=self.centralwidget)
        self.edit_button = QtWidgets.QPushButton("Редактировать", parent=self.centralwidget)
        self.delete_button = QtWidgets.QPushButton("Удалить", parent=self.centralwidget)
        self.copy_password_button = QtWidgets.QPushButton("Копировать пароль", parent=self.centralwidget)
        self.import_export_button = QtWidgets.QPushButton("Импорт и экспорт", parent=self.centralwidget)
        self.buttons_layout.addWidget(self.add_button)
        self.buttons_layout.addWidget(self.edit_button)
        self.buttons_layout.addWidget(self.delete_button)
        self.buttons_layout.addWidget(self.copy_password_button)
        self.buttons_layout.addWidget(self.import_export_button)
        self.content_layout.addLayout(self.buttons_layout)
        self.main_layout.addLayout(self.content_layout, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("Менеджер паролей")
