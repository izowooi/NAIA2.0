# tabs/storyteller/story_item_widget.py

import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize

from ui.theme import DARK_COLORS

class StoryItemWidget(QFrame):
    """
    썸네일 이미지, 변수명, 내부 데이터를 가지는 최소 단위 위젯.
    자신의 데이터를 파일로 저장하고 불러오는 책임을 가집니다.
    """
    def __init__(self, project_path: str, group_name: str, variable_name: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.group_name = group_name
        self.variable_name = variable_name
        
        # 데이터 파일 경로 설정
        self.base_path = Path(self.project_path) / self.group_name
        self.image_path = self.base_path / f"{self.variable_name}.png"
        self.json_path = self.base_path / f"{self.variable_name}.json"
        
        self.data = {}
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setFixedSize(128, 160)
        self.setStyleSheet(f"""
            StoryItemWidget {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 4px;
            }}
            StoryItemWidget:hover {{
                border: 1px solid {DARK_COLORS['accent_blue']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(112, 112)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"background-color: {DARK_COLORS['bg_primary']}; border-radius: 3px;")
        
        self.name_label = QLabel(self.variable_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(f"color: {DARK_COLORS['text_primary']}; font-size: 13px;")

        layout.addWidget(self.thumbnail_label)
        layout.addWidget(self.name_label)

    def load_data(self):
        """파일에서 이미지와 JSON 데이터를 로드합니다."""
        try:
            # 이미지 로드
            if self.image_path.exists():
                pixmap = QPixmap(str(self.image_path))
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.thumbnail_label.setText("No Image")

            # JSON 데이터 로드
            if self.json_path.exists():
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            
        except Exception as e:
            print(f"Error loading data for {self.variable_name}: {e}")

    def save_data(self):
        """현재 데이터를 이미지와 JSON 파일로 저장합니다."""
        try:
            # 폴더가 없으면 생성
            self.base_path.mkdir(parents=True, exist_ok=True)

            # 이미지 저장
            pixmap = self.thumbnail_label.pixmap()
            if pixmap and not pixmap.isNull():
                pixmap.save(str(self.image_path), "PNG")

            # JSON 데이터 저장
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving data for {self.variable_name}: {e}")