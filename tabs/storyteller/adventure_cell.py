import uuid
import json
import base64
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel, 
    QTextEdit, QScrollArea, QSizePolicy, QSplitter, QComboBox, QCheckBox, QGridLayout, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QColor, QAction, QMouseEvent
from typing import TYPE_CHECKING, Optional, Dict, Any

from ui.theme import DARK_STYLES, DARK_COLORS, CUSTOM
from tabs.storyteller.testbench_widget import TestbenchWidget
from tabs.storyteller.cloned_story_item import ClonedStoryItem
from PIL import Image
from PIL.ImageQt import ImageQt

if TYPE_CHECKING:
    from tabs.storyteller.adventure_tab import AdventureTab

class StableImageWidget(QWidget):
    """
    paintEvent를 직접 구현하여 resize 루프를 원천적으로 방지하는
    안정적인 이미지 표시 위젯.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setPixmap(self, pixmap: QPixmap):
        """표시할 원본 QPixmap을 설정하고, 위젯에 다시 그리도록 요청합니다."""
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
        else:
            self._pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(DARK_COLORS['bg_secondary']))
        if not self._pixmap:
            painter.setPen(QColor(DARK_COLORS['text_secondary']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "결과 이미지가 여기에 표시됩니다...")
            return
        widget_size = self.size()
        square_size = min(widget_size.width(), widget_size.height())
        scaled_pixmap = self._pixmap.scaled(
            QSize(square_size, square_size),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        x = (widget_size.width() - scaled_pixmap.width()) // 2
        y = (widget_size.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

    def resizeEvent(self, event):
        """위젯 크기가 변경될 때 자동으로 이미지를 다시 그립니다."""
        super().resizeEvent(event)
        # 크기 변경 후 이미지 다시 그리기
        self.update()


class CharacterWidget(QFrame):
    context_menu_requested = pyqtSignal(QPoint)

    def __init__(self, character_data, variable_name, parent=None):
        super().__init__(parent)
        self.character_data = character_data
        self.variable_name = variable_name
        
        self.setFixedSize(130, 160)
        self.setStyleSheet(f"""
            CharacterWidget {{
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 6px;
                background-color: {DARK_COLORS['bg_secondary']};
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
        
        self.load_character_display()

    def load_character_display(self):
        """캐릭터 데이터로부터 썸네일을 로드하여 표시합니다."""
        thumbnail_b64 = self.character_data.get("thumbnail_base64")
        if thumbnail_b64:
            try:
                image_bytes = base64.b64decode(thumbnail_b64)
                pixmap = QPixmap()
                pixmap.loadFromData(image_bytes, "PNG")
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            except Exception as e:
                self.thumbnail_label.setText("Image Error")
                print(f"Error decoding thumbnail for {self.variable_name}: {e}")
        else:
            self.thumbnail_label.setText("No Image")

    def update_character(self, character_data, variable_name):
        """새로운 캐릭터 데이터로 위젯의 표시 내용을 업데이트합니다."""
        self.character_data = character_data
        self.variable_name = variable_name
        self.name_label.setText(variable_name)
        self.load_character_display() # 썸네일 새로고침

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

class CharacterFrame(QFrame):
    remove_requested = pyqtSignal(object)
    swap_requested = pyqtSignal(str, str) # source_name, target_name

    def __init__(self, character_full_data: dict, variable_name: str, storyteller_tab, parent=None):
        super().__init__(parent)
        self.setFixedHeight(180)
        self.storyteller_tab = storyteller_tab
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(8)

        # ▼▼▼▼▼ [수정] 불필요한 QFrame을 제거하고 레이아웃 구조 단순화 ▼▼▼▼▼
        # 1. 왼쪽 패널을 위한 QVBoxLayout을 직접 생성
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(4,4,4,4)

        # 2. 삭제 버튼을 담을 헤더 레이아웃
        remove_button = QPushButton("x")
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet(f"color: {DARK_COLORS['error']}; border: none; font-weight: bold;")
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(remove_button)
        
        # 3. 캐릭터 위젯 생성
        self.char_widget = CharacterWidget(character_full_data, variable_name)
        self.char_widget.setFixedWidth(130) # 너비 고정

        # 4. 왼쪽 패널 레이아웃에 헤더와 캐릭터 위젯 추가
        left_panel_layout.addLayout(header_layout)
        left_panel_layout.addWidget(self.char_widget)
        left_panel_layout.addStretch()

        # 5. 오른쪽: Testbench 위젯
        testbench_config = {
            'placeholder_text': "Drop non-character items here...",
            'accept_filter': lambda data: not data.get("isCharacter"),
            'origin_tag': 'adventure_character_item_bench' # 고유 태그 부여
        }
        self.testbench = TestbenchWidget(storyteller_tab=storyteller_tab, config=testbench_config)

        # 6. 메인 레이아웃에 왼쪽 패널 레이아웃과 테스트벤치 추가
        main_layout.addLayout(left_panel_layout)
        main_layout.addWidget(self.testbench, 1)

        self.char_widget.context_menu_requested.connect(self.show_swap_context_menu)

    def show_swap_context_menu(self, global_pos: QPoint):
        adventure_tab: AdventureTab = self.storyteller_tab.right_panel.widget(1)
        if not hasattr(adventure_tab, 'character_testbench'): return
            
        # character_testbench에서 현재 캐릭터를 제외한 목록 가져오기
        other_items = adventure_tab.character_testbench.get_other_items(self.char_widget.variable_name)
        if not other_items: return

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {DARK_COLORS['bg_tertiary']}; color: white; border: 1px solid #555; }} QMenu::item:selected {{ background-color: {DARK_COLORS['accent_blue']}; }}")
        
        title_action = QAction("Switch to...", self); title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        for item in other_items:
            action = QAction(item.variable_name, self)
            action.triggered.connect(
                lambda checked=False, target_name=item.variable_name:
                self.swap_requested.emit(self.char_widget.variable_name, target_name)
            )
            menu.addAction(action)
        
        menu.exec(global_pos)

    def get_data(self) -> dict:
        return {
            "character_variable_name": self.char_widget.variable_name,
            "character_full_data": self.char_widget.character_data,
            "testbench_items": self.testbench.get_items_data()
        }

class CharacterDropZone(QFrame):
    character_dropped = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.default_style = f"""
            CharacterDropZone {{
                border: 2px dashed {DARK_COLORS['border_light']};
                border-radius: 8px;
                background-color: {DARK_COLORS['bg_secondary']};
            }}
        """
        self.active_style = f"""
            CharacterDropZone {{
                border: 2px solid {DARK_COLORS['accent_blue']};
                border-radius: 8px;
                background-color: #2B2B2B;
            }}
        """
        self.setStyleSheet(self.default_style)
        
        layout = QVBoxLayout(self)
        self.placeholder_label = QLabel("Character Drag & Drop (상단벤치)")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("border: none; color: #FFFFFF; background: transparent;")
        layout.addWidget(self.placeholder_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data.hasText():
            try:
                data = json.loads(mime_data.text())
                if (data.get("source") == "ClonedStoryItem" and 
                    data.get("origin_tag") == "adventure_character_bench"):
                    event.acceptProposedAction()
                    self.setStyleSheet(self.active_style) # 활성 스타일 적용
                    return
            except (json.JSONDecodeError, KeyError):
                pass
        
        event.ignore()

    def dragLeaveEvent(self, event):
        """드래그가 위젯 밖으로 나가면 기본 스타일로 복원합니다."""
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        data = json.loads(mime_data.text())
        self.character_dropped.emit(data)
        self.setStyleSheet(self.default_style)

class Cell(QFrame):
    remove_requested = pyqtSignal(object)
    clone_requested = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    insert_below_requested = pyqtSignal(object)

    def __init__(self, manager, master_resolution_combo: QComboBox, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.id = str(uuid.uuid4())
        self.character_frames = []
        self.left_layout = None
        self.content_layout = None
        self.left_panel = None # left_panel 참조를 위해 추가
        self.right_panel = None # right_panel 참조를 위해 추가
        self.setStyleSheet(f"border: 1px solid {DARK_COLORS['border']}; border-radius: 6px;")
        self.master_resolution_combo = master_resolution_combo 
        self.init_ui()

    def init_ui(self):  
        self.main_layout = QVBoxLayout(self)
        
        # 1. 상단: 입력 패널과 출력 패널을 담을 수평 레이아웃 (Splitter -> QHBoxLayout)
        self.content_layout = QHBoxLayout()

        self.left_panel = self._create_left_panel()
        self.right_panel = self._create_right_panel()
        
        self.content_layout.addWidget(self.left_panel, 1) # 1:1 비율
        self.content_layout.addWidget(self.right_panel, 1) # 1:1 비율
        
        self.main_layout.addLayout(self.content_layout)

        # 2. 하단: 컨트롤 버튼 영역
        control_layout = self._create_control_layout()
        self.main_layout.addLayout(control_layout)

    def _create_left_panel(self) -> QWidget:
        """입력 관련 위젯들을 담는 왼쪽 패널을 생성합니다."""
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        
        self.in_label = QLabel("In []:")
        self.in_label.setStyleSheet("font-weight: bold; color: #FFFFFF; margin-bottom: 5px;")
        self.left_layout.addWidget(self.in_label)

        prompt_layout = QHBoxLayout()
        self.positive_prompt_edit = QTextEdit(); self.positive_prompt_edit.setPlaceholderText("Positive Prompt...")
        self.negative_prompt_edit = QTextEdit(); self.negative_prompt_edit.setPlaceholderText("Negative Prompt...")
        self.positive_prompt_edit.setStyleSheet(DARK_STYLES['compact_textedit'])
        self.negative_prompt_edit.setStyleSheet(DARK_STYLES['compact_textedit'])
        self.positive_prompt_edit.setFixedHeight(140)
        self.negative_prompt_edit.setFixedHeight(140)
        prompt_layout.addWidget(self.positive_prompt_edit)
        prompt_layout.addWidget(self.negative_prompt_edit)
        self.left_layout.addLayout(prompt_layout)

        self.global_events_testbench = TestbenchWidget(
            storyteller_tab=self.manager.storyteller_tab,
            config={'placeholder_text': "Global Event Drag & Drop (Testbench)", 'accept_filter': lambda data: not data.get("isCharacter")}
        )
        self.left_layout.addWidget(self.global_events_testbench)
        
        self.character_drop_zone = CharacterDropZone()
        self.character_drop_zone.character_dropped.connect(self.add_character_frame)
        self.left_layout.addWidget(self.character_drop_zone)

        return left_widget

    def _create_right_panel(self) -> QWidget:
        """출력 관련 위젯들을 담는 오른쪽 패널을 생성합니다."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.out_label = QLabel("Out []:")
        self.out_label.setStyleSheet("font-weight: bold; color: #FFFFFF; margin-bottom: 5px;")
        right_layout.addWidget(self.out_label)

        self.output_image_widget = StableImageWidget()
        right_layout.addWidget(self.output_image_widget)
        
        return right_widget
        
    def _create_control_layout(self) -> QVBoxLayout:
        """하단 컨트롤 버튼 레이아웃을 생성합니다."""
        # 메인 컨트롤 레이아웃 (수직)
        main_control_layout = QVBoxLayout()
        main_control_layout.setSpacing(8)

        # 윗줄: 해상도 및 시드 설정
        top_row_layout = QGridLayout()
        top_row_layout.setSpacing(8)

        # 해상도 콤보박스 (마스터 복제)
        self.resolution_combo = QComboBox()
        for i in range(self.master_resolution_combo.count()):
            self.resolution_combo.addItem(self.master_resolution_combo.itemText(i))
        self.resolution_combo.setCurrentText(self.master_resolution_combo.currentText())
        self.resolution_combo.setStyleSheet(DARK_STYLES['compact_combobox'])
        self.resolution_combo.setMaximumWidth(200)  # 최대 너비 설정

        self.seed_reuse_checkbox = QCheckBox("시드 재사용")
        self.seed_reuse_checkbox.setFixedWidth(160)  # 체크박스 고정 너비
        self.seed_reuse_checkbox.setStyleSheet(f"{DARK_STYLES['dark_checkbox']}; color: #FFFFFF;")

        # 그리드 레이아웃에 위젯 배치
        top_row_layout.addWidget(self.resolution_combo, 0, 0, Qt.AlignmentFlag.AlignLeft)
        top_row_layout.addWidget(self.seed_reuse_checkbox, 0, 1, Qt.AlignmentFlag.AlignLeft)


        # 아랫줄: 기존 제어 버튼
        bottom_row_layout = QHBoxLayout()
        run_button = QPushButton("Run / Rerun .."); run_button.setStyleSheet(DARK_STYLES['primary_button'])
        run_button.clicked.connect(self.run)
        insert_below_button = QPushButton("➕ Insert Cell Below"); insert_below_button.setStyleSheet(DARK_STYLES['secondary_button'])
        up_button = QPushButton("▲"); up_button.setStyleSheet(DARK_STYLES['secondary_button'])
        up_button.clicked.connect(lambda: self.move_up_requested.emit(self))
        
        down_button = QPushButton("▼"); down_button.setStyleSheet(DARK_STYLES['secondary_button'])
        down_button.clicked.connect(lambda: self.move_down_requested.emit(self))
        
        clone_button = QPushButton("Clone"); clone_button.setStyleSheet(DARK_STYLES['secondary_button'])
        clone_button.clicked.connect(lambda: self.clone_requested.emit(self))
        remove_button = QPushButton("Remove"); remove_button.setStyleSheet(f"{DARK_STYLES['secondary_button']} color: {DARK_COLORS['error']};")
        
        bottom_row_layout.addWidget(run_button)
        bottom_row_layout.addWidget(insert_below_button)
        bottom_row_layout.addStretch()
        bottom_row_layout.addWidget(up_button); bottom_row_layout.addWidget(down_button)
        bottom_row_layout.addWidget(clone_button); bottom_row_layout.addWidget(remove_button)
        
        # 시그널 연결
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        insert_below_button.clicked.connect(lambda: self.insert_below_requested.emit(self))

        main_control_layout.addLayout(top_row_layout)
        main_control_layout.addLayout(bottom_row_layout)

        return main_control_layout

    def set_input_panel_visible(self, visible: bool):
        """왼쪽 입력 패널의 표시 여부를 너비 조절을 통해 설정합니다."""
        if self.left_panel:
            if visible:
                # 보이기: 너비 제한을 풀어 원래 크기로 복원
                self.left_panel.setMaximumWidth(16777215) 
                self.left_panel.setVisible(True)
            else:
                # 숨기기: 너비를 0으로 만들어 공간을 차지하지 않게 함
                self.left_panel.setMaximumWidth(0)

    def add_character_frame(self, dropped_data: dict):
        if len(self.character_frames) >= 6:
            return

        character_full_data = dropped_data.get("full_data")
        variable_name = dropped_data.get("variable_name")
        if not character_full_data or not variable_name:
            print("❌ 드롭된 데이터에 full_data 또는 variable_name이 없습니다.")
            return

        new_frame = CharacterFrame(character_full_data, variable_name, self.manager.storyteller_tab)
        new_frame.remove_requested.connect(self.remove_character_frame)
        new_frame.swap_requested.connect(self.manager.handle_character_swap)
        self.left_layout.insertWidget(self.left_layout.indexOf(self.character_drop_zone), new_frame)
        self.character_frames.append(new_frame)
        
        self.update_character_drop_zone_visibility()
    def remove_character_frame(self, frame_to_remove: CharacterFrame):
        if frame_to_remove in self.character_frames:
            self.character_frames.remove(frame_to_remove)
            frame_to_remove.deleteLater()
            self.update_character_drop_zone_visibility()

    def update_character_drop_zone_visibility(self):
        self.character_drop_zone.setVisible(len(self.character_frames) < 6)

    def get_data(self) -> dict:
        character_frames_data = [frame.get_data() for frame in self.character_frames]
        options_data = {
            "resolution_text": self.resolution_combo.currentText(),
            "seed_reuse": self.seed_reuse_checkbox.isChecked()
        }
        return {
            "id": self.id,
            "main_prompt": {
                "positive": self.positive_prompt_edit.toPlainText(),
                "negative": self.negative_prompt_edit.toPlainText()
            },
            "options": options_data,
            "global_testbench_items": self.global_events_testbench.get_items_data(),
            "character_frames": character_frames_data
        }

    def update_index_label(self):
        """CellManager로부터 자신의 인덱스를 받아와 라벨을 업데이트합니다."""
        index = self.manager.get_cell_index(self)
        if index != -1:
            self.in_label.setText(f"In [{index + 1}]:")
            self.out_label.setText(f"Out [{index + 1}]:")
    
    # ✅ Cell이 캐릭터 프레임들에 접근할 수 있는 메서드들
    def get_character_frames(self):
        """모든 CharacterFrame 반환"""
        return self.character_drop_zone.character_frames
    
    def get_character_frame_by_id(self, frame_id):
        """ID로 CharacterFrame 찾기"""
        return self.character_drop_zone.get_character_frame_by_id(frame_id)
    
    def get_character_testbench_items(self, frame_id):
        """특정 캐릭터 프레임의 테스트벤치 아이템들 반환"""
        frame = self.get_character_frame_by_id(frame_id)
        return frame.get_testbench_items() if frame else []
    
    def run(self):
        """CellManager에 이 Cell의 실행을 요청합니다."""
        self.manager.execute_cell_logic(self)

    def set_data(self, data: dict):
        """외부 데이터로 Cell의 UI를 설정합니다. (복제 및 로드 시 사용)"""
        # 1. 메인 프롬프트 및 옵션 설정
        main_prompt = data.get("main_prompt", {})
        self.positive_prompt_edit.setText(main_prompt.get("positive", ""))
        self.negative_prompt_edit.setText(main_prompt.get("negative", ""))
        options = data.get("options", {})
        self.resolution_combo.setCurrentText(options.get("resolution_text", "1024 x 1024"))
        self.seed_reuse_checkbox.setChecked(options.get("seed_reuse", False))

        # 2. Global Testbench 복원
        self.global_events_testbench.load_from_data(data.get("global_testbench_items", []))
            
        # 3. CharacterFrame 목록 복원
        for frame in self.character_frames[:]: # 리스트 복사본으로 순회하며 안전하게 제거
            self.remove_character_frame(frame)
            
        for frame_data in data.get("character_frames", []):
            new_frame = CharacterFrame(
                frame_data.get("character_full_data"),
                frame_data.get("character_variable_name"),
                self.manager.storyteller_tab
            )
            new_frame.remove_requested.connect(self.remove_character_frame)
            new_frame.testbench.load_from_data(frame_data.get("testbench_items", []))
            
            self.left_layout.insertWidget(self.left_layout.indexOf(self.character_drop_zone), new_frame)
            self.character_frames.append(new_frame)
        
        self.update_character_drop_zone_visibility()

    def get_run_parameters(self, character_index_map: dict) -> dict:
        """이미지 생성을 위한 파라미터를 조합하여 반환합니다. (원본 로직 복원)"""
        # 1. Character Frame 데이터 수집
        characters_data = {}
        for frame in self.character_frames:
            char_name = frame.char_widget.variable_name
            char_index = character_index_map.get(char_name)
            
            if char_index is not None:
                print(f"DEBUG: {char_name}의 위치 : {char_index}")
                positive, negative = frame.testbench.get_all_prompts()
                characters_data[char_index] = [positive, negative]
            else:
                print(f"WARNING: Character index for '{char_name}' not found in map.")
        
        # 2. Global Events Testbench 데이터 수집
        global_positive, global_negative = self.global_events_testbench.get_all_prompts()
        global_prompt_data = {"positive": global_positive, "negative": global_negative}

        # 3. 메인 프롬프트 수집
        main_prompt_data = {
            "positive": self.positive_prompt_edit.toPlainText(),
            "negative": self.negative_prompt_edit.toPlainText()
        }

        # 4 & 5. 옵션 수집 (해상도, 시드 재사용)
        res_text = self.resolution_combo.currentText()
        try:
            width, height = map(int, res_text.replace(" ", "").split('x'))
        except ValueError:
            width, height = 1024, 1024 # 파싱 실패 시 기본값
            
        options_data = {
            "width": width, "height": height,
            "seed_reuse": self.seed_reuse_checkbox.isChecked()
        }

        return {
            "id": self.id,
            "characters": characters_data,
            "global_prompt": global_prompt_data,
            "main_prompt": main_prompt_data,
            "options": options_data
        }

class CellManager(QWidget):
    scenario_run_started = pyqtSignal()
    scenario_run_finished = pyqtSignal()

    def __init__(self, app_context, storyteller_tab, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.storyteller_tab = storyteller_tab
        self.cells: list[Cell] = []
        self.master_resolution_combo = self._clone_main_resolution_combo()
        self.running_cell: Cell | None = None
        self.is_scenario_running = False
        self.run_queue: list[Cell] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(10)

        # 1. 최상단 Cell 추가 버튼 영역
        top_control_bar = QFrame()
        top_control_layout = QHBoxLayout(top_control_bar)
        top_control_layout.setContentsMargins(10,0,10,0)
        
        add_top_button = QPushButton("➕ Add Cell to Top")
        add_top_button.setStyleSheet(DARK_STYLES['secondary_button'])
        add_top_button.clicked.connect(self.add_cell_at_top)
        
        top_control_layout.addStretch()
        top_control_layout.addWidget(add_top_button)
        top_control_layout.addStretch()
        main_layout.addWidget(top_control_bar)

        # 2. 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(CUSTOM['middle_scroll_area'])
        
        container = QWidget()
        self.cells_layout = QVBoxLayout(container)
        self.cells_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cells_layout.setSpacing(15)
        self.cells_layout.setContentsMargins(10, 10, 10, 10)
        self.cells_layout.addStretch(1)
        
        self.scroll_area.setWidget(container)
        main_layout.addWidget(self.scroll_area)
        
        QTimer.singleShot(0, self.add_initial_cell)

    def add_cell(self, data=None, index: int = -1):
        """새로운 Cell을 생성하고, 지정된 인덱스에 추가합니다."""
        new_cell = Cell(manager=self, master_resolution_combo=self.master_resolution_combo, parent=self)
        new_cell.remove_requested.connect(self.remove_cell)
        new_cell.clone_requested.connect(self.clone_cell)
        new_cell.move_up_requested.connect(self.move_cell_up)
        new_cell.move_down_requested.connect(self.move_cell_down)
        new_cell.insert_below_requested.connect(self._on_insert_cell_below)

        # 인덱스가 -1이거나 범위를 벗어나면 맨 뒤에 추가
        if index == -1 or index > len(self.cells):
            index = len(self.cells)
        
        self.cells.insert(index, new_cell)
        
        # stretch를 제외한 위치에 삽입
        self.cells_layout.insertWidget(index, new_cell)

        if data:
            new_cell.set_data(data)
        
        self.update_all_cell_controls()

    def remove_cell(self, cell: Cell):
        """셀을 제거합니다."""
        if cell in self.cells:
            self.cells.remove(cell)
            self.cells_layout.removeWidget(cell)
            cell.deleteLater()
            self.update_all_cell_controls()
            
            # ✅ 최소 1개 Cell 유지
            if len(self.cells) == 0:
                QTimer.singleShot(100, self.add_initial_cell)  # 잠시 후 새 Cell 추가

    def _clone_main_resolution_combo(self) -> QComboBox:
        """메인 윈도우의 해상도 콤보박스를 복제하여 반환합니다."""
        main_combo = self.app_context.main_window.resolution_combo
        new_combo = QComboBox()
        for i in range(main_combo.count()):
            new_combo.addItem(main_combo.itemText(i))
        new_combo.setCurrentText(main_combo.currentText())
        return new_combo

    def add_initial_cell(self):
        if not self.cells:
            self.add_cell()

    def add_cell_at_top(self):
        """최상단에 새 Cell을 추가합니다."""
        self.add_cell(index=0)

    def _on_insert_cell_below(self, requesting_cell: Cell):
        """특정 Cell 아래에 새 Cell을 삽입합니다."""
        try:
            index = self.cells.index(requesting_cell)
            self.add_cell(index=index + 1)
        except ValueError:
            print(f"오류: Cell {requesting_cell}을 목록에서 찾을 수 없습니다.")

    def clone_cell(self, cell: Cell):
        """셀을 복제하여 바로 아래에 추가합니다."""
        try:
            index = self.cells.index(cell)
            cell_data = cell.get_data()
            self.add_cell(data=cell_data, index=index + 1)
        except ValueError:
            print(f"오류: 복제할 Cell {cell}을 목록에서 찾을 수 없습니다.")

    def update_all_cell_controls(self):
        """모든 셀의 인덱스 라벨과 시드 재사용 체크박스 상태를 업데이트합니다."""
        for i, cell in enumerate(self.cells):
            # 인덱스 라벨 업데이트
            cell.update_index_label()
            
            # 시드 재사용 체크박스 상태 업데이트
            if i == 0:
                cell.seed_reuse_checkbox.setChecked(False)
                cell.seed_reuse_checkbox.setVisible(False)
            else:
                cell.seed_reuse_checkbox.setVisible(True)
    def get_cell_index(self, cell: Cell) -> int:
        try:
            return self.cells.index(cell)
        except ValueError:
            return -1

    def get_all_data(self) -> list[dict]:
        """모든 Cell의 데이터를 리스트로 취합하여 반환합니다."""
        # 1. AdventureTab의 character_testbench에서 캐릭터 인덱스 맵 생성
        character_index_map = {}
        adventure_tab = self.storyteller_tab.right_panel.widget(1) # AdventureTab 가정
        if hasattr(adventure_tab, 'character_testbench'):
            char_items = adventure_tab.character_testbench.get_all_cloned_items()
            for i, item in enumerate(char_items):
                character_index_map[item.variable_name] = i

        # 2. 각 Cell에서 데이터를 수집
        return [cell.get_data() for cell in self.cells]
    
    def execute_cell_logic(self, cell: Cell):
        if self.running_cell is not None:
            self.app_context.main_window.status_bar.showMessage("⚠️ 다른 Cell이 이미 실행 중입니다.", 3000)
            return

        print(f"--- 🚀 Cell [{self.get_cell_index(cell) + 1}] 실행 시작 ---")
        self.running_cell = cell # 실행 중인 Cell로 설정

        # 1. AdventureTab의 character_testbench에서 검증 데이터 수집
        adventure_tab = self.storyteller_tab.right_panel.widget(1)
        validation_data = {}
        character_index_map = {}
        char_bench_items = []
        if hasattr(adventure_tab, 'character_testbench'):
            char_bench_items = adventure_tab.character_testbench.get_all_cloned_items()
            for i, item in enumerate(char_bench_items):
                positive, negative = adventure_tab.character_testbench.get_prompts_for_item(item)
                validation_data[i] = [positive, negative]
                character_index_map[item.variable_name] = i
        
        # 2. Cell 자체 데이터 수집 (character_index_map 전달)
        cell_data = cell.get_run_parameters(character_index_map)

        # 3. 프롬프트 조합 (이제 Cell에서 인덱싱된 데이터가 바로 넘어옴)
        final_positive, final_negative = self._combine_prompts(cell_data, validation_data, char_bench_items)
        
        # 4. 옵션 수집
        options = cell_data.get("options", {})
        width = options.get("width", 1024); height = options.get("height", 1024)
        seed_reuse = options.get("seed_reuse", False)
        main_seed_fix_checkbox = self.app_context.main_window.seed_fix_checkbox
        if main_seed_fix_checkbox:
            # Cell의 체크박스 상태에 따라 메인 UI의 시드 고정 체크박스를 제어
            main_seed_fix_checkbox.setChecked(seed_reuse)
            if seed_reuse:
                print(f"  🌱 Cell [{self.get_cell_index(cell) + 1}] 시드 재사용 활성화")

        # 5. 최종 파라미터 생성 및 생성 요청
        override_params = {
            "input": final_positive,
            "negative_prompt": final_negative,
            "width": width,
            "height": height,
            "random_resolution": False
        }
        
        print("\n--- 📝 최종 생성 파라미터 ---")
        print(f"  Positive: {override_params['input'][:150]}...")
        print(f"  Negative: {override_params['negative_prompt'][:150]}...")
        print(f"  Resolution: {width}x{height}")
        print("-------------------------------\n")
        
        try:
            auto_generate_checkbox = self.app_context.main_window.generation_checkboxes.get("자동 생성")
            if auto_generate_checkbox.isChecked(): auto_generate_checkbox.setChecked(False)  # 자동 생성 해제
            gen_controller = self.app_context.main_window.generation_controller
            
            # 1. 생성 완료 이벤트를 구독합니다.
            self.app_context.subscribe("generation_completed_for_redirect", self._on_cell_generation_finished)
            
            # 2. 생성 파이프라인을 실행합니다.
            gen_controller.execute_generation_pipeline(overrides=override_params)
            
            self.app_context.main_window.status_bar.showMessage(f"⏳ Cell [{self.get_cell_index(cell) + 1}] 이미지 생성 중...")
        except Exception as e:
            print(f"❌ Cell 생성 요청 실패: {e}")
            self.running_cell = None # 오류 발생 시 상태 초기화
            self.app_context.main_window.status_bar.showMessage(f"❌ 생성 요청 실패: {e}", 5000)


    def _combine_prompts(self, cell_data: dict, validation_data: dict, char_bench_items: list) -> str| str:
        """Cell 데이터와 검증 데이터를 바탕으로 최종 Positive/Negative 프롬프트를 조합합니다."""
        
        # --- Positive Prompt 조합 ---
        main_pos = cell_data.get("main_prompt", {}).get("positive", "")
        global_pos = cell_data.get("global_prompt", {}).get("positive", "")
        char_data_from_cell = cell_data.get("characters", {})
        is_naid4_mode = self._should_use_character_module()
        
        # NAID4 모드일 경우, 캐릭터 프롬프트는 CharacterModule로 보내고 여기서는 비웁니다.
        if is_naid4_mode:
            self._update_character_module_with_testbench(char_bench_items, char_data_from_cell)
            characters_positive = [] # 최종 프롬프트에는 캐릭터 상세 정보 제외
        else:
            # 기존 로직: 캐릭터 프롬프트를 최종 프롬프트에 포함
            characters_positive = []
            char_data_from_cell = cell_data.get("characters", {})
            for char_index, (cell_pos, _) in char_data_from_cell.items():
                base_pos, _ = validation_data.get(char_index, ["", ""])
                characters_positive.append(", ".join(part for part in [base_pos, cell_pos] if part))

        positive_parts = [main_pos, global_pos] + characters_positive
        combined_positive = ", ".join(part for part in positive_parts if part)

        # --- 인물 수 태그 처리 ---
        num_of_boy = 0
        num_of_girl = 0
        num_of_other = 0
        for char_index in char_data_from_cell.keys():
            if 0 <= char_index < len(char_bench_items):
                item = char_bench_items[char_index] 
                pp = item.data.get('description', {}).get('positive_prompt', '').strip()
                identity = pp.split(",")[0].strip().lower() if pp else ""
                if "boy" in identity: num_of_boy += 1
                elif "girl" in identity: num_of_girl += 1
                elif "other" in identity: num_of_other += 1
        
        tags = [tag.strip() for tag in combined_positive.split(',') if tag.strip()]
        if num_of_boy > 0: tags.append(f"{num_of_boy}boy" if num_of_boy == 1 else f"{num_of_boy}boys")
        if num_of_girl > 0: tags.append(f"{num_of_girl}girl" if num_of_girl == 1 else f"{num_of_girl}girls")
        if num_of_other > 0: tags.append(f"{num_of_other}other" if num_of_other == 1 else f"{num_of_other}others")

        person_sets = {"boys": {"1boy", "2boys", "3boys", "4boys", "5boys", "6+boys"}, "girls": {"1girl", "2girls", "3girls", "4girls", "5girls", "6+girls"}, "others": {"1other", "2others", "3others", "4others", "5others", "6+others"}}
        found_person_tags = []
        for category in ["boys", "girls", "others"]:
            i = 0
            while i < len(tags):
                if tags[i] in person_sets[category]:
                    found_person_tags.append(tags.pop(i))
                else: i += 1
        
        final_person_tags = []
        if found_person_tags:
            group_max_tags = {}
            for tag in found_person_tags:
                num = 6 if tag.startswith("6+") else int(re.match(r'(\d+)', tag).group(1)) if re.match(r'(\d+)', tag) else 0
                for group_name, group_set in person_sets.items():
                    if tag in group_set:
                        if group_name not in group_max_tags or num > (6 if group_max_tags[group_name].startswith("6+") else int(re.match(r'(\d+)', group_max_tags[group_name]).group(1))):
                            group_max_tags[group_name] = tag
                        break
            for group_name in ["boys", "girls", "others"]:
                if group_name in group_max_tags:
                    final_person_tags.append(group_max_tags[group_name])
        
        final_positive_prompt = ", ".join(final_person_tags + tags)

        # --- Negative Prompt 조합 ---
        main_neg = cell_data.get("main_prompt", {}).get("negative", "")
        global_neg = cell_data.get("global_prompt", {}).get("negative", "")
        characters_negative = []
        for char_index, (_, cell_neg) in char_data_from_cell.items():
            _, base_neg = validation_data.get(char_index, ["", ""])
            characters_negative.append(", ".join(part for part in [base_neg, cell_neg] if part))
        
        main_ui_negative = self.app_context.main_window.negative_prompt_textedit.toPlainText().strip()
        negative_parts = [main_ui_negative, main_neg, global_neg] + characters_negative
        final_negative_prompt = ", ".join(part for part in negative_parts if part)

        return final_positive_prompt, final_negative_prompt
    
    def _should_use_character_module(self) -> bool:
        """Character Module 사용 조건(NAI API + NAID4 모델)을 체크합니다."""
        try:
            if self.app_context.current_api_mode != 'NAI': return False
            model_text = self.app_context.main_window.model_combo.currentText()
            if 'NAID4' not in model_text: return False
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if not char_module: return False
            print("✅ Character Module 사용 조건 충족: NAI + NAID4")
            return True
        except Exception as e:
            print(f"⚠️ Character Module 조건 체크 실패: {e}")
            return False

    def _update_character_module_with_testbench(self, char_bench_items: list[ClonedStoryItem], char_data_from_cell: dict):
        """TestBench와 Cell의 캐릭터 아이템들을 조합하여 Character Module에 업데이트합니다."""
        try:
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if not char_module: return

            final_characters = []
            final_ucs = []
            
            # 1. char_bench_items를 순회하며 기본 캐릭터 정보 수집
            for i in char_data_from_cell.keys():
                # 인덱스가 char_bench_items의 범위를 벗어나지 않는지 확인
                if 0 <= i < len(char_bench_items):
                    item = char_bench_items[i]
                    
                    # 기본 프롬프트 (character_testbench)
                    base_positive = item.get_enhanced_positive_prompt()
                    base_negative = item.data.get("description", {}).get("negative_prompt", "").strip()
                    
                    # Cell 전용 프롬프트 (char_data_from_cell)
                    cell_positive, cell_negative = char_data_from_cell.get(i, ["", ""])
                    
                    # 프롬프트 조합
                    combined_positive = ", ".join(part for part in [base_positive, cell_positive] if part)
                    combined_negative = ", ".join(part for part in [base_negative, cell_negative] if part)

                    if combined_positive:
                        final_characters.append(combined_positive)
                        final_ucs.append(combined_negative)
            
            if final_characters:
                char_module.modifiable_clone = {'characters': final_characters, 'uc': final_ucs}
                if hasattr(char_module, 'activate_checkbox'):
                    char_module.activate_checkbox.setChecked(True)
                if hasattr(char_module, 'update_processed_display'):
                    char_module.update_processed_display(final_characters, final_ucs)
                print(f"✅ Character Module 업데이트 완료: {len(final_characters)}개 캐릭터")
        except Exception as e:
            print(f"❌ Character Module 업데이트 실패: {e}")

    def _on_cell_generation_finished(self, result: dict):
        """생성된 이미지를 올바른 Cell에 업데이트합니다."""
        # 이벤트 구독 즉시 해제 (일회성)
        self.app_context.subscribers["generation_completed_for_redirect"].remove(self._on_cell_generation_finished)
        
        if not self.running_cell:
            print("⚠️ 실행 중인 Cell 정보가 없어 이미지 업데이트를 건너뜁니다.")
            # 시나리오 실행 중이었다면 중단
            if self.is_scenario_running:
                self.is_scenario_running = False
                self.run_queue.clear()
            return
        try:
            image_object = result
            if isinstance(image_object, Image.Image):
                q_image = ImageQt(image_object)
                pixmap = QPixmap.fromImage(q_image)
                if not pixmap.isNull():
                    self.running_cell.output_image_widget.setPixmap(pixmap)
                    self.scroll_area.ensureWidgetVisible(self.running_cell, 50, 50)
                    self.app_context.main_window.status_bar.showMessage(f"✅ Cell [{self.get_cell_index(self.running_cell) + 1}] 생성 완료!", 3000)
                else:
                    self.app_context.main_window.status_bar.showMessage("❌ QPixmap 변환 실패", 5000)
            else:
                message = result.get('message', '알 수 없는 오류')
                self.app_context.main_window.status_bar.showMessage(f"❌ 생성 실패: {message}", 5000)

        except Exception as e:
            print(f"❌ Cell 이미지 업데이트 중 오류: {e}")
        finally:
            main_seed_fix_checkbox = self.app_context.main_window.seed_fix_checkbox
            if main_seed_fix_checkbox:
                main_seed_fix_checkbox.setChecked(False)
            current_cell_index = self.get_cell_index(self.running_cell)
            print(f"  -> Cell [{current_cell_index + 1}] 작업 완료.")
            
            self.running_cell = None # 현재 셀 실행 완료
            if self.is_scenario_running:
                QTimer.singleShot(500, self._run_next_cell)

    def clone_cell(self, cell: Cell):
        """셀을 복제하여 바로 아래에 추가합니다."""
        try:
            index = self.cells.index(cell)
            # character_index_map은 get_data 내부에서만 의미가 있으므로 빈 dict 전달
            cell_data = cell.get_data() 
            self.add_cell(data=cell_data, index=index + 1)
        except ValueError:
            print(f"오류: 복제할 Cell {cell}을 목록에서 찾을 수 없습니다.")

    def move_cell_up(self, cell: Cell):
        """셀을 위로 한 칸 이동합니다."""
        try:
            index = self.cells.index(cell)
            if index > 0:
                # 리스트와 레이아웃에서 모두 이동
                self.cells.insert(index - 1, self.cells.pop(index))
                self.cells_layout.insertWidget(index - 1, self.cells_layout.takeAt(index).widget())
                self.update_all_cell_controls()
        except ValueError:
            print(f"오류: 이동할 Cell {cell}을 목록에서 찾을 수 없습니다.")

    def move_cell_down(self, cell: Cell):
        """셀을 아래로 한 칸 이동합니다."""
        try:
            index = self.cells.index(cell)
            if index < len(self.cells) - 1:
                # 리스트와 레이아웃에서 모두 이동
                self.cells.insert(index + 1, self.cells.pop(index))
                self.cells_layout.insertWidget(index + 1, self.cells_layout.takeAt(index).widget())
                self.update_all_cell_controls()
        except ValueError:
            print(f"오류: 이동할 Cell {cell}을 목록에서 찾을 수 없습니다.")

    def handle_character_swap(self, source_name: str, target_name: str):
        """모든 Cell을 순회하며 source_name을 target_name으로 교체 또는 맞바꿉니다."""
        print(f"🔄 캐릭터 교체 실행: '{source_name}' -> '{target_name}'")

        adventure_tab = self.storyteller_tab.right_panel.widget(1)
        target_item = adventure_tab.find_character_in_bench(target_name)
        if not target_item:
            print(f"❌ 교체할 대상 '{target_name}'을 찾을 수 없습니다.")
            return

        swapped_or_replaced = False
        for cell in self.cells:
            source_frame, target_frame = None, None
            source_index, target_index = -1, -1

            for i, frame in enumerate(cell.character_frames):
                if frame.char_widget.variable_name == source_name:
                    source_frame, source_index = frame, i
                elif frame.char_widget.variable_name == target_name:
                    target_frame, target_index = frame, i

            if source_frame and target_frame:
                # --- Swap 로직 ---
                print(f"  - Cell [{self.get_cell_index(cell) + 1}]에서 Swap 실행")
                source_item = adventure_tab.find_character_in_bench(source_name)
                if not source_item: continue

                source_frame.char_widget.update_character(target_item.data, target_item.variable_name)
                target_frame.char_widget.update_character(source_item.data, source_item.variable_name)
                swapped_or_replaced = True

            elif source_frame:
                # --- Replace 로직 ---
                print(f"  - Cell [{self.get_cell_index(cell) + 1}]에서 Replace 실행")
                source_frame.char_widget.update_character(target_item.data, target_item.variable_name)
                swapped_or_replaced = True

        # ▼▼▼▼▼ [수정] 모든 루프가 끝난 후 상태 메시지 한 번만 표시 ▼▼▼▼▼
        if swapped_or_replaced:
            self.app_context.main_window.status_bar.showMessage(f"✅ '{source_name}' 캐릭터 관련 프레임 업데이트 완료.", 3000)
            
    def clear_all_cells(self):
        """모든 Cell을 제거하고 초기 상태로 되돌립니다."""
        for cell in self.cells[:]:
            self.remove_cell(cell)
        
        # remove_cell에서 마지막 셀이 제거될 때 add_initial_cell을 호출하므로
        # 여기서는 별도 호출이 필요 없음.
        if not self.cells:
            self.add_initial_cell()

    def load_from_data(self, cells_data: list):
        """데이터 리스트로부터 전체 Cell 목록을 복원합니다."""
        # 1. 기존 셀 모두 제거 (초기 셀 추가 없이)
        for cell in self.cells[:]:
            self.cells.remove(cell)
            self.cells_layout.removeWidget(cell)
            cell.deleteLater()
        
        # 2. 데이터로부터 새 셀들 생성
        if not cells_data:
            self.add_initial_cell() # 데이터가 없으면 초기 셀 하나만 추가
        else:
            for cell_data in cells_data:
                self.add_cell(data=cell_data)

    def run_scenario(self):
        if self.is_scenario_running: return
        if not self.cells: return
        
        self.is_scenario_running = True
        self.run_queue = self.cells.copy()
        self.scenario_run_started.emit()
        
        self.app_context.main_window.status_bar.showMessage(f"🚀 시나리오 실행 시작 (총 {len(self.run_queue)}개 Cell)")
        self._run_next_cell()

    def stop_scenario(self):
        """실행 중인 시나리오를 중단합니다."""
        if not self.is_scenario_running: return
        
        self.is_scenario_running = False
        self.run_queue.clear()
        
        # 현재 실행 중인 생성이 있다면 중단 (구현 필요 시)
        # self.app_context.main_window.generation_controller.cancel_generation()
        
        self.scenario_run_finished.emit()
        self.app_context.main_window.status_bar.showMessage("🛑 시나리오 실행이 중단되었습니다.", 3000)
        print("🛑 시나리오 실행 중단됨.")

    def _run_next_cell(self):
        if not self.is_scenario_running:
            self.scenario_run_finished.emit() # 중단된 경우 상태 복원
            return

        if self.run_queue:
            next_cell = self.run_queue.pop(0)
            self.execute_cell_logic(next_cell)
        else:
            self.is_scenario_running = False
            self.scenario_run_finished.emit()
            self.app_context.main_window.status_bar.showMessage("✅ 시나리오 실행 완료!", 5000)

    def set_immersive_mode(self, enabled: bool):
        """모든 Cell의 Immersive Mode 상태를 설정합니다."""
        for cell in self.cells:
            cell.set_input_panel_visible(not enabled)

    def save_all_cell_images(self, directory: str) -> int:
        """모든 Cell의 출력 이미지를 지정된 디렉토리에 저장합니다."""
        saved_count = 0
        save_path = Path(directory)
        
        for i, cell in enumerate(self.cells):
            if cell.output_image_widget and cell.output_image_widget._pixmap:
                pixmap_to_save = cell.output_image_widget._pixmap
                filename = f"cell_{i+1:03d}.png"
                filepath = save_path / filename
                
                try:
                    pixmap_to_save.save(str(filepath), "PNG")
                    saved_count += 1
                    print(f"  🖼️ 이미지 저장: {filepath}")
                except Exception as e:
                    print(f"❌ '{filename}' 저장 실패: {e}")
        
        return saved_count