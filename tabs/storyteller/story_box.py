from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QSizePolicy, QToolButton, QMenu,
    QLabel, QInputDialog, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QEvent
from PyQt6.QtGui import QAction, QMouseEvent

from ui.theme import DARK_STYLES, DARK_COLORS
from tabs.storyteller.story_item_widget import StoryItemWidget
from tabs.storyteller.custom_dialogs import CustomInputDialog
from tabs.storyteller.flow_layout import FlowLayout

class StoryBox(QWidget):
    subgroup_add_requested = pyqtSignal(str, str)
    expanded = pyqtSignal(object)
    focused = pyqtSignal(object)
    collapsed = pyqtSignal(object)

    def __init__(self, title: str, variable_name: str, description: str = "", level: str = 'upper', parent_box=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.variable_name = variable_name
        self.level = level
        self.description = description
        self.parent_box = parent_box
        
        self.is_collapsed = False
        self.child_boxes = {}
        self.items = {}

        self.setStyleSheet(DARK_STYLES['collapsible_box'])
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(8, 6, 8, 8)

        self.toggle_button = QToolButton(text=f" {self.title}", checkable=True, checked=True)
        self.default_style = "QToolButton { background-color: transparent; color: white; }"
        self.focused_style = "QToolButton { background-color: #FAFAD2; color: #000; font-weight: bold; }"
        self.toggle_button.setStyleSheet(self.default_style)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_button.toggled.connect(self.on_toggled)
        self.toggle_button.installEventFilter(self)
        
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
        self.content_area.installEventFilter(self)
        self.content_area.viewport().installEventFilter(self)
        content_widget = QWidget()
        if self.level == 'upper':
            self.content_layout = QVBoxLayout(content_widget)
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        else:
            self.content_layout = QGridLayout(content_widget)
            self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content_layout.setSpacing(8)
        self.content_area.setWidget(content_widget)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.content_area)

    def eventFilter(self, obj, event: QEvent) -> bool:
        # 감시 대상(obj)이 타이틀 버튼, 콘텐츠 영역, 또는 그 내부 viewport이고,
        # 이벤트가 마우스 버튼 누름일 때 focused 시그널을 발생시킵니다.
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj in [self.toggle_button, self.content_area, self.content_area.viewport()]:
                self.focused.emit(self)
        
        # 자식 위젯(StoryItemWidget)에서 온 이벤트인지 확인
        if isinstance(obj, StoryItemWidget) and event.type() == QEvent.Type.MouseButtonPress:
            self.focused.emit(self)

        return super().eventFilter(obj, event)
    
    def mousePressEvent(self, event: QMouseEvent):
        self.focused.emit(self)
        super().mousePressEvent(event)
    
    def show_context_menu(self, position: QPoint):
        menu = QMenu(self); menu.setStyleSheet(f"QMenu {{ background-color: {DARK_COLORS['bg_tertiary']}; color: {DARK_COLORS['text_primary']}; border: 1px solid {DARK_COLORS['border']}; }} QMenu::item:selected {{ background-color: {DARK_COLORS['accent_blue']}; }}")
        add_subgroup_action = QAction("➕ 하위 그룹 추가", self); add_subgroup_action.triggered.connect(self._request_add_subgroup); menu.addAction(add_subgroup_action)
        menu.exec(self.toggle_button.mapToGlobal(position))

    def _request_add_subgroup(self):
        text, ok = CustomInputDialog.getText(self, '하위 그룹 추가', '새 하위 그룹의 이름을 입력하세요:')
        if ok and text: self.subgroup_add_requested.emit(self.variable_name, text)

    def on_toggled(self, checked):
        self.is_collapsed = not checked
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.description_label.setVisible(checked and bool(self.description))
        self.content_area.setVisible(checked)
        if checked: 
            self.expanded.emit(self)
        else:
            self.collapsed.emit(self)

    def collapse(self): self.toggle_button.setChecked(False)

    def set_focused(self, is_focused: bool):
        if is_focused: self.toggle_button.setStyleSheet(self.focused_style)
        else: self.toggle_button.setStyleSheet(self.default_style)
        
    def add_subgroup(self, story_box_widget):
        if self.level == 'upper' and isinstance(self.content_layout, QVBoxLayout):
            # ▼▼▼▼▼ [신규] 추가되는 하위 그룹에도 이벤트 필터 설치 ▼▼▼▼▼
            story_box_widget.installEventFilter(self)
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            self.content_layout.addWidget(story_box_widget)
            self.child_boxes[story_box_widget.variable_name] = story_box_widget
        else: print(f"Warning: {self.title} is not an UpperLevel box.")
        
    def add_item(self, item_widget: StoryItemWidget):
        if self.level == 'lower':
            # ▼▼▼▼▼ [신규] 추가되는 아이템에도 이벤트 필터 설치 ▼▼▼▼▼
            item_widget.installEventFilter(self)
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            self.content_layout.addWidget(item_widget)
            self.items[item_widget.variable_name] = item_widget
        else: print(f"Warning: {self.title} is not a LowerLevel box.")