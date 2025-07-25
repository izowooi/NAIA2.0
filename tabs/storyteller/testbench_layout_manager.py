from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from typing import List, Optional

from tabs.storyteller.cloned_story_item import ClonedStoryItem

class TestbenchRow(QWidget):
    """Testbench의 한 행을 관리하는 위젯 - Horizontal Scroll 지원"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_items_per_row = 12  # 6에서 12로 증가 (단일 행에 모든 아이템)
        self.items: List[ClonedStoryItem] = []
        
        # 드롭 미리보기용 인디케이터
        self.drop_indicator = None
        
        self.init_ui()
    
    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)  # 아이템 간 간격
        self.layout.addStretch()  # 왼쪽 정렬을 위한 stretch
        
        # 초기 최소 너비 설정
        self.update_minimum_width()
        
        # 드롭 인디케이터 생성 (초기에는 숨김)
        self.create_drop_indicator()
    
    def create_drop_indicator(self):
        """드롭 위치를 표시하는 인디케이터 생성"""
        from PyQt6.QtWidgets import QFrame
        from ui.theme import DARK_COLORS
        
        self.drop_indicator = QFrame(self)
        self.drop_indicator.setFixedSize(3, 140)  # 얇은 세로 막대
        self.drop_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 1px;
                border: 1px solid #ffffff;
            }}
        """)
        self.drop_indicator.hide()  # 기본적으로 숨김
    
    def show_drop_indicator(self, index: int):
        """지정된 인덱스 위치에 드롭 인디케이터 표시"""
        if not self.drop_indicator:
            self.create_drop_indicator()
        
        # 인디케이터를 올바른 위치에 배치
        x_pos = self.calculate_indicator_position(index)
        self.drop_indicator.move(x_pos, 10)  # Y는 고정, X만 계산
        self.drop_indicator.show()
        self.drop_indicator.raise_()  # 다른 요소들 위에 표시
    
    def hide_drop_indicator(self):
        """드롭 인디케이터 숨김"""
        if self.drop_indicator:
            self.drop_indicator.hide()
    
    def calculate_indicator_position(self, index: int) -> int:
        """인디케이터가 표시될 X 좌표 계산"""
        if index == 0:
            return 5  # 맨 앞
        elif index >= len(self.items):
            # 맨 뒤
            if self.items:
                last_item = self.items[-1]
                return last_item.x() + last_item.width() + 8
            else:
                return 5
        else:
            # 중간 위치
            target_item = self.items[index]
            return target_item.x() - 8
    
    def can_add_item(self) -> bool:
        """이 행에 아이템을 더 추가할 수 있는지 확인"""
        return len(self.items) < self.max_items_per_row
    
    def add_item(self, item: ClonedStoryItem, index: Optional[int] = None) -> bool:
        """아이템을 지정된 인덱스에 추가"""
        if not self.can_add_item():
            return False
        
        if index is None:
            index = len(self.items)
        
        # 인덱스 범위 검증
        index = max(0, min(index, len(self.items)))
        
        # 아이템을 리스트와 레이아웃에 추가
        self.items.insert(index, item)
        
        # stretch를 제거하고 아이템을 추가 후 다시 stretch 추가
        self.layout.removeItem(self.layout.itemAt(self.layout.count() - 1))  # stretch 제거
        self.layout.insertWidget(index, item)
        self.layout.addStretch()  # stretch 다시 추가
        
        # 최소 너비 업데이트 (스크롤을 위해)
        self.update_minimum_width()
        
        print(f"Added item to row at index {index}, total items: {len(self.items)}")
        return True
    
    def remove_item(self, item: ClonedStoryItem) -> bool:
        """아이템을 제거"""
        if item in self.items:
            self.items.remove(item)
            self.layout.removeWidget(item)
            
            # 최소 너비 업데이트
            self.update_minimum_width()
            
            print(f"Removed item from row, remaining items: {len(self.items)}")
            return True
        return False
    
    def update_minimum_width(self):
        """아이템 개수에 따른 최소 너비 업데이트"""
        if not self.items:
            self.setMinimumWidth(0)
            return
        
        # 아이템 너비(128) + 간격(12) × 아이템 개수 + 여유 공간
        item_width = 128
        spacing = 12
        margin = 20
        
        min_width = len(self.items) * (item_width + spacing) - spacing + margin
        self.setMinimumWidth(min_width)
        
        print(f"Updated minimum width to {min_width} for {len(self.items)} items")
    
    def get_item_index(self, item: ClonedStoryItem) -> int:
        """아이템의 인덱스를 반환"""
        try:
            return self.items.index(item)
        except ValueError:
            return -1
    
    def is_empty(self) -> bool:
        """행이 비어있는지 확인"""
        return len(self.items) == 0
    
    def get_drop_index(self, drop_x: int) -> int:
        """드롭 위치에 따른 삽입 인덱스 계산"""
        if not self.items:
            return 0
        
        for i, item in enumerate(self.items):
            item_center_x = item.x() + item.width() / 2
            if drop_x < item_center_x:
                return i
        
        return len(self.items)


