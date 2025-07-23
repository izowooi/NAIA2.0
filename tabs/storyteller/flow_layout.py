# tabs/storyteller/flow_layout.py

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy, QSpacerItem

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, h_spacing=-1, v_spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
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
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        space_x = self.spacing() if self.h_spacing == -1 else self.h_spacing
        space_y = self.spacing() if self.v_spacing == -1 else self.v_spacing

        for item in self.item_list:
            # ▼▼▼▼▼ [수정] x 좌표 계산 로직 수정 ▼▼▼▼▼
            # 현재 아이템의 너비
            item_width = item.sizeHint().width()

            # 다음 아이템이 들어갈 x 좌표 계산
            # 현재 줄의 맨 처음이 아니면(x != rect.x()) 간격을 추가
            next_x = x + item_width
            if x != rect.x():
                next_x += space_x

            # 다음 아이템이 경계를 벗어나면 줄바꿈
            if next_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            # 다음 아이템을 위해 x 좌표 업데이트
            x += item_width + space_x
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y()