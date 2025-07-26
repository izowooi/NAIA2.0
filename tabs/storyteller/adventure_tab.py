from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel, QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer

from ui.theme import DARK_STYLES, DARK_COLORS
from tabs.storyteller.testbench_widget import TestbenchWidget
from tabs.storyteller.adventure_cell import CellManager
from tabs.storyteller.cloned_story_item import ClonedStoryItem
from typing import Optional
import json
from pathlib import Path

class AdventureTab(QWidget):
    """
    Adventure 모드의 UI와 로직을 담당하는 클래스.
    """
    def __init__(self, app_context, storyteller_tab, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.storyteller_tab = storyteller_tab
        self.character_testbench = None
        self.cell_manager = None
        self.run_button = None
        
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
        self.character_testbench.item_swap_requested.connect(self._on_character_swap_requested)
        self.character_testbench.setMaximumHeight(180)
        layout.addWidget(self.character_testbench)
        
        # 3. Cell 기반 UI를 관리할 CellManager
        self.cell_manager = CellManager(self.app_context, self.storyteller_tab, parent=panel)
        self.cell_manager.scenario_run_started.connect(self._update_run_button_to_stop)
        self.cell_manager.scenario_run_finished.connect(self._update_run_button_to_run)
        layout.addWidget(self.cell_manager, 1)
        
        return panel  # ✅ 반환값 추가

    def _create_control_frame(self) -> QFrame:
        """상단 컨트롤 버튼들을 담는 프레임을 생성합니다."""
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setStyleSheet(DARK_STYLES['compact_card'])

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 0, 8, 0)
        
        self.run_button = QPushButton("▶ RUN")
        self.run_button.setStyleSheet(DARK_STYLES['primary_button'])
        self.run_button.clicked.connect(self._on_run_stop_button_clicked)
        
        save_scenario_button = QPushButton("💾 Save to scenario")
        save_scenario_button.setStyleSheet(DARK_STYLES['secondary_button'])
        save_scenario_button.clicked.connect(self._on_save_scenario) # 시그널 연결

        load_scenario_button = QPushButton("📂 Load scenario")
        load_scenario_button.setStyleSheet(DARK_STYLES['secondary_button'])
        load_scenario_button.clicked.connect(self._on_load_scenario) # 시그널 연결

        save_all_images_button = QPushButton("🖼️ Save All Images")
        save_all_images_button.setStyleSheet(DARK_STYLES['secondary_button'])
        save_all_images_button.clicked.connect(self._on_save_all_images)

        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet(DARK_STYLES['secondary_button'])
        clear_button.clicked.connect(self._on_clear_all) # 시그널 연결

        immersive_checkbox = QCheckBox("Immersive mode")
        immersive_checkbox.setStyleSheet(DARK_STYLES['dark_checkbox'])
        immersive_checkbox.toggled.connect(self._on_immersive_mode_toggled)
        
        layout.addWidget(self.run_button)
        layout.addWidget(save_scenario_button)
        layout.addWidget(load_scenario_button)
        layout.addWidget(save_all_images_button)
        layout.addStretch(1)
        #layout.addWidget(immersive_checkbox)
        layout.addWidget(clear_button)

        return frame
    
    def _on_character_swap_requested(self, source_name: str, target_name: str):
        """Testbench의 교체 요청을 CellManager로 전달합니다."""
        if self.cell_manager:
            self.cell_manager.handle_character_swap(source_name, target_name)

    def find_character_in_bench(self, variable_name: str) -> Optional[ClonedStoryItem]:
        """character_testbench에서 이름으로 ClonedStoryItem을 찾습니다."""
        if self.character_testbench:
            all_items = self.character_testbench.get_all_cloned_items()
            for item in all_items:
                if item.variable_name == variable_name:
                    return item
        return None
    
    def _on_clear_all(self):
        """Adventure 탭의 모든 동적 콘텐츠를 초기화합니다."""
        if self.character_testbench:
            self.character_testbench.clear_items()
        
        if self.cell_manager:
            self.cell_manager.clear_all_cells()

        self.app_context.main_window.status_bar.showMessage("✅ Adventure 탭이 초기화되었습니다.", 3000)

    def _on_save_scenario(self):
        """현재 Adventure 탭의 상태를 .json 파일로 저장합니다."""
        if not self.cell_manager or not self.character_testbench:
            return

        # 1. 파일 저장 경로 받기
        file_path, _ = QFileDialog.getSaveFileName(self, "시나리오 저장", "", "JSON Files (*.json)")
        if not file_path:
            return

        # 2. 데이터 수집
        scenario_data = {
            "character_testbench_items": self.character_testbench.get_items_data(),
            "cells": self.cell_manager.get_all_data()
        }

        # 3. 파일로 저장
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(scenario_data, f, indent=4, ensure_ascii=False)
            self.app_context.main_window.status_bar.showMessage(f"✅ 시나리오가 '{Path(file_path).name}'에 저장되었습니다.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"시나리오 저장 중 오류가 발생했습니다:\n{e}")

    def _on_load_scenario(self):
        """'.json' 파일에서 시나리오를 불러와 Adventure 탭 상태를 복원합니다."""
        file_path, _ = QFileDialog.getOpenFileName(self, "시나리오 불러오기", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)

            # 1. 기존 상태 초기화
            self._on_clear_all()
            
            # 2. 데이터로부터 상태 복원
            if self.character_testbench:
                self.character_testbench.load_from_data(scenario_data.get("character_testbench_items", []))
            
            if self.cell_manager:
                # clear_all_cells가 비동기로 초기 셀을 만들 수 있으므로 잠시 기다림
                QTimer.singleShot(10, lambda: self.cell_manager.load_from_data(scenario_data.get("cells", [])))

            self.app_context.main_window.status_bar.showMessage(f"✅ '{Path(file_path).name}' 시나리오를 불러왔습니다.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "로드 오류", f"시나리오를 불러오는 중 오류가 발생했습니다:\n{e}")

    def _on_run_stop_button_clicked(self):
        """RUN/STOP 버튼 클릭을 처리합니다."""
        if self.cell_manager:
            if self.cell_manager.is_scenario_running:
                self.cell_manager.stop_scenario()
            else:
                self.cell_manager.run_scenario()

    def _update_run_button_to_run(self):
        """버튼을 'RUN' 상태로 업데이트합니다."""
        if self.run_button:
            self.run_button.setText("▶ RUN")
            self.run_button.setStyleSheet(DARK_STYLES['primary_button'])

    def _update_run_button_to_stop(self):
        """버튼을 'STOP' 상태로 업데이트합니다."""
        if self.run_button:
            self.run_button.setText("■ STOP")
            self.run_button.setStyleSheet(f"{DARK_STYLES['secondary_button']} background-color: {DARK_COLORS['error']};")

    def _on_immersive_mode_toggled(self, checked: bool):
        """Immersive mode 체크 시 CellManager에 상태를 전달합니다."""
        if self.cell_manager:
            self.cell_manager.set_immersive_mode(checked)

    def _on_save_all_images(self):
        """모든 Cell의 이미지를 지정된 폴더에 저장하도록 CellManager에 요청합니다."""
        if not self.cell_manager or not self.cell_manager.cells:
            QMessageBox.information(self, "알림", "저장할 이미지가 없습니다.")
            return

        # 사용자에게 저장할 폴더 선택 요청
        dir_path = QFileDialog.getExistingDirectory(self, "이미지를 저장할 폴더 선택", "")
        if dir_path:
            saved_count = self.cell_manager.save_all_cell_images(dir_path)
            QMessageBox.information(self, "저장 완료", f"{saved_count}개의 이미지를 성공적으로 저장했습니다.")