from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

from ui.theme import DARK_STYLES, DARK_COLORS
from tabs.storyteller.testbench_widget import TestbenchWidget
from tabs.storyteller.adventure_cell import CellManager

class AdventureTab(QWidget):
    """
    Adventure 모드의 UI와 로직을 담당하는 클래스.
    """
    def __init__(self, app_context, storyteller_tab, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.storyteller_tab = storyteller_tab
        self.character_testbench = None
        
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 좌측 패널 (컨트롤 + 캐릭터 Testbench + 향후 Cell 영역)
        main_panel = self._create_main_panel()

        main_layout.addWidget(main_panel)


    def _create_main_panel(self) -> QWidget:
        """컨트롤, Testbench, Cell 영역을 담을 메인 패널을 생성합니다."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        # 1. 상단 컨트롤 프레임
        control_frame = self._create_control_frame()
        layout.addWidget(control_frame)
        
        # 2. 캐릭터 전용 Testbench
        character_bench_config = {
            'placeholder_text': "[Characters Bench] Drag & Drop 'Character' items to here…",
            'origin_tag': 'adventure_character_bench'
        }
        self.character_testbench = TestbenchWidget(
            storyteller_tab=self.storyteller_tab,
            config=character_bench_config,
            parent=panel  # 명시적으로 부모 설정
        )
        self.character_testbench.setMaximumHeight(180)
        layout.addWidget(self.character_testbench)
        
        # 3. Cell 기반 UI를 관리할 CellManager
        self.cell_manager = CellManager(self.app_context, self.storyteller_tab, parent=panel)
        layout.addWidget(self.cell_manager, 1)
        
        return panel  # ✅ 반환값 추가

    def _create_control_frame(self) -> QFrame:
        """상단 컨트롤 버튼들을 담는 프레임을 생성합니다."""
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setStyleSheet(DARK_STYLES['compact_card'])

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 0, 8, 0)
        
        run_button = QPushButton("▶ RUN")
        run_button.setStyleSheet(DARK_STYLES['primary_button'])
        
        save_scenario_button = QPushButton("Save to scenario")
        save_scenario_button.setStyleSheet(DARK_STYLES['secondary_button'])
        
        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet(DARK_STYLES['secondary_button'])
        
        layout.addWidget(run_button)
        layout.addWidget(save_scenario_button)
        layout.addStretch(1)
        layout.addWidget(clear_button)

        return frame