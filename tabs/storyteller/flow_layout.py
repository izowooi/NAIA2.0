# tabs/storyteller/flow_layout.py

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy, QSpacerItem, QLayoutItem, QWidget, QWidgetItem

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=10, h_spacing=12, v_spacing=12):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.item_list: list[QLayoutItem] = []
        
        # 기본 간격 설정
        self.setSpacing(12)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self.item_list.append(item)
        self.invalidate()

    def insertWidget(self, index: int, widget: QWidget):
        """위젯을 특정 인덱스에 안전하게 삽입"""
        if widget is None:
            print("Warning: Trying to insert None widget")
            return
        
        print(f"FlowLayout: Inserting widget {widget} at index {index}")
        
        # 인덱스 범위 검증
        index = max(0, min(index, len(self.item_list)))
        
        # 위젯의 부모를 먼저 설정
        parent_widget = self.parentWidget()
        if parent_widget:
            widget.setParent(parent_widget)
            print(f"Set widget parent to: {parent_widget}")
        
        # 위젯을 보이게 설정
        widget.show()
        widget.setVisible(True)
        
        # QWidget을 QLayoutItem으로 래핑
        item = QWidgetItem(widget)
        self.item_list.insert(index, item)
        
        print(f"FlowLayout: Item list now has {len(self.item_list)} items")
        
        # 강제 레이아웃 업데이트
        self.invalidate()
        self.activate()
        
        # 즉시 지오메트리 설정
        if parent_widget:
            self.setGeometry(parent_widget.rect())
        
        print(f"Widget geometry after insert: {widget.geometry()}")
        print(f"Widget visible after insert: {widget.isVisible()}")

    def removeWidget(self, widget: QWidget):
        """위젯을 안전하게 제거"""
        if widget is None:
            return
        
        for i, item in enumerate(self.item_list):
            if item.widget() is widget:
                removed_item = self.takeAt(i)
                if removed_item:
                    # 위젯을 레이아웃에서 완전히 분리
                    removed_widget = removed_item.widget()
                    if removed_widget:
                        removed_widget.setParent(None)
                break
        
        self.invalidate()
        self.activate()  # 즉시 레이아웃 업데이트

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            item = self.item_list.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            if item and item.widget():  # None 체크 추가
                size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        # 컨테이너 여백 추가 (TestbenchWidget의 border와 padding 고려)
        margin_left = 10
        margin_top = 10
        margin_right = 10
        margin_bottom = 10
        
        # 실제 사용 가능한 영역 계산
        available_rect = QRect(
            rect.x() + margin_left,
            rect.y() + margin_top,
            rect.width() - margin_left - margin_right,
            rect.height() - margin_top - margin_bottom
        )
        
        x = available_rect.x()
        y = available_rect.y()
        line_height = 0
        
        # 아이템 간 간격 설정 (기본값보다 크게)
        space_x = max(12, self.spacing() if self.h_spacing == -1 else self.h_spacing)
        space_y = max(12, self.spacing() if self.v_spacing == -1 else self.v_spacing)

        print(f"FlowLayout: Available area: {available_rect}, spacing: {space_x}x{space_y}")

        for i, item in enumerate(self.item_list):
            if not item or not item.widget():
                continue
                
            item_size = item.sizeHint()
            item_width = item_size.width()
            item_height = item_size.height()
            
            # 다음 아이템의 x 위치 계산
            next_x = x + item_width
            if i > 0:  # 첫 번째 아이템이 아니면 간격 추가
                next_x += space_x

            # 줄바꿈 검사: 오른쪽 경계를 넘어가면 다음 줄로
            if next_x > available_rect.right() and line_height > 0:
                x = available_rect.x()  # 왼쪽 여백으로 돌아감
                y = y + line_height + space_y
                line_height = 0

            if not test_only:
                # 위젯의 실제 위치 설정
                widget_rect = QRect(x, y, item_width, item_height)
                item.setGeometry(widget_rect)
                
                # 디버깅 정보
                widget = item.widget()
                if widget and hasattr(widget, 'instance_id'):
                    print(f"Layout: Widget {widget.instance_id[:8]} positioned at ({x}, {y}) size: {item_width}x{item_height}")
            
            # 다음 위치 계산
            x += item_width + space_x
            line_height = max(line_height, item_height)
        
        return y + line_height - rect.y() + margin_top + margin_bottom