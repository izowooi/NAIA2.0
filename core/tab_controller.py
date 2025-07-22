import os
import glob
import importlib.util
import traceback
from pathlib import Path
from typing import Type, List, Dict, Optional

from PyQt6.QtWidgets import QTabWidget, QWidget, QPushButton, QTabBar
from PyQt6.QtCore import pyqtSignal

from interfaces.base_tab_module import BaseTabModule
from core.context import AppContext
from ui.theme import DARK_STYLES

class TabController(QWidget):
    """
    RightView의 탭들을 동적으로 로드, 생성 및 관리하는 컨트롤러.
    MiddleSectionController와 유사한 패턴으로 작동합니다.
    """
    
    # 탭 추가/제거 시 다른 컴포넌트에 알리기 위한 시그널
    tab_added = pyqtSignal(str, object)  # tab_id, instance
    tab_removed = pyqtSignal(str) # tab_id

    def __init__(self, tabs_dir: str, app_context: AppContext, tab_widget: QTabWidget, parent: QWidget = None):
        super().__init__(parent)
        self.tabs_dir = tabs_dir
        self.app_context = app_context
        self.tab_widget = tab_widget  # UI 제어를 위해 RightView의 QTabWidget을 직접 참조

        self.module_classes: List[Type[BaseTabModule]] = []
        self.module_instances: Dict[str, BaseTabModule] = {}
        self.tab_index_map: Dict[str, int] = {}  # tab_id -> index 매핑
        
        if not os.path.exists(tabs_dir):
            os.makedirs(tabs_dir)
            print(f"📁 탭 모듈 디렉토리 생성: {tabs_dir}")

    def initialize_tabs(self):
        """모든 탭 모듈을 로드하고 UI를 구성하는 메인 메서드"""
        self._load_tab_modules()
        
        # 모듈들을 order 순서대로 정렬
        sorted_classes = sorted(self.module_classes, key=lambda c: c().get_tab_order())

        for cls in sorted_classes:
            try:
                # 1. 모듈 인스턴스 생성
                temp_instance = cls()
                if temp_instance.get_tab_type() != 'core':
                    print(f"  -> 동적 탭 '{temp_instance.get_tab_title()}'은 시작 시 로드하지 않습니다.")
                    continue
                instance = cls()
                tab_id = instance.tab_id

                # 2. 컨텍스트 주입
                instance.initialize_with_context(self.app_context)
                
                # 3. UI 위젯 생성
                widget = instance.create_widget(parent=self.tab_widget)
                
                # 4. 탭 위젯에 추가
                tab_index = self.tab_widget.addTab(widget, instance.get_tab_title())

                # 5. 인스턴스 및 정보 저장
                self.module_instances[tab_id] = instance
                self.tab_index_map[tab_id] = tab_index
                
                # 6. 닫기 가능한 탭에 닫기 버튼 추가
                if instance.can_close_tab():
                    self._add_close_button_to_tab(tab_index, tab_id)
                
                # 7. 초기화 완료 후 on_initialize 호출
                instance.on_initialize()
                
                self.tab_added.emit(tab_id, instance)
                print(f"✅ 탭 '{instance.get_tab_title()}' UI 생성 및 초기화 완료.")

            except Exception as e:
                print(f"❌ 탭 '{cls.__name__}' 생성 중 오류 발생: {e}")
                traceback.print_exc()

    def _load_tab_modules(self):
        """'tabs/' 디렉토리에서 *.py 파일들을 찾아 클래스를 로드합니다."""
        print(f"🔍 탭 모듈 로드 시작: {self.tabs_dir}")
        pattern = os.path.join(self.tabs_dir, "*.py")
        module_files = glob.glob(pattern)

        for path in module_files:
            name = Path(path).stem
            try:
                spec = importlib.util.spec_from_file_location(name, path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if isinstance(obj, type) and issubclass(obj, BaseTabModule) and obj is not BaseTabModule:
                            self.module_classes.append(obj)
                            print(f"  -> 탭 모듈 클래스 발견: {obj.__name__}")
            except Exception as e:
                print(f"❌ 탭 모듈 로드 실패 ({name}): {e}")
                traceback.print_exc()

    def _add_close_button_to_tab(self, tab_index: int, tab_id: str):
        """특정 탭에 닫기 버튼을 추가합니다."""
        close_button = QPushButton("✕")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 9px;
                font-family: Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                color: #B0B0B0;
                padding: 0px 4px;
            }
            QPushButton:hover {
                background-color: #F44336;
                color: white;
            }
        """)
        close_button.setFixedSize(18, 18)
        close_button.setToolTip("탭 닫기")
        close_button.clicked.connect(lambda: self.close_tab(tab_id))
        
        self.tab_widget.tabBar().setTabButton(tab_index, QTabBar.ButtonPosition.RightSide, close_button)

    def close_tab(self, tab_id: str):
        """탭 ID를 기반으로 탭을 닫습니다."""
        if tab_id not in self.module_instances:
            return
        
        instance = self.module_instances[tab_id]
        if not instance.on_tab_closing(): # 닫기 전 확인
            return
            
        # 탭 위젯에서 해당 위젯 찾아서 닫기
        tab_index = self.tab_index_map[tab_id]
        widget = self.tab_widget.widget(tab_index)
        self.tab_widget.removeTab(tab_index)
        
        # 정리 작업
        instance.cleanup()
        widget.deleteLater()
        
        # 매핑 정보 제거
        del self.module_instances[tab_id]
        del self.tab_index_map[tab_id]
        
        # 인덱스 매핑 재조정
        self._rebuild_index_mapping()
        
        self.tab_removed.emit(tab_id)
        print(f"✅ 탭 '{instance.get_tab_title()}' 제거 완료.")

    def _rebuild_index_mapping(self):
        """탭 인덱스 매핑을 재구축합니다."""
        self.tab_index_map.clear()
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            for tab_id, instance in self.module_instances.items():
                if hasattr(instance, 'widget') and instance.widget == widget:
                    self.tab_index_map[tab_id] = i
                    break

    def get_tab_instance(self, tab_id: str) -> Optional[BaseTabModule]:
        """탭 ID로 탭 인스턴스를 반환합니다."""
        return self.module_instances.get(tab_id)
    
    def add_tab_by_name(self, module_class_name: str, **kwargs):
        """
        클래스 이름을 기반으로 탭을 동적으로 추가하고 활성화합니다.
        이미 탭이 열려있으면 해당 탭으로 전환합니다.
        """
        # 1. 이미 해당 모듈의 인스턴스가 있는지 확인
        for instance in self.module_instances.values():
            if instance.__class__.__name__ == module_class_name:
                print(f"✅ 이미 열려있는 탭 '{instance.get_tab_title()}'으로 전환합니다.")
                self.switch_to_tab(instance.tab_id)
                return

        # 2. 로드된 클래스 목록에서 해당 클래스 찾기
        TargetModuleClass = next((cls for cls in self.module_classes if cls.__name__ == module_class_name), None)

        if not TargetModuleClass:
            print(f"❌ '{module_class_name}'에 해당하는 탭 모듈 클래스를 찾을 수 없습니다.")
            return

        # 3. 새 탭 추가 (기존 add_tab_from_class 로직 재사용)
        try:
            instance = TargetModuleClass()
            instance.initialize_with_context(self.app_context)
            
            # 동적 데이터가 필요한 경우 setup 메서드 호출
            if hasattr(instance, 'setup'):
                instance.setup(**kwargs)

            widget = instance.create_widget(self.tab_widget)
            tab_index = self.tab_widget.addTab(widget, instance.get_tab_title())

            self.module_instances[instance.tab_id] = instance
            self.tab_index_map[instance.tab_id] = tab_index
            
            if instance.can_close_tab():
                self._add_close_button_to_tab(tab_index, instance.tab_id)
            
            instance.on_initialize()
            self.tab_widget.setCurrentIndex(tab_index) # 새로 추가된 탭으로 즉시 전환
            self.tab_added.emit(instance.tab_id, instance)
            print(f"✅ 동적 탭 '{instance.get_tab_title()}' 추가 완료.")

        except Exception as e:
            print(f"❌ 동적 탭 '{module_class_name}' 생성 중 오류: {e}")
            traceback.print_exc()

    def switch_to_tab(self, tab_id: str):
        """탭 ID를 기반으로 해당 탭으로 전환합니다."""
        if tab_id in self.tab_index_map:
            self.tab_widget.setCurrentIndex(self.tab_index_map[tab_id])