import json
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ui.theme import DARK_COLORS
from tabs.storyteller.cloned_story_item import ClonedStoryItem
from tabs.storyteller.testbench_layout_manager import TestbenchLayoutManager

class TestbenchWidget(QFrame):
    def __init__(self, storyteller_tab, parent=None):
        super().__init__(parent)
        self.storyteller_tab = storyteller_tab
        self.setAcceptDrops(True)
        
        # 디버깅을 위한 카운터
        self.clone_counter = 0
        
        # 새로운 single-row 레이아웃 매니저 사용
        self.layout_manager = TestbenchLayoutManager(self)
        
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            TestbenchWidget {{ 
                border: 2px dashed {DARK_COLORS['border']}; 
                border-radius: 8px; 
                background-color: {DARK_COLORS['bg_primary']}; 
            }}
        """)
        
        # 레이아웃 매니저가 이미 초기화되었으므로 추가 설정 불필요

    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입 시 검증"""
        mime_data = event.mimeData()
        if mime_data.hasText():
            try:
                data = json.loads(mime_data.text())
                source_type = data.get("source")
                
                if source_type in ["StoryItemWidget", "ClonedStoryItem"]:
                    # 아이템 수 제한 확인 (새 아이템 추가인 경우)
                    if source_type == "StoryItemWidget" and not self.layout_manager.can_add_more_items():
                        event.ignore()
                        return
                    
                    event.acceptProposedAction()
                    # 드래그 중 시각적 피드백
                    self.setStyleSheet(f"""
                        TestbenchWidget {{ 
                            border: 2px dashed {DARK_COLORS['accent_blue']}; 
                            border-radius: 8px; 
                            background-color: {DARK_COLORS['bg_secondary']}; 
                        }}
                    """)
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
            cloned_widget = ClonedStoryItem(original_widget, parent=self)
            
            # 제거 시그널 연결
            cloned_widget.remove_requested.connect(self._on_remove_clone_requested)
            
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

    def is_full(self) -> bool:
        """Testbench가 가득 찬 상태인지 확인"""
        return not self.layout_manager.can_add_more_items()