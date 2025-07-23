# tabs/storyteller_tab.py

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QTabWidget, 
    QScrollArea, QLabel, QFrame, QTextEdit, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter
from PIL import Image
from PIL.ImageQt import ImageQt

from interfaces.base_tab_module import BaseTabModule
from ui.theme import DARK_STYLES, CUSTOM, DARK_COLORS
from tabs.storyteller.story_box import StoryBox
from tabs.storyteller.story_item_widget import StoryItemWidget

class SquareImageLabel(QLabel):
    # ... [이전과 동일, 변경 없음] ...
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {DARK_COLORS['bg_secondary']}; border: 1px solid {DARK_COLORS['border']}; border-radius: 8px; color: {DARK_COLORS['text_secondary']};")
        self._original_pixmap = None
    def setPixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull(): self._original_pixmap = pixmap; self.update_scaled_pixmap()
        else: self.clear(); self.setText("출력 이미지가 여기에 표시됩니다..."); self._original_pixmap = None
    def resizeEvent(self, event): super().resizeEvent(event); self.update_scaled_pixmap()
    def update_scaled_pixmap(self):
        if self._original_pixmap:
            size = min(self.width(), self.height())
            if size <= 0: return
            scaled_pixmap = self._original_pixmap.scaled(QSize(size, size), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            target = QPixmap(QSize(size, size)); target.fill(Qt.GlobalColor.transparent)
            painter = QPainter(target); x = (size - scaled_pixmap.width()) // 2; y = (size - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap); painter.end()
            super().setPixmap(target)
        else: super().clear(); super().setText("출력 이미지가 여기에 표시됩니다...")

class StorytellerTabModule(BaseTabModule):
    # ... [이전과 동일, 변경 없음] ...
    def __init__(self): super().__init__(); self.widget: StorytellerTab = None
    def get_tab_title(self) -> str: return "📖 Storyteller"
    def get_tab_order(self) -> int: return 5
    def get_tab_type(self) -> str: return 'core'
    def create_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None: self.widget = StorytellerTab(self.app_context, parent)
        return self.widget

class StorytellerTab(QWidget):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.projects_base_dir = "tabs/storyteller"
        self.current_project_path = None
        self.story_boxes = {}
        Path(self.projects_base_dir).mkdir(parents=True, exist_ok=True)
        self.setStyleSheet(f"background-color: {DARK_COLORS['bg_primary']};")
        self.init_ui()

    def init_ui(self):
        # ... [이전과 동일] ...
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(CUSTOM["main_splitter"])
        self.left_panel = self._create_left_panel()
        self.right_panel = self._create_right_panel()
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([350, 1050])
        main_layout.addWidget(splitter)
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None: widget.deleteLater()

    def _create_left_panel(self) -> QWidget:
        main_container = QWidget()
        self.left_panel_layout = QVBoxLayout(main_container)
        self.left_panel_layout.setContentsMargins(0,0,0,0)
        self.left_panel_layout.setSpacing(8)
        self._show_project_selection_ui()
        return main_container

    def _show_project_selection_ui(self):
        self._clear_layout(self.left_panel_layout)
        # ▼▼▼▼▼ [수정] __pycache__ 제외 로직 유지 ▼▼▼▼▼
        project_dirs = [d.name for d in os.scandir(self.projects_base_dir) if d.is_dir() and d.name != "__pycache__"]
        if not project_dirs:
            (Path(self.projects_base_dir) / "default").mkdir(exist_ok=True)
            project_dirs.append("default")
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        title_label = QLabel("프로젝트 선택")
        title_label.setStyleSheet(f"{DARK_STYLES['label_style']} font-size: 18px; font-weight: 600;")
        self.left_panel_layout.addWidget(title_label)
        for project_name in sorted(project_dirs):
            project_card = self._create_project_card(project_name)
            self.left_panel_layout.addWidget(project_card)
        self.left_panel_layout.addStretch(1)

    def _create_project_card(self, project_name: str) -> QFrame:
        # ... [이전과 동일] ...
        card = QFrame()
        card.setStyleSheet(DARK_STYLES['compact_card'])
        layout = QHBoxLayout(card)
        stats_label = QLabel(f"**{project_name}**\n<small>그룹 0개, 아이템 0개</small>")
        stats_label.setTextFormat(Qt.TextFormat.MarkdownText)
        stats_label.setStyleSheet("color: white;")
        start_button = QPushButton("시작")
        start_button.setStyleSheet(DARK_STYLES['primary_button'])
        start_button.setFixedWidth(100)
        start_button.clicked.connect(lambda: self._on_project_start_clicked(project_name))
        layout.addWidget(stats_label)
        layout.addStretch(1)
        layout.addWidget(start_button)
        return card

    def _on_project_start_clicked(self, project_name: str):
        self.current_project_path = Path(self.projects_base_dir) / project_name
        self._clear_layout(self.left_panel_layout)
        self._load_project_ui(project_name)

    def _load_project_ui(self, project_name: str):
        self.story_boxes.clear()
        
        # 1. 상단 고정 컨트롤 패널 추가
        control_panel = QFrame()
        control_panel.setStyleSheet(DARK_STYLES['compact_card'])
        control_layout = QHBoxLayout(control_panel)
        add_group_btn = QPushButton("➕ 그룹 추가")
        add_group_btn.setStyleSheet(DARK_STYLES['secondary_button'])
        search_item_input = QLineEdit()
        search_item_input.setPlaceholderText("🔎 아이템 검색...")
        search_item_input.setStyleSheet(DARK_STYLES['compact_lineedit'])
        # ▼▼▼▼▼ [신규] 종료 버튼 추가 ▼▼▼▼▼
        exit_button = QPushButton("↩️ 종료")
        exit_button.setStyleSheet(DARK_STYLES['secondary_button'])
        exit_button.clicked.connect(self._on_exit_project_clicked)
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        control_layout.addWidget(add_group_btn)
        control_layout.addWidget(search_item_input, 1) # 검색창이 남은 공간을 채우도록
        control_layout.addWidget(exit_button)
        self.left_panel_layout.addWidget(control_panel)

        # 2. StoryBox들을 담을 스크롤 영역 추가
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(CUSTOM["middle_scroll_area"])
        container = QWidget()
        self.story_box_layout = QVBoxLayout(container)
        self.story_box_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.story_box_layout.setSpacing(8)
        
        # ▼▼▼▼▼ [수정] 프로젝트 폴더를 재귀적으로 스캔하여 StoryBox 계층 구조 동적 생성 ▼▼▼▼▼
        project_path = Path(self.projects_base_dir) / project_name
        
        # 최상위 그룹 (UpperLevel)
        group_dirs = [d for d in project_path.iterdir() if d.is_dir()]
        if not group_dirs:
            (project_path / "characters").mkdir(exist_ok=True)
            group_dirs.append(project_path / "characters")
        
        for group_dir in sorted(group_dirs):
            group_name = group_dir.name
            box = StoryBox(title=group_name.capitalize(), variable_name=group_name, level='upper')
            box.subgroup_add_requested.connect(self._on_subgroup_add_requested)
            
            # 하위 그룹 (LowerLevel)
            subgroup_dirs = [d for d in group_dir.iterdir() if d.is_dir()]
            for subgroup_dir in sorted(subgroup_dirs):
                subgroup_name = subgroup_dir.name
                sub_box = StoryBox(title=subgroup_name, variable_name=subgroup_name, level='lower')
                box.add_subgroup(sub_box)
                self.story_boxes[f"{group_name}/{subgroup_name}"] = sub_box # 하위 그룹도 참조
            
            self.story_box_layout.addWidget(box)
            self.story_boxes[group_name] = box # 상위 그룹 참조
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
        scroll_area.setWidget(container)
        self.left_panel_layout.addWidget(scroll_area)

    # ▼▼▼▼▼ [신규] 프로젝트 종료 버튼 핸들러 ▼▼▼▼▼
    def _on_exit_project_clicked(self):
        """프로젝트를 닫고 프로젝트 선택 화면으로 돌아갑니다."""
        # 메모리 정리
        self.story_boxes.clear()
        self.current_project_path = None
        # 프로젝트 선택 UI 다시 표시
        self._show_project_selection_ui()
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    
    def _on_subgroup_add_requested(self, parent_group_name, new_group_name):
        """StoryBox에서 받은 하위 그룹 추가 요청을 처리합니다."""
        if not self.current_project_path:
            QMessageBox.critical(self, "오류", "현재 활성화된 프로젝트가 없습니다.")
            return

        try:
            # 1. 실제 하위 폴더 생성 (self.current_project_path 사용)
            new_group_path = self.current_project_path / parent_group_name / new_group_name
            new_group_path.mkdir(exist_ok=False)

            # 2. UI에 LowerLevel StoryBox 추가
            parent_box = self.story_boxes.get(parent_group_name)
            if parent_box:
                sub_box = StoryBox(title=new_group_name, variable_name=new_group_name, level='lower')
                parent_box.add_subgroup(sub_box)
                self.story_boxes[f"{parent_group_name}/{new_group_name}"] = sub_box
                QMessageBox.information(self, "성공", f"하위 그룹 '{new_group_name}'을(를) 추가했습니다.")
            else:
                raise ValueError(f"부모 그룹 '{parent_group_name}'을 찾을 수 없습니다.")

        except FileExistsError:
            QMessageBox.warning(self, "오류", f"이미 '{new_group_name}' 이름의 하위 그룹이 존재합니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"하위 그룹 추가 중 오류 발생: {e}")
            print(f"하위 그룹 추가 중 오류: {e}")
    
    # ... [나머지 메서드들은 이전과 동일] ...
    def _create_right_panel(self) -> QWidget:
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(DARK_STYLES['dark_tabs'])
        workshop_tab = self._create_workshop_ui()
        adventure_tab = QWidget()
        adventure_layout = QVBoxLayout(adventure_tab)
        adventure_label = QLabel("🚀 Adventure\n\n완성된 스토리를 바탕으로 새로운 이야기를 생성하고 탐험합니다.")
        adventure_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        adventure_label.setStyleSheet(f"{DARK_STYLES['label_style']} color: {DARK_COLORS['text_secondary']};")
        adventure_layout.addWidget(adventure_label)
        tab_widget.addTab(workshop_tab, "Workshop")
        tab_widget.addTab(adventure_tab, "Adventure")
        return tab_widget

    def _create_workshop_ui(self) -> QWidget:
        workshop_widget = QWidget()
        main_v_layout = QVBoxLayout(workshop_widget)
        main_v_layout.setContentsMargins(0, 8, 0, 0)
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setStyleSheet(CUSTOM["main_splitter"])
        top_panel = QWidget()
        top_h_layout = QHBoxLayout(top_panel)
        top_h_layout.setContentsMargins(0, 0, 0, 0)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setStyleSheet(CUSTOM["main_splitter"])
        left_input_panel = QWidget()
        left_v_layout = QVBoxLayout(left_input_panel)
        left_v_layout.setSpacing(8)
        self.positive_prompt_edit = QTextEdit()
        self.positive_prompt_edit.setPlaceholderText("Positive Prompt 입력...")
        self.positive_prompt_edit.setStyleSheet(DARK_STYLES['compact_textedit'])
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setPlaceholderText("Negative Prompt 입력...")
        self.negative_prompt_edit.setStyleSheet(DARK_STYLES['compact_textedit'])
        self.generate_button = QPushButton("Generate")
        self.generate_button.setStyleSheet(DARK_STYLES['primary_button'])
        self.generate_button.clicked.connect(self._on_workshop_generate_clicked)
        left_v_layout.addWidget(self.positive_prompt_edit, 1)
        left_v_layout.addWidget(self.negative_prompt_edit, 1)
        left_v_layout.addWidget(self.generate_button)
        self.right_output_panel = SquareImageLabel()
        h_splitter.addWidget(left_input_panel)
        h_splitter.addWidget(self.right_output_panel)
        h_splitter.setSizes([400, 600])
        top_h_layout.addWidget(h_splitter)
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet(DARK_STYLES['compact_card'])
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_label = QLabel("하단 UI 영역")
        bottom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']};")
        bottom_layout.addWidget(bottom_label)
        v_splitter.addWidget(top_panel)
        v_splitter.addWidget(bottom_panel)
        v_splitter.setStretchFactor(0, 8)
        v_splitter.setStretchFactor(1, 2)
        main_v_layout.addWidget(v_splitter)
        return workshop_widget
    
    def _on_workshop_generate_clicked(self):
        positive_prompt = self.positive_prompt_edit.toPlainText().strip()
        if not positive_prompt:
            self.app_context.main_window.status_bar.showMessage("⚠️ Positive Prompt를 입력해주세요.", 3000)
            return
        try:
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if char_module and char_module.activate_checkbox.isChecked():
                char_module.activate_checkbox.setChecked(False)
                print("ℹ️ Workshop 생성: 캐릭터 모듈을 비활성화했습니다.")
                self.app_context.main_window.status_bar.showMessage("캐릭터 모듈이 임시 비활성화되었습니다.", 2000)
        except Exception as e:
            print(f"⚠️ 캐릭터 모듈 비활성화 실패: {e}")
        override_params = {
            "input": positive_prompt,
            "negative_prompt": self.negative_prompt_edit.toPlainText(),
            "width": 1024,
            "height": 1024,
            "random_resolution": False
        }
        self.app_context.subscribe("generation_completed_for_redirect", self._on_workshop_image_generated)
        gen_controller = self.app_context.main_window.generation_controller
        gen_controller.execute_generation_pipeline(overrides=override_params)

    def _on_workshop_image_generated(self, result: dict):
        self.app_context.subscribers["generation_completed_for_redirect"].remove(self._on_workshop_image_generated)
        image_object = result.get("image")
        if isinstance(image_object, Image.Image):
            q_image = ImageQt(image_object)
            pixmap = QPixmap.fromImage(q_image)
            if not pixmap.isNull():
                self.right_output_panel.setPixmap(pixmap)
                print("✅ Workshop 이미지 업데이트 완료.")
            else:
                print("❌ QPixmap 변환 실패.")
        else:
            print(f"⚠️ 전달받은 결과에 유효한 이미지가 없습니다: {type(image_object)}")