class TestbenchLayoutManager:
    """Testbench의 전체 레이아웃을 관리하는 클래스 - Single Row with Horizontal Scroll"""
    
    def __init__(self, parent_widget: QWidget):
        self.parent_widget = parent_widget
        self.single_row: Optional[TestbenchRow] = None
        self.scroll_area: Optional[QScrollArea] = None
        self.placeholder_label: Optional[QLabel] = None
        self.max_total_items = 12  # 여전히 12개 제한 유지
        self.current_preview_row = None  # 현재 미리보기가 표시된 행 (항상 single_row)
        
        self.init_layout()
    
    def init_layout(self):
        """기본 레이아웃 초기화"""
        self.main_layout = QVBoxLayout(self.parent_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)
        
        # 스크롤 영역 생성
        self.create_scroll_area()
        
        # 플레이스홀더 추가
        self.show_placeholder()
    
    def create_scroll_area(self):
        """가로 스크롤이 가능한 스크롤 영역 생성"""
        self.scroll_area = QScrollArea(self.parent_widget)
        
        # 스크롤 정책 설정
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 스크롤 영역 스타일링
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                border: none;
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #666666;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
        """)
        
        # 위젯 크기 조정 허용
        self.scroll_area.setWidgetResizable(True)
        
        # 고정 높이 설정 (기존 2행 높이와 비슷하게)
        self.scroll_area.setFixedHeight(160)  # 아이템 높이(164) + 여유 공간
        
        # 단일 행 생성
        self.single_row = TestbenchRow()
        self.scroll_area.setWidget(self.single_row)
        
        # 메인 레이아웃에 추가
        self.main_layout.addWidget(self.scroll_area)
        
        # 초기에는 숨김 (플레이스홀더가 표시됨)
        self.scroll_area.hide()
    
    def show_placeholder(self):
        """플레이스홀더 표시"""
        if not self.placeholder_label:
            from ui.theme import DARK_COLORS
            self.placeholder_label = QLabel("[Testbench] Drag & Drop left widget items to here…")
            self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.placeholder_label.setStyleSheet(f"""
                color: {DARK_COLORS['text_secondary']}; 
                border: none; 
                font-size: 18px; 
                background-color: transparent;
                padding: 20px;
            """)
        
        if self.placeholder_label.parent() is None:
            self.main_layout.addWidget(self.placeholder_label)
            self.placeholder_label.show()
        
        # 스크롤 영역 숨김
        if self.scroll_area:
            self.scroll_area.hide()
    
    def hide_placeholder(self):
        """플레이스홀더 숨김"""
        if self.placeholder_label and self.placeholder_label.parent():
            self.main_layout.removeWidget(self.placeholder_label)
            self.placeholder_label.hide()
        
        # 스크롤 영역 표시
        if self.scroll_area:
            self.scroll_area.show()
    
    def can_add_more_items(self) -> bool:
        """더 많은 아이템을 추가할 수 있는지 확인"""
        current_count = self.get_total_item_count()
        return current_count < self.max_total_items
    
    def get_total_item_count(self) -> int:
        """현재 총 아이템 수 반환"""
        if self.single_row:
            return len(self.single_row.items)
        return 0
    
    def show_drop_preview(self, drop_pos) -> bool:
        """드롭 위치 미리보기 표시"""
        if not drop_pos or not self.single_row:
            return False
        
        # 기존 미리보기 숨김
        self.hide_drop_preview()
        
        # 아이템 수 제한 확인
        if not self.can_add_more_items():
            return False
        
        # 스크롤 영역 내의 상대 좌표로 변환
        scroll_widget_pos = self.scroll_area.mapFrom(self.parent_widget, drop_pos)
        row_pos = self.single_row.mapFrom(self.scroll_area.viewport(), scroll_widget_pos)
        
        # 드롭 인덱스 계산
        target_index = self.single_row.get_drop_index(row_pos.x())
        
        # 미리보기 표시
        self.single_row.show_drop_indicator(target_index)
        self.current_preview_row = self.single_row
        
        # 드래그 중 자동 스크롤 처리
        self._handle_auto_scroll(scroll_widget_pos)
        
        return True
    
    def _handle_auto_scroll(self, pos):
        """드래그 중 자동 스크롤 처리"""
        if not self.scroll_area:
            return
        
        scroll_margin = 50  # 스크롤 트리거 마진
        scroll_step = 10    # 스크롤 스텝
        
        viewport_width = self.scroll_area.viewport().width()
        
        # 왼쪽 끝 근처에서 왼쪽으로 스크롤
        if pos.x() < scroll_margin:
            current_value = self.scroll_area.horizontalScrollBar().value()
            new_value = max(0, current_value - scroll_step)
            self.scroll_area.horizontalScrollBar().setValue(new_value)
        
        # 오른쪽 끝 근처에서 오른쪽으로 스크롤
        elif pos.x() > viewport_width - scroll_margin:
            scrollbar = self.scroll_area.horizontalScrollBar()
            current_value = scrollbar.value()
            max_value = scrollbar.maximum()
            new_value = min(max_value, current_value + scroll_step)
            scrollbar.setValue(new_value)
    
    def hide_drop_preview(self):
        """드롭 미리보기 숨김"""
        if self.current_preview_row:
            self.current_preview_row.hide_drop_indicator()
            self.current_preview_row = None
        
        # 안전장치: 단일 행의 인디케이터 숨김
        if self.single_row:
            self.single_row.hide_drop_indicator()

    def add_item(self, item: ClonedStoryItem, drop_pos=None) -> bool:
        """아이템을 적절한 위치에 추가"""
        # 아이템 수 제한 확인
        if not self.can_add_more_items():
            print(f"Cannot add item: Maximum {self.max_total_items} items allowed")
            return False
        
        # 단일 행이 없으면 생성 (이미 create_scroll_area에서 생성됨)
        if not self.single_row:
            return False
        
        # 드롭 위치 계산
        target_index = 0
        if drop_pos and self.scroll_area:
            scroll_widget_pos = self.scroll_area.mapFrom(self.parent_widget, drop_pos)
            row_pos = self.single_row.mapFrom(self.scroll_area.viewport(), scroll_widget_pos)
            target_index = self.single_row.get_drop_index(row_pos.x())
        
        # 아이템 추가
        if self.single_row.add_item(item, target_index):
            self.hide_placeholder()
            self.hide_drop_preview()  # 미리보기 정리
            self._update_layout()
            print(f"Item added. Total items: {self.get_total_item_count()}/{self.max_total_items}")
            return True
        
        return False
    
    def remove_item(self, item: ClonedStoryItem) -> bool:
        """아이템을 제거"""
        if self.single_row and self.single_row.remove_item(item):
            self._update_layout()
            return True
        
        return False
    
    def reorder_item(self, item: ClonedStoryItem, drop_pos) -> bool:
        """아이템의 순서를 변경"""
        if not self.single_row or item not in self.single_row.items:
            return False
        
        # 미리보기 숨김
        self.hide_drop_preview()
        
        # 기존 위치에서 제거
        old_index = self.single_row.get_item_index(item)
        self.single_row.remove_item(item)
        
        # 새로운 위치 계산
        target_index = 0
        if drop_pos and self.scroll_area:
            scroll_widget_pos = self.scroll_area.mapFrom(self.parent_widget, drop_pos)
            row_pos = self.single_row.mapFrom(self.scroll_area.viewport(), scroll_widget_pos)
            target_index = self.single_row.get_drop_index(row_pos.x())
        
        # 인덱스 조정 (제거로 인한 인덱스 변화 고려)
        if target_index > old_index:
            target_index -= 1
        
        # 새 위치에 추가
        self.single_row.add_item(item, target_index)
        
        self._update_layout()
        return True
    
    def _update_layout(self):
        """레이아웃 상태 업데이트"""
        # 아이템이 없으면 플레이스홀더 표시
        has_items = self.single_row and not self.single_row.is_empty()
        
        if not has_items:
            self.show_placeholder()
        else:
            self.hide_placeholder()
        
        # 레이아웃 업데이트
        self.parent_widget.updateGeometry()
        self.parent_widget.update()
    
    def get_all_items(self) -> List[ClonedStoryItem]:
        """모든 아이템의 리스트 반환 (순서대로)"""
        if self.single_row:
            return self.single_row.items.copy()
        return []