from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QFrame, QMessageBox
from ui.theme import DARK_COLORS, DARK_STYLES

def style_qmessagebox(msg_box: QMessageBox):
    """QMessageBox 인스턴스에 커스텀 다크 테마 스타일을 적용합니다."""
    msg_box.setStyleSheet(f"""
        QMessageBox {{
            background-color: {DARK_COLORS['bg_secondary']};
        }}
        QLabel {{
            color: {DARK_COLORS['text_primary']};
            font-size: 14px;
        }}
        QPushButton {{
            background-color: {DARK_COLORS['bg_tertiary']};
            border: 1px solid {DARK_COLORS['border']};
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {DARK_COLORS['bg_hover']};
        }}
        QPushButton:pressed {{
            background-color: {DARK_COLORS['bg_pressed']};
        }}
    """)

class CustomInputDialog(QDialog):
    """
    어두운 테마에 맞게 스타일링된 커스텀 텍스트 입력 다이얼로그.
    QInputDialog.getText()를 대체합니다.
    """
    def __init__(self, parent=None, title="입력", label="값을 입력하세요:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {DARK_COLORS['bg_secondary']}; }}
            QLabel {{ color: {DARK_COLORS['text_primary']}; font-size: 14px; }}
            QLineEdit {{
                background-color: {DARK_COLORS['bg_primary']};
                border: 1px solid {DARK_COLORS['border']};
                padding: 8px; font-size: 14px;
                color: {DARK_COLORS['text_primary']};
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: {DARK_COLORS['accent_blue']}; color: white;
                font-weight: bold; padding: 8px 16px;
                border: none; border-radius: 4px; font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #1565C0; }}
        """)

        layout = QVBoxLayout(self)
        
        info_label = QLabel(label)
        layout.addWidget(info_label)

        self.text_input = QLineEdit(self)
        self.text_input.setProperty("autocomplete_ignore", True)
        layout.addWidget(self.text_input)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_text(self):
        """입력된 텍스트를 반환합니다."""
        return self.text_input.text().strip()

    @staticmethod
    def getText(parent, title, label):
        """QInputDialog.getText와 유사한 인터페이스를 제공하는 static 메서드."""
        dialog = CustomInputDialog(parent, title, label)
        result = dialog.exec()
        text = dialog.get_text()
        return text, result == QDialog.DialogCode.Accepted
    
class ConfirmationDialog(QDialog):
    """경고 메시지를 포함할 수 있는 커스텀 확인 다이얼로그."""
    def __init__(self, parent=None, title="확인", text="", warning_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(f"background-color: {DARK_COLORS['bg_secondary']};")

        layout = QVBoxLayout(self)
        
        main_text_label = QLabel(text)
        main_text_label.setStyleSheet(f"color: {DARK_COLORS['text_primary']}; font-size: 14px;")
        layout.addWidget(main_text_label)

        if warning_text:
            warning_frame = QFrame()
            warning_frame.setStyleSheet(f"background-color: #4A4A00; border: 1px solid {DARK_COLORS['warning']}; border-radius: 4px;")
            warning_layout = QVBoxLayout(warning_frame)
            
            warning_label = QLabel(warning_text)
            warning_label.setStyleSheet(f"color: {DARK_COLORS['warning']}; font-size: 13px; font-weight: bold; border: none; background-color: transparent;")
            warning_layout.addWidget(warning_label)
            layout.addWidget(warning_frame)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        button_box.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_STYLES['secondary_button']}; color: white;
                font-weight: bold; padding: 8px 16px;
                border: none; border-radius: 4px; font-size: 14px; min-width: 80px;
            }}
        """)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @staticmethod
    def ask(parent, title, text, warning_text=""):
        dialog = ConfirmationDialog(parent, title, text, warning_text)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted