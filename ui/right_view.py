from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QPushButton, QTabBar,
    QMenu, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction
import os
import pandas as pd

from ui.theme import DARK_STYLES, DARK_COLORS
from ui.detached_window import DetachedWindow
from core.tab_controller import TabController

class EnhancedTabWidget(QTabWidget):
    """우클릭 컨텍스트 메뉴가 있는 향상된 탭 위젯"""
    tab_detach_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.non_detachable_tabs = set()

    def set_tab_detachable(self, tab_index: int, detachable: bool):
        if detachable:
            self.non_detachable_tabs.discard(tab_index)
        else:
            self.non_detachable_tabs.add(tab_index)

    def show_context_menu(self, position: QPoint):
        tab_index = self.tabBar().tabAt(position)
        if tab_index == -1 or tab_index in self.non_detachable_tabs:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DARK_COLORS['bg_tertiary']};
                color: {DARK_COLORS['text_primary']};
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 4px; padding: 5px;
            }}
            QMenu::item {{ padding: 8px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {DARK_COLORS['accent_blue']}; }}
        """)
        
        detach_action = QAction("🔗 외부 창에서 열기", self)
        detach_action.triggered.connect(lambda: self.tab_detach_requested.emit(tab_index))
        menu.addAction(detach_action)
        
        global_pos = self.tabBar().mapToGlobal(position)
        menu.exec(global_pos)

class RightView(QWidget):
    """
    오른쪽 패널의 탭 컨테이너 클래스.
    TabController를 통해 모든 탭을 동적으로 관리합니다.
    """
    # Main window로 전달될 시그널들
    instant_generation_requested = pyqtSignal(dict)
    load_prompt_to_main_ui = pyqtSignal(str)
    generate_with_image_requested = pyqtSignal(dict)

    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        
        # 분리된 창 추적용
        self.detached_windows = {}
        self.detached_widgets = {}
        
        self.init_ui()
        
        # ✅ TabController를 통해 모든 탭을 동적으로 설정
        self.tab_controller = TabController(
            tabs_dir='tabs',  # 탭 모듈이 위치한 디렉토리
            app_context=self.app_context,
            tab_widget=self.tab_widget,
            parent=self
        )
        self.tab_controller.initialize_tabs()
        
        # ✅ ImageViewerModule 인스턴스를 컨트롤러로부터 가져와 시그널 연결
        image_viewer_module = self.tab_controller.get_tab_instance('ImageViewerModule')
        if image_viewer_module:
            # ImageViewerModule의 시그널을 RightView의 시그널에 다시 연결
            if hasattr(image_viewer_module, 'instant_generation_requested'):
                image_viewer_module.instant_generation_requested.connect(self.instant_generation_requested)
            if hasattr(image_viewer_module, 'load_prompt_to_main_ui'):
                image_viewer_module.load_prompt_to_main_ui.connect(self.load_prompt_to_main_ui)
        else:
            print("⚠️ ImageViewerModule 인스턴스를 찾을 수 없어 시그널 연결에 실패했습니다.")

        # Browser Tab
        browser_module = self.tab_controller.get_tab_instance('BrowserTabModule')
        if browser_module:
            if hasattr(browser_module, 'instant_generation_requested'):
                browser_module.instant_generation_requested.connect(self.instant_generation_requested)
                print("✅ BrowserTabModule의 instant_generation_requested 시그널이 연결되었습니다.")
            if hasattr(browser_module, 'generate_with_image_requested'):
                browser_module.generate_with_image_requested.connect(self.generate_with_image_requested)
        else:
            print("⚠️ BrowserTabModule 인스턴스를 찾을 수 없어 시그널 연결에 실패했습니다.")


    def init_ui(self):
        """기본 UI 구조 초기화"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        self.tab_widget = EnhancedTabWidget()
        self.tab_widget.setStyleSheet(DARK_STYLES['dark_tabs'])
        self.tab_widget.tab_detach_requested.connect(self.detach_tab)
        
        main_layout.addWidget(self.tab_widget)

    def detach_tab(self, tab_index: int):
        """탭을 외부 창으로 분리"""
        if tab_index in self.detached_windows:
            self.detached_windows[tab_index].raise_()
            self.detached_windows[tab_index].activateWindow()
            return
            
        widget = self.tab_widget.widget(tab_index)
        tab_title = self.tab_widget.tabText(tab_index)
        
        if not widget: return
            
        try:
            placeholder = self.create_placeholder_widget(tab_title)
            self.tab_widget.removeTab(tab_index)
            self.tab_widget.insertTab(tab_index, placeholder, f"🔗 {tab_title}")
            
            self.detached_widgets[tab_index] = (widget, tab_title)
            
            detached_window = DetachedWindow(widget, tab_title, tab_index, parent_container=self)
            detached_window.window_closed.connect(self.reattach_tab)
            
            self.detached_windows[tab_index] = detached_window
            detached_window.show()
            
        except Exception as e:
            print(f"❌ 탭 '{tab_title}' 분리 실패: {e}")
            import traceback
            traceback.print_exc()

    def reattach_tab(self, tab_index: int, widget: QWidget):
        """외부 창에서 탭으로 복귀"""
        if tab_index not in self.detached_widgets: return
            
        original_widget, original_title = self.detached_widgets[tab_index]
        
        try:
            placeholder = self.tab_widget.widget(tab_index)
            self.tab_widget.removeTab(tab_index)
            if placeholder: placeholder.deleteLater()
                
            widget.setParent(self)
            self.tab_widget.insertTab(tab_index, widget, original_title)
            self.tab_widget.setCurrentIndex(tab_index)
            
            del self.detached_widgets[tab_index]
            if tab_index in self.detached_windows: del self.detached_windows[tab_index]
                
        except Exception as e:
            print(f"❌ 탭 '{original_title}' 복귀 실패: {e}")
            import traceback
            traceback.print_exc()

    def create_placeholder_widget(self, tab_title: str) -> QWidget:
        """분리된 탭 자리에 표시할 플레이스홀더 위젯 생성"""
        placeholder = QFrame()
        placeholder.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: 2px dashed {DARK_COLORS['border_light']};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        icon_label = QLabel("🔗")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 48px; color: {DARK_COLORS['text_secondary']};")
        
        message_label = QLabel(f"'{tab_title}'이(가)\n외부 창에서 열려있습니다")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(f"font-size: 16px; color: {DARK_COLORS['text_secondary']};")
        
        return_button = QPushButton("창 닫고 여기로 복귀")
        return_button.setStyleSheet(DARK_STYLES['secondary_button'])
        return_button.clicked.connect(lambda: self.force_reattach_tab(tab_title))
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        layout.addWidget(return_button)
        layout.addStretch()
        
        return placeholder

    def force_reattach_tab(self, tab_title: str):
        """플레이스홀더 버튼을 통해 강제로 탭 복귀"""
        for tab_index, window in self.detached_windows.items():
            if window.tab_title == tab_title:
                window.close()
                break

    def close_all_detached_windows(self):
        """앱 종료 시 모든 분리된 창을 닫습니다."""
        for window in list(self.detached_windows.values()):
            window.close()
        self.detached_windows.clear()

    # === ImageWindow 관련 메서드들 (컨트롤러를 통해 인스턴스에 접근) ===
    def _get_image_viewer_instance(self):
        """컨트롤러에서 ImageViewerModule 인스턴스를 가져옵니다."""
        if hasattr(self, 'tab_controller'):
            return self.tab_controller.get_tab_instance('ImageViewerModule')
        return None

    def update_image(self, image):
        """이미지 업데이트"""
        instance = self._get_image_viewer_instance()
        if instance and hasattr(instance, 'image_window_widget'):
            instance.image_window_widget.update_image(image)

    def update_info(self, text: str):
        """정보 업데이트"""
        instance = self._get_image_viewer_instance()
        if instance and hasattr(instance, 'image_window_widget'):
            instance.image_window_widget.update_info(text)

    def add_to_history(self, image, raw_bytes: bytes, info: str, source_row: pd.Series):
        """히스토리 추가"""
        instance = self._get_image_viewer_instance()
        if instance and hasattr(instance, 'image_window_widget'):
            instance.image_window_widget.add_to_history(image, raw_bytes, info, source_row)
            
    # # === 동적 탭 생성을 위한 메서드들 ===
    # def add_api_management_tab(self):
    #     """API 관리 탭 추가 (TabController를 통해)"""
    #     if self.tab_controller:
    #         self.tab_controller.add_tab_by_name('APIManagementTabModule')

    # def add_depth_search_tab(self, search_results, main_window):
    #     """심층 검색 탭 추가 (TabController를 통해)"""
    #     if self.tab_controller:
    #         self.tab_controller.add_tab_by_name(
    #             'DepthSearchTabModule',
    #             search_results=search_results,
    #             main_window=main_window
    #         )