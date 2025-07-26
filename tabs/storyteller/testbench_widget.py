import json, base64
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from ui.theme import DARK_COLORS
from tabs.storyteller.cloned_story_item import ClonedStoryItem
from tabs.storyteller.testbench_layout_manager import TestbenchLayoutManager
from tabs.storyteller.cloned_story_item import ClonedStoryItem

class TestbenchWidget(QFrame):
    item_swap_requested = pyqtSignal(str, str) # source_name, target_name

    def __init__(self, storyteller_tab, config: dict, parent=None):
        super().__init__(parent)
        self.storyteller_tab = storyteller_tab
        self.placeholder_text = config.get('placeholder_text', "Drop items here...")
        self.accept_filter = config.get('accept_filter')
        self.origin_tag = config.get('origin_tag', 'default_bench')
        self.setAcceptDrops(True)

        self.clone_counter = 0  # 복제된 아이템 카운터
        
        self.init_ui()
        
        ui_elements = {'placeholder_label': self.placeholder_label}
        self.layout_manager = TestbenchLayoutManager(self, ui_elements)

    def init_ui(self):
        self.setStyleSheet(f"""
            TestbenchWidget {{ 
                border: 2px dashed {DARK_COLORS['border']}; 
                border-radius: 8px; 
                background-color: {DARK_COLORS['bg_primary']}; 
            }}
        """)
        
        self.placeholder_label = QLabel(self.placeholder_text, self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(f"""
            color: {DARK_COLORS['text_secondary']}; 
            border: none; 
            font-size: 14px; 
            font-style: normal; 
            background-color: transparent;
        """)
        self.placeholder_label.setFixedHeight(160)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입 시 검증"""
        mime_data = event.mimeData()
        if mime_data.hasText():
            try:
                data = json.loads(mime_data.text())
                source_type = data.get("source")
                
                if source_type in ["StoryItemWidget", "ClonedStoryItem"]:
                    # 필터 함수가 있으면, 필터를 통과하는지 확인
                    if self.accept_filter and not self.accept_filter(data):
                        event.ignore()
                        return

                    if source_type == "StoryItemWidget" and not self.layout_manager.can_add_more_items():
                        event.ignore()
                        return
                    
                    event.acceptProposedAction()
                    self.setStyleSheet(f"border: 2px dashed {DARK_COLORS['accent_blue']}; border-radius: 8px; background-color: {DARK_COLORS['bg_secondary']};")
                else:
                    event.ignore()
            except (json.JSONDecodeError, KeyError):
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """드래그 이동 시 미리보기 표시"""
        try:
            mime_data = event.mimeData()
            data = json.loads(mime_data.text())
            source_type = data.get("source")
            
            if source_type in ["StoryItemWidget", "ClonedStoryItem"]:
                drop_pos = event.position().toPoint()
                
                # 미리보기 표시 (새로운 single-row 시스템에서)
                success = self.layout_manager.show_drop_preview(drop_pos)
                if success:
                    event.acceptProposedAction()
                else:
                    event.ignore()
            else:
                event.ignore()
        except Exception as e:
            print(f"Drag move error: {e}")
            event.ignore()

    def dragLeaveEvent(self, event):
        """드래그 이탈 시 원래 스타일 복원 및 미리보기 숨김"""
        self.layout_manager.hide_drop_preview()
        self.setStyleSheet(f"""
            TestbenchWidget {{ 
                border: 2px dashed {DARK_COLORS['border']}; 
                border-radius: 8px; 
                background-color: {DARK_COLORS['bg_primary']}; 
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        """드롭 이벤트 처리"""
        try:
            mime_data = event.mimeData()
            data = json.loads(mime_data.text())
            source_type = data.get("source")

            print(f"Drop event: {source_type}")

            if source_type == "StoryItemWidget":
                self._handle_story_item_drop(data, event)
            elif source_type == "ClonedStoryItem":
                self._handle_cloned_item_drop(data, event)
            else:
                print(f"Unknown source type: {source_type}")
            
        except Exception as e:
            print(f"Drop event error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 미리보기 정리 및 드래그 스타일 해제
            self.layout_manager.hide_drop_preview()
            self.dragLeaveEvent(None)

    def _handle_story_item_drop(self, data, event):
        """원본 StoryItemWidget 드롭 처리"""
        group_path = data.get("group_path")
        variable_name = data.get("variable_name")
        
        print(f"Creating clone for: {variable_name} from {group_path}")
        
        # 아이템 수 제한 확인
        if not self.layout_manager.can_add_more_items():
            print(f"Cannot add item: Maximum {self.layout_manager.max_total_items} items allowed")
            return
        
        # 원본 위젯 찾기
        original_widget = self.storyteller_tab.find_item_widget(group_path, variable_name)
        if not original_widget:
            print(f"Original widget not found: {group_path}/{variable_name}")
            return
        
        # 복제본 생성
        try:
            cloned_widget = ClonedStoryItem(original_widget, origin_tag=self.origin_tag, parent_bench=self, parent=self)
            cloned_widget.remove_requested.connect(self._on_remove_clone_requested)
            cloned_widget.swap_requested.connect(self._on_item_swap_requested)
            
            self.clone_counter += 1
            print(f"Created clone #{self.clone_counter}: {cloned_widget.instance_id}")
            
            # 레이아웃 매니저를 통해 추가
            drop_pos = event.position().toPoint()
            success = self.layout_manager.add_item(cloned_widget, drop_pos)
            
            if success:
                print(f"Clone inserted successfully")
            else:
                print(f"Failed to insert clone - limit reached")
                cloned_widget.deleteLater()
            
        except Exception as e:
            print(f"Error creating clone: {e}")
            import traceback
            traceback.print_exc()

    def _handle_cloned_item_drop(self, data, event):
        """복제된 아이템의 재정렬 처리"""
        instance_id = data.get("instance_id")
        dragged_widget = self._find_clone_by_id(instance_id)
        
        if not dragged_widget:
            print(f"Cloned widget not found: {instance_id}")
            return
        
        # 레이아웃 매니저를 통해 재정렬 (single-row 시스템에서)
        drop_pos = event.position().toPoint()
        success = self.layout_manager.reorder_item(dragged_widget, drop_pos)
        
        if success:
            print(f"Widget reordered successfully")
        else:
            print(f"Failed to reorder widget")

    def _on_remove_clone_requested(self, clone_widget):
        """복제된 아이템의 제거 요청 처리"""
        print(f"Removing clone: {clone_widget.instance_id}")
        
        try:
            # 레이아웃 매니저를 통해 제거
            success = self.layout_manager.remove_item(clone_widget)
            
            if success:
                # 위젯 삭제
                clone_widget.deleteLater()
                print(f"Clone removed successfully")
            else:
                print(f"Failed to remove clone from layout")
                
        except Exception as e:
            print(f"Error removing clone: {e}")
            import traceback
            traceback.print_exc()

    def _find_clone_by_id(self, instance_id):
        """instance_id로 복제본 위젯 찾기"""
        all_items = self.layout_manager.get_all_items()
        for item in all_items:
            if hasattr(item, 'instance_id') and item.instance_id == instance_id:
                return item
        return None

    def get_status_info(self) -> str:
        """현재 상태 정보 반환 (상태바 표시용)"""
        current_count = self.layout_manager.get_total_item_count()
        max_count = self.layout_manager.max_total_items
        return f"Testbench: {current_count}/{max_count} items"

    def get_all_cloned_items(self):
        """모든 복제된 아이템 반환 (외부 접근용)"""
        return self.layout_manager.get_all_items()

    def get_prompts_for_item(self, item: ClonedStoryItem) -> str | str:
        """특정 ClonedStoryItem의 positive, negative 프롬프트를 반환합니다."""
        if hasattr(item, 'data') and isinstance(item.data, dict):
            description = item.data.get("description", {})
            positive = description.get("positive_prompt", "").strip()
            negative = description.get("negative_prompt", "").strip()
            return positive, negative
        return "", ""

    def is_full(self) -> bool:
        """Testbench가 가득 찬 상태인지 확인"""
        return not self.layout_manager.can_add_more_items()
    
    def get_all_prompts(self) -> str| str:
        """Testbench 내 모든 ClonedStoryItem의 프롬프트를 조합하여 반환합니다."""
        all_positive = []
        all_negative = []
        
        items = self.layout_manager.get_all_items()
        for item in items:
            if hasattr(item, 'data') and isinstance(item.data, dict):
                description = item.data.get("description", {})
                
                positive = description.get("positive_prompt", "").strip()
                if positive:
                    all_positive.append(positive)
                
                negative = description.get("negative_prompt", "").strip()
                if negative:
                    all_negative.append(negative)
                    
        return ", ".join(all_positive), ", ".join(all_negative)
    
    def clear_items(self):
        """Testbench의 모든 아이템을 제거합니다."""
        all_items = self.layout_manager.get_all_items()
        for item in all_items:
            if self.layout_manager.remove_item(item):
                item.deleteLater()
        self.layout_manager._update_layout()

    def get_items_data(self) -> list[dict]:
        """Testbench의 모든 아이템 데이터를 리스트로 반환합니다."""
        items_data = []
        all_items = self.layout_manager.get_all_items()
        for item in all_items:
            if hasattr(item, 'get_data'):
                items_data.append(item.get_data())
        return items_data

    def add_item_from_data(self, item_data: dict):
        """딕셔너리 데이터로부터 ClonedStoryItem을 생성하여 추가합니다."""
        try:
            full_data = item_data.get("full_data", {})
            variable_name = item_data.get("variable_name")
            origin_tag = item_data.get("origin_tag")
            
            # 원본 StoryItemWidget을 임시로 생성하여 ClonedStoryItem에 전달
            from tabs.storyteller.story_item_widget import StoryItemWidget
            temp_original = StoryItemWidget(group_path="", variable_name=variable_name)
            temp_original.data = full_data
            
            thumbnail_b64 = full_data.get("thumbnail_base64")
            if thumbnail_b64:
                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(thumbnail_b64), "PNG")
                temp_original.thumbnail_label.setPixmap(pixmap)
            
            cloned_widget = ClonedStoryItem(temp_original, origin_tag=origin_tag, parent_bench=self, parent=self)
            cloned_widget.remove_requested.connect(self._on_remove_clone_requested)
            cloned_widget.swap_requested.connect(self._on_item_swap_requested) # 누락된 시그널 연결 추가

            self.layout_manager.add_item(cloned_widget)
        except Exception as e:
            print(f"Error adding item from data: {e}")

    def clear_items(self):
        """Testbench의 모든 아이템을 제거합니다."""
        all_items = self.layout_manager.get_all_items()
        for item in all_items:
            if self.layout_manager.remove_item(item):
                item.deleteLater()
        self.layout_manager._update_layout()

    def load_from_data(self, items_data: list):
        """딕셔너리 리스트로 Testbench의 상태를 완전히 복원합니다."""
        self.clear_items()
        for item_data in items_data:
            self.add_item_from_data(item_data)

    def _on_item_swap_requested(self, source_item: ClonedStoryItem, target_variable_name: str):
        """자식 위젯의 교체 요청을 받아 자신의 시그널을 발생시킵니다."""
        print(f"Testbench: Swap requested from '{source_item.variable_name}' to '{target_variable_name}'")
        self.item_swap_requested.emit(source_item.variable_name, target_variable_name)

    def get_other_items(self, item_to_exclude: ClonedStoryItem) -> list[ClonedStoryItem]:
        """주어진 아이템을 제외한 모든 아이템의 리스트를 반환합니다."""
        all_items = self.layout_manager.get_all_items()
        return [item for item in all_items if item is not item_to_exclude]