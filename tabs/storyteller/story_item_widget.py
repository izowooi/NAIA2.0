import os
import json
from pathlib import Path
import base64
from io import BytesIO

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap, QMouseEvent, QDrag
from PyQt6.QtCore import Qt, QSize, QMimeData, QBuffer, QIODevice

from ui.theme import DARK_COLORS

class StoryItemWidget(QFrame):
    """
    썸네일 이미지와 데이터를 JSON 파일 하나로 관리하는 위젯.
    """
    def __init__(self, project_path: str, group_name: str, variable_name: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.group_name = group_name
        self.variable_name = variable_name
        
        # ▼▼▼▼▼ [수정] image_path 제거, json_path만 사용 ▼▼▼▼▼
        self.base_path = Path(self.project_path) / self.group_name
        self.json_path = self.base_path / f"{self.variable_name}.json"
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
        self.data = {}
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # ... [UI 구성 코드는 이전과 동일] ...
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
        """JSON 파일에서 데이터와 Base64 인코딩된 이미지를 로드합니다."""
        try:
            if self.json_path.exists():
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                # ▼▼▼▼▼ [수정] JSON에서 이미지 데이터 로드 ▼▼▼▼▼
                thumbnail_b64 = self.data.get("thumbnail_base64")
                if thumbnail_b64:
                    # Base64 문자열을 이미지 바이트로 디코딩
                    image_bytes = base64.b64decode(thumbnail_b64)
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_bytes, "PNG")
                    self.thumbnail_label.setPixmap(pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    self.thumbnail_label.setText("No Image")
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            else:
                 self.thumbnail_label.setText("No Image")
        except Exception as e:
            print(f"Error loading data for {self.variable_name}: {e}")

    def save_data(self):
        """현재 데이터를 JSON 파일로 저장 (이미지는 Base64로 인코딩하여 포함)."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)

            # ▼▼▼▼▼ [수정] 이미지를 Base64 문자열로 변환하여 data에 추가 ▼▼▼▼▼
            pixmap = self.thumbnail_label.pixmap()
            if pixmap and not pixmap.isNull():
                # QPixmap -> bytes 변환
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                pixmap.save(buffer, "PNG")
                image_bytes = buffer.data()
                
                # bytes -> Base64 문자열 변환
                thumbnail_b64 = base64.b64encode(image_bytes).decode('ascii')
                self.data["thumbnail_base64"] = thumbnail_b64
            else:
                # 이미지가 없으면 데이터에서 키 제거
                self.data.pop("thumbnail_base64", None)
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

            # JSON 데이터 저장
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving data for {self.variable_name}: {e}")

    def mouseMoveEvent(self, event: QMouseEvent):
        # ... [드래그앤드롭 로직은 이전과 동일] ...
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            drag_data = {
                "source": "StoryItemWidget",
                "project_path": self.project_path,
                "group_name": self.group_name,
                "variable_name": self.variable_name
            }
            mime_data.setText(json.dumps(drag_data))
            drag.setMimeData(mime_data)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            drag.exec(Qt.DropAction.CopyAction)