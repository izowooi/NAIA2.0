# tabs/storyteller/item_editor.py

import base64
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QFrame, QMessageBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

from ui.theme import DARK_STYLES, DARK_COLORS, CUSTOM
from tabs.storyteller.story_item_widget import StoryItemWidget
from tabs.storyteller.custom_dialogs import CustomInputDialog, style_qmessagebox

class ItemEditorWidget(QFrame):
    item_deleted = pyqtSignal(object)
    item_saved = pyqtSignal(object, dict)
    regeneration_requested = pyqtSignal(object, dict)
    assign_to_workshop_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item_widget: StoryItemWidget = None
        # ▼▼▼▼▼ [신규] 상태 관리를 위한 변수 추가 ▼▼▼▼▼
        self.is_edit_mode = False
        self.appendix_widgets: dict[str, (QTextEdit, QPushButton)] = {}
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        self.setStyleSheet(f"""
            ItemEditorWidget {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: 1px solid {DARK_COLORS['accent_blue']};
                border-radius: 8px;
                margin-bottom: 8px;
            }}
        """)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_panel_layout = QHBoxLayout()
        
        # 1. 좌측 패널 (썸네일 및 버튼)
        left_panel_layout = QVBoxLayout()
        self.thumbnail_label = QLabel("Thumbnail")
        self.thumbnail_label.setFixedSize(256, 256)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"background-color: {DARK_COLORS['bg_primary']}; border-radius: 5px;")
        
        self.regenerate_button = QPushButton("🔄 Regenerate")
        self.regenerate_button.setStyleSheet(DARK_STYLES['secondary_button'])
        self.assign_workshop_button = QPushButton("➡️ Assign workshop")
        self.assign_workshop_button.setStyleSheet(DARK_STYLES['secondary_button'])
        self.delete_button = QPushButton("❌ Delete")
        self.delete_button.setStyleSheet(f"{DARK_STYLES['secondary_button']} color: {DARK_COLORS['error']};")
        
        left_panel_layout.addWidget(self.thumbnail_label)
        # left_panel_layout.addWidget(self.regenerate_button) # 기능 중복으로 일단 주석처리함
        left_panel_layout.addWidget(self.assign_workshop_button)
        left_panel_layout.addWidget(self.delete_button)
        
        # 2. 중앙 패널 (프롬프트)
        center_panel_layout = QVBoxLayout()
        # ▼▼▼▼▼ [수정] 프롬프트 영역 UI 변경 ▼▼▼▼▼
        positive_group, self.positive_prompt_edit, _ = self._create_prompt_group("Positive Prompt", "아이템의 Positive Prompt...")
        negative_group, self.negative_prompt_edit, _ = self._create_prompt_group("Negative Prompt", "아이템의 Negative Prompt...")
        center_panel_layout.addWidget(positive_group)
        center_panel_layout.addWidget(negative_group)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
        # 3. 우측 패널 (Appendix)
        right_panel_layout = QVBoxLayout()
        # ▼▼▼▼▼ [수정] Appendix 영역을 동적 컨테이너로 변경 ▼▼▼▼▼
        appendix_container_label = QLabel("Appendix Container")
        appendix_container_label.setStyleSheet(DARK_STYLES['label_style'])
        
        appendix_scroll = QScrollArea()
        appendix_scroll.setWidgetResizable(True)
        appendix_scroll.setStyleSheet(CUSTOM['middle_scroll_area'])
        
        appendix_widget = QWidget()
        self.appendix_layout = QVBoxLayout(appendix_widget)
        self.appendix_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        appendix_scroll.setWidget(appendix_widget)
        
        self.add_appendix_button = QPushButton("(+) Add appendix ..")
        self.add_appendix_button.setStyleSheet(f"""
            QPushButton {{
                border: 2px dashed {DARK_COLORS['border']};
                color: {DARK_COLORS['text_secondary']};
                padding: 10px;
                font-style: italic;
            }}
            QPushButton:hover {{
                border-color: {DARK_COLORS['accent_blue']};
                color: {DARK_COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {DARK_COLORS['bg_pressed']};
            }}
            QPushButton:disabled {{
                border-color: {DARK_COLORS['border']};
                color: {DARK_COLORS['text_disabled']};
            }}
        """)
        self.add_appendix_button.clicked.connect(self._on_add_appendix_clicked)

        right_panel_layout.addWidget(appendix_container_label)
        right_panel_layout.addWidget(appendix_scroll)
        right_panel_layout.addWidget(self.add_appendix_button)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        top_panel_layout.addLayout(left_panel_layout, 1)
        top_panel_layout.addLayout(center_panel_layout, 2)
        top_panel_layout.addLayout(right_panel_layout, 2)
        
        # 하단 패널 (저장/닫기 버튼)
        bottom_panel_layout = QHBoxLayout()
        self.modify_save_button = QPushButton("Modify")
        self.modify_save_button.setStyleSheet(DARK_STYLES['primary_button'])
        self.close_discard_button = QPushButton("Close")
        self.close_discard_button.setStyleSheet(f"{DARK_STYLES['secondary_button']} color: {DARK_COLORS['warning']};")

        bottom_panel_layout.addStretch(1)
        bottom_panel_layout.addWidget(self.modify_save_button)
        bottom_panel_layout.addWidget(self.close_discard_button)

        main_layout.addLayout(top_panel_layout)
        main_layout.addLayout(bottom_panel_layout)
        
        # 시그널 연결
        self.modify_save_button.clicked.connect(self._on_modify_save_button_clicked)
        self.close_discard_button.clicked.connect(self._on_close_discard_button_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.regenerate_button.clicked.connect(self._on_regenerate_clicked)
        self.assign_workshop_button.clicked.connect(self._on_assign_to_workshop_clicked)
        

    # ▼▼▼▼▼ [신규] 반복되는 UI 생성을 위한 헬퍼 메서드 ▼▼▼▼▼
    def _create_prompt_group(self, key: str, placeholder: str) -> QWidget| QTextEdit| QPushButton:
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        layout.setContentsMargins(0,0,0,0)
        
        # 제목 라인 (라벨 + 삭제 버튼)
        title_layout = QHBoxLayout()
        label = QLabel(key)
        label.setStyleSheet(DARK_STYLES['label_style'])
        
        delete_button = QPushButton("x")
        delete_button.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; border: none; font-weight: bold;")
        delete_button.setFixedSize(20, 20)
        delete_button.clicked.connect(lambda: self._on_delete_appendix_widget(key, group_widget))
        
        title_layout.addWidget(label)
        title_layout.addStretch()
        title_layout.addWidget(delete_button)
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText(placeholder)
        text_edit.setStyleSheet(DARK_STYLES['compact_textedit'])

        layout.addLayout(title_layout)
        layout.addWidget(text_edit)
        return group_widget, text_edit, delete_button
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    def open_for_item(self, item_widget: StoryItemWidget):
        self.current_item_widget = item_widget
        self.load_item_data()
        self._set_edit_mode(False) # 항상 보기 모드로 시작
        self.show()
    
    def load_item_data(self):
        # ... [이전 로직과 유사하나 Appendix 로딩 방식 변경] ...
        if not self.current_item_widget: return
        data = self.current_item_widget.data
        thumbnail_b64 = data.get("thumbnail_base64")
        if thumbnail_b64:
            pixmap = QPixmap(); pixmap.loadFromData(base64.b64decode(thumbnail_b64), "PNG")
            self.thumbnail_label.setPixmap(pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        desc = data.get("description", {}); self.positive_prompt_edit.setText(desc.get("positive_prompt", "")); self.negative_prompt_edit.setText(desc.get("negative_prompt", ""))
        
        # ▼▼▼▼▼ [수정] 동적 Appendix 위젯 로딩 ▼▼▼▼▼
        # 기존 위젯 모두 제거
        while self.appendix_layout.count():
            item = self.appendix_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.appendix_widgets.clear()

        appendix_data = data.get("appendix", {})
        if not appendix_data: # 기본 explain 필드 추가
            appendix_data["explain"] = "이 item에 대한 description을 작성해주세요."
        
        for key, value in appendix_data.items():
            self._add_appendix_widget(key, value)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    def close_editor(self):
        self.current_item_widget = None
        self.hide()

    # ▼▼▼▼▼ [신규/수정] 상태(Mode) 변경 및 버튼 핸들러 로직 ▼▼▼▼▼
    def _set_edit_mode(self, enabled: bool):
        """보기/수정 모드를 전환하는 중앙 컨트롤 메서드"""
        self.is_edit_mode = enabled
        
        # 모든 입력창 활성화/비활성화
        self.positive_prompt_edit.setReadOnly(not enabled)
        self.negative_prompt_edit.setReadOnly(not enabled)
        for key, (text_edit, delete_button) in self.appendix_widgets.items():
            text_edit.setReadOnly(not enabled)
            if key != "explain":
                delete_button.setVisible(enabled)

        # 버튼 활성화/비활성화 및 텍스트 변경
        self.regenerate_button.setEnabled(enabled)
        self.add_appendix_button.setEnabled(enabled)
        self.delete_button.setEnabled(not enabled) # 삭제는 수정 모드에서 비활성화
        self.assign_workshop_button.setEnabled(not enabled)

        if enabled:
            self.modify_save_button.setText("💾 Save")
            self.close_discard_button.setText("✖️ Discard")
        else:
            self.modify_save_button.setText("✏️ Modify")
            self.close_discard_button.setText("Close")

    def _on_delete_appendix_widget(self, key: str, widget: QWidget):
        widget.deleteLater()
        if key in self.appendix_widgets:
            del self.appendix_widgets[key]

    def _on_assign_to_workshop_clicked(self):
        """Assign workshop 버튼 클릭 시, 현재 아이템의 모든 프롬프트 정보를 시그널로 보냅니다."""
        if not self.current_item_widget: return
        
        data = self.current_item_widget.data
        desc_data = data.get("description", {})
        workshop_data = data.get("workshop", {})
        
        all_prompts = {
            "prefix": workshop_data.get("prefix_prompt", ""),
            "positive": desc_data.get("positive_prompt", ""),
            "postfix": workshop_data.get("postfix_prompt", ""),
            "negative": desc_data.get("negative_prompt", "")
        }
        self.assign_to_workshop_requested.emit(all_prompts)

    def _on_modify_save_button_clicked(self):
        """Modify/Save 버튼 클릭 핸들러"""
        if self.is_edit_mode: # 현재 수정 모드(Save 버튼 상태)일 때
            if not self.current_item_widget: return
        
            # 부가 정보 수집
            new_appendix_data = {key: widgets[0].toPlainText() for key, widgets in self.appendix_widgets.items()}
            new_data = {
                "thumbnail_base64": self.current_item_widget.data.get("thumbnail_base64"),
                "description": {
                    "positive_prompt": self.positive_prompt_edit.toPlainText(),
                    "negative_prompt": self.negative_prompt_edit.toPlainText()
                },
                "appendix": new_appendix_data,
                "workshop": self.current_item_widget.data.get("workshop", {})
            }
            self.item_saved.emit(self.current_item_widget, new_data)
            self._set_edit_mode(False)
        else: # 현재 보기 모드(Modify 버튼 상태)일 때
            self._set_edit_mode(True)

    def _on_close_discard_button_clicked(self):
        """Close/Discard 버튼 클릭 핸들러"""
        if self.is_edit_mode: # 현재 수정 모드(Discard 버튼 상태)일 때
            self.load_item_data() # 데이터 원상 복구
            self._set_edit_mode(False)
        else: # 현재 보기 모드(Close 버튼 상태)일 때
            self.close_editor()

    def _on_add_appendix_clicked(self):
        """Add appendix 버튼 클릭 시 새 속성 추가"""
        key, ok = CustomInputDialog.getText(self, "부가 정보 추가", "추가할 속성의 이름을 입력하세요:")
        if ok and key:
            if key in self.appendix_widgets:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("오류")
                msg_box.setText("이미 존재하는 속성 이름입니다.")
                style_qmessagebox(msg_box)
                msg_box.exec()
                return
            self._add_appendix_widget(key, "") # 빈 값으로 위젯 추가

    def _add_appendix_widget(self, key: str, value: str):
        group, text_edit, delete_button = self._create_prompt_group(key, f"{key}에 대한 내용 입력...")
        text_edit.setText(value)
        text_edit.setReadOnly(not self.is_edit_mode)
        
        # explain 필드는 삭제 버튼을 항상 숨김
        if key == "explain":
            delete_button.hide()
        else:
            delete_button.setVisible(self.is_edit_mode)
        
        self.appendix_layout.addWidget(group)
        self.appendix_widgets[key] = (text_edit, delete_button)
    
    def _on_delete_clicked(self):
        if not self.current_item_widget: return
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle('아이템 삭제')
        msg_box.setText(f"'{self.current_item_widget.variable_name}' 아이템을 정말로 삭제하시겠습니까?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        style_qmessagebox(msg_box) # 스타일 적용
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self.item_deleted.emit(self.current_item_widget)
            self.close_editor()

    def _on_regenerate_clicked(self):
        if not self.current_item_widget: return
        override_params = { "input": self.positive_prompt_edit.toPlainText(), "negative_prompt": self.negative_prompt_edit.toPlainText(), "width": 1024, "height": 1024, "random_resolution": False }
        self.regeneration_requested.emit(self.current_item_widget, override_params)