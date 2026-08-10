class WhiteNightsTheme:
    @staticmethod
    def get_stylesheet():
        return """
        QWidget {
            background-color: #F8F8F8;
            color: #333333;
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-size: 14px;
        }

        QMainWindow {
            background-color: #F8F8F8;
        }

        QDialog {
            background-color: #F8F8F8;
        }

        QLabel {
            color: #333333;
            padding: 5px 0;
        }

        QLineEdit {
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #FFFFFF;
            selection-background-color: #B2D7F3;
            selection-color: #333333;
        }
        QLineEdit:focus {
            border: 1px solid #0078D7;
        }

        QPushButton {
            background-color: #E1E1E1;
            color: #333333;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 8px 15px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #D4D4D4;
            border-color: #BBBBBB;
        }
        QPushButton:pressed {
            background-color: #C0C0C0;
            border-color: #AAAAAA;
        }
        QPushButton:disabled {
            background-color: #F0F0F0;
            color: #AAAAAA;
            border-color: #E0E0E0;
        }

        QTableWidget {
            background-color: #FFFFFF;
            alternate-background-color: #F5F5F5;
            gridline-color: #E0E0E0;
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            selection-background-color: #B2D7F3;
            selection-color: #333333;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #B2D7F3;
            color: #333333;
        }

        QHeaderView::section {
            background-color: #E1E1E1;
            color: #333333;
            padding: 6px;
            border: 1px solid #CCCCCC;
            border-bottom: 2px solid #0078D7;
            font-weight: bold;
        }
        """