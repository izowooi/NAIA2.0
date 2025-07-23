# tabs/storyteller/story_box.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QSizePolicy, QToolButton, QMenu,
    QLabel, QInputDialog, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QAction

from ui.theme import DARK_STYLES, DARK_COLORS
from tabs.storyteller.story_item_widget import StoryItemWidget

class StoryBox(QWidget):
    subgroup_add_requested = pyqtSignal(str, str) # parent_group_name, new_group_name

    def __init__(self, title: str, variable_name: str, description: str = "", level: str = 'upper', parent=None):
        super().__init__(parent)
        self.title = title
        self.variable_name = variable_name
        self.level = level
        self.description = description
        
        self.child_boxes = {} # 하위 StoryBox 인스턴스 저장
        self.items = {}  # StoryItemWidget 인스턴스 저장

        self.setStyleSheet(DARK_STYLES['collapsible_box'])
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(8, 6, 8, 8)

        self.toggle_button = QToolButton(text=f" {self.title}", checkable=True, checked=True)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_button.toggled.connect(self.on_toggled)
        
        if self.level == 'upper':
            self.toggle_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.toggle_button.customContextMenuRequested.connect(self.show_context_menu)
        
        self.description_label = QLabel(self.description)
        self.description_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; padding: 0px 10px 5px 10px;")
        self.description_label.setVisible(bool(self.description))
        self.description_label.setWordWrap(True)

        self.content_area = QScrollArea()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_area.setWidgetResizable(True)
        self.content_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        content_widget = QWidget()
        # ▼▼▼▼▼ [수정] 레벨에 따라 다른 레이아웃 사용 ▼▼▼▼▼
        if self.level == 'upper':
            # UpperLevel은 하위 StoryBox들을 담기 위해 QVBoxLayout 사용
            self.content_layout = QVBoxLayout(content_widget)
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        else: # 'lower'
            # LowerLevel은 StoryItemWidget들을 담기 위해 QGridLayout 사용
            self.content_layout = QGridLayout(content_widget)
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        self.content_layout.setSpacing(8)
        self.content_area.setWidget(content_widget)

        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.content_area)

    def show_context_menu(self, position: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {DARK_COLORS['bg_tertiary']}; color: {DARK_COLORS['text_primary']}; border: 1px solid {DARK_COLORS['border']}; }}
            QMenu::item:selected {{ background-color: {DARK_COLORS['accent_blue']}; }}
        """)
        
        add_subgroup_action = QAction("➕ 하위 그룹 추가", self)
        add_subgroup_action.triggered.connect(self._request_add_subgroup)
        menu.addAction(add_subgroup_action)
        
        menu.exec(self.toggle_button.mapToGlobal(position))

    def _request_add_subgroup(self):
        """하위 그룹 이름 입력을 위한 다이얼로그를 띄웁니다."""
        text, ok = QInputDialog.getText(self, '하위 그룹 추가', '새 하위 그룹의 이름을 입력하세요 (영문, 숫자, _만 가능):')
        if ok and text:
            # ▼▼▼▼▼ [수정] 자기 자신의 정보만 담아 시그널 발생 ▼▼▼▼▼
            self.subgroup_add_requested.emit(self.variable_name, text)

    def on_toggled(self, checked):
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.description_label.setVisible(checked and bool(self.description))
        self.content_area.setVisible(checked)

    def add_subgroup(self, story_box_widget):
        """하위 StoryBox를 QVBoxLayout에 추가합니다 (UpperLevel 전용)."""
        if self.level == 'upper' and isinstance(self.content_layout, QVBoxLayout):
            self.content_layout.addWidget(story_box_widget)
            self.child_boxes[story_box_widget.variable_name] = story_box_widget
        else:
            print(f"Warning: {self.title} is not an UpperLevel box.")

    def add_item(self, item_widget: StoryItemWidget):
        """StoryItemWidget을 그리드 레이아웃에 추가합니다 (LowerLevel 전용)."""
        if self.level == 'lower' and isinstance(self.content_layout, QGridLayout):
            row = len(self.items) // 4
            col = len(self.items) % 4
            self.content_layout.addWidget(item_widget, row, col)
            self.items[item_widget.variable_name] = item_widget
        else:
            print(f"Warning: {self.title} is not a LowerLevel box.")