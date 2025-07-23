import os, json
from pathlib import Path
import fnmatch
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QTabWidget, 
    QScrollArea, QLabel, QFrame, QTextEdit, QPushButton, QLineEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from PIL import Image
from PIL.ImageQt import ImageQt

from interfaces.base_tab_module import BaseTabModule
from ui.theme import DARK_STYLES, CUSTOM, DARK_COLORS
from tabs.storyteller.story_box import StoryBox
from tabs.storyteller.story_item_widget import StoryItemWidget
from tabs.storyteller.custom_dialogs import CustomInputDialog

class StableImageWidget(QWidget):
    """
    paintEvent를 직접 구현하여 resize 루프를 원천적으로 방지하는
    안정적인 이미지 표시 위젯.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        # setSizePolicy를 통해 위젯이 공간을 채우도록 설정
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setPixmap(self, pixmap: QPixmap):
        """표시할 원본 QPixmap을 설정하고, 위젯에 다시 그리도록 요청합니다."""
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
        else:
            self._pixmap = None
        self.update() # paintEvent를 다시 호출하도록 요청

    def paintEvent(self, event):
        """위젯을 다시 그려야 할 때마다 호출됩니다."""
        painter = QPainter(self)
        
        # 1. 위젯의 배경을 어두운 색으로 채웁니다.
        painter.fillRect(self.rect(), QColor(DARK_COLORS['bg_secondary']))
        
        if not self._pixmap:
            # 2. 이미지가 없으면 플레이스홀더 텍스트를 그립니다.
            painter.setPen(QColor(DARK_COLORS['text_secondary']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "출력 이미지가 여기에 표시됩니다...")
            return

        # 3. 위젯의 가용 공간 안에서 1:1 정사각형 영역을 계산합니다.
        widget_size = self.size()
        square_size = min(widget_size.width(), widget_size.height())
        
        # 4. 원본 이미지를 위에서 계산된 정사각형 크기에 맞춰 스케일링합니다.
        scaled_pixmap = self._pixmap.scaled(
            QSize(square_size, square_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 5. 스케일링된 이미지를 위젯의 중앙에 그립니다.
        x = (widget_size.width() - scaled_pixmap.width()) // 2
        y = (widget_size.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

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
        self.projects_base_dir = Path("tabs/storyteller")
        self.global_dir = self.projects_base_dir / "global"
        self.global_dir.mkdir(parents=True, exist_ok=True)
        self.current_project_path = None
        self.story_boxes = {}
        Path(self.projects_base_dir).mkdir(parents=True, exist_ok=True)
        self.active_story_box = None
        self.expanded_upper_box = None
        self.expanded_lower_box = None
        self.save_path_label = None
        self.variable_name_input = None
        self.setStyleSheet(f"background-color: {DARK_COLORS['bg_primary']};")
        self.init_ui()
        self.load_settings()

    def _get_project_stats(self, project_path: Path) -> int | int:
        """프로젝트 내의 그룹(폴더) 수와 아이템(.json) 수를 반환합니다."""
        group_count = 0
        item_count = 0
        if project_path.is_dir():
            for root, dirs, files in os.walk(project_path):
                # 최상위 폴더는 그룹 수에서 제외
                if Path(root) != project_path:
                    group_count += len(dirs)
                
                # .json 파일 수 계산
                item_count += len(fnmatch.filter(files, '*.json'))
            
            # 최상위 그룹 수 추가
            group_count += len([d for d in project_path.iterdir() if d.is_dir()])
            
        return group_count, item_count

    def _show_project_selection_ui(self):
        self._clear_layout(self.left_panel_layout)
        
        # --- 타이틀 및 새 프로젝트 추가 버튼 ---
        title_layout = QHBoxLayout()
        title_label = QLabel("프로젝트 선택")
        title_label.setStyleSheet(f"{DARK_STYLES['label_style']} font-size: 18px; font-weight: 600;")
        
        add_project_btn = QPushButton("➕ 새 프로젝트")
        add_project_btn.setStyleSheet(DARK_STYLES['secondary_button'])
        add_project_btn.clicked.connect(self._on_add_project_clicked)

        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(add_project_btn)
        self.left_panel_layout.addLayout(title_layout)

        # --- 프로젝트 목록 ---
        project_dirs = [d.name for d in os.scandir(self.projects_base_dir) if d.is_dir() and d.name not in ["__pycache__", "global"]]
        if not project_dirs:
            (self.projects_base_dir / "default").mkdir(exist_ok=True)
            project_dirs.append("default")
        
        for project_name in sorted(project_dirs):
            # 프로젝트 통계 계산
            project_path = self.projects_base_dir / project_name
            group_count, item_count = self._get_project_stats(project_path)
            # 통계와 함께 카드 생성
            project_card = self._create_project_card(project_name, group_count, item_count)
            self.left_panel_layout.addWidget(project_card)
        
        self.left_panel_layout.addStretch(1)

    def _create_project_card(self, project_name: str, group_count: int, item_count: int) -> QFrame:
        card = QFrame()
        card.setStyleSheet(DARK_STYLES['compact_card'])
        layout = QHBoxLayout(card)
        # 통계 정보를 라벨에 표시
        stats_label = QLabel(f"**{project_name}**\n<small>그룹 {group_count}개, 아이템 {item_count}개</small>")
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

    def _on_project_start_clicked(self, project_name: str):
        self.current_project_path = Path(self.projects_base_dir) / project_name
        self._clear_layout(self.left_panel_layout)
        self._load_project_ui(project_name)

    def _load_project_ui(self, project_name: str):
        self.story_boxes.clear()
        self.active_story_box = None
        self.expanded_upper_box = None
        self.expanded_lower_box = None
        
        control_panel = QFrame()
        control_panel.setStyleSheet(DARK_STYLES['compact_card'])
        control_layout = QHBoxLayout(control_panel)
        add_group_btn = QPushButton("➕ 그룹 추가")
        add_group_btn.setStyleSheet(DARK_STYLES['secondary_button'])
        add_group_btn.clicked.connect(self._on_add_group_clicked)
        search_item_input = QLineEdit()
        search_item_input.setPlaceholderText("🔎 아이템 검색...")
        search_item_input.setStyleSheet(DARK_STYLES['compact_lineedit'])
        search_item_input.setProperty("autocomplete_ignore", True)
        exit_button = QPushButton("↩️ 종료")
        exit_button.setStyleSheet(DARK_STYLES['secondary_button'])
        exit_button.clicked.connect(self._on_exit_project_clicked)
        control_layout.addWidget(add_group_btn)
        control_layout.addWidget(search_item_input, 1)
        control_layout.addWidget(exit_button)
        self.left_panel_layout.addWidget(control_panel)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(CUSTOM["middle_scroll_area"])
        container = QWidget()
        self.story_box_layout = QVBoxLayout(container)
        self.story_box_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.story_box_layout.setSpacing(8)
        
        project_path = self.projects_base_dir / project_name
        self._load_groups_from_path(project_path, "Local")
        self._load_groups_from_path(self.global_dir, "Global")
        
        scroll_area.setWidget(container)
        self.left_panel_layout.addWidget(scroll_area)

    def _load_groups_from_path(self, path: Path, section_title: str):
        group_dirs = [d for d in path.iterdir() if d.is_dir()]
        if not group_dirs and section_title == "Local":
            (path / "characters").mkdir(exist_ok=True)
            group_dirs.append(path / "characters")

        if group_dirs:
            title_label = QLabel(f"--- {section_title} ---")
            title_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; margin-top: 10px;")
            self.story_box_layout.addWidget(title_label)

            for group_dir in sorted(group_dirs):
                group_name = group_dir.name
                box = StoryBox(title=group_name.capitalize(), variable_name=group_name, level='upper')
                box.expanded.connect(self._on_story_box_expanded)
                box.focused.connect(self._on_story_box_focused)
                box.subgroup_add_requested.connect(self._on_subgroup_add_requested)
                box.collapse()
                subgroup_dirs = [d for d in group_dir.iterdir() if d.is_dir()]
                for subgroup_dir in sorted(subgroup_dirs):
                    subgroup_name = subgroup_dir.name
                    # ▼▼▼▼▼ [수정] parent_box 인자 전달 ▼▼▼▼▼
                    sub_box = StoryBox(title=subgroup_name, variable_name=subgroup_name, level='lower', parent_box=box)
                    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                    sub_box.expanded.connect(self._on_story_box_expanded)
                    sub_box.focused.connect(self._on_story_box_focused)
                    sub_box.collapsed.connect(self._on_story_box_collapsed)
                    sub_box.collapse()
                    box.add_subgroup(sub_box)
                    self.story_boxes[f"{group_name}/{subgroup_name}"] = sub_box
                
                self.story_box_layout.addWidget(box)
                self.story_boxes[group_name] = box

    def _on_exit_project_clicked(self):
        """프로젝트를 닫고 프로젝트 선택 화면으로 돌아갑니다."""
        # 메모리 정리
        self.story_boxes.clear()
        self.current_project_path = None
        self.active_story_box = None
        self.expanded_upper_box = None
        self.expanded_lower_box = None
        if self.save_path_label:
            self.save_path_label.setText("저장되는 경로: 선택되지 않음")
        self._show_project_selection_ui()

    def _on_add_group_clicked(self):
        """상단 컨트롤 패널의 '그룹 추가' 버튼 클릭 시 호출됩니다."""
        if not self.current_project_path: return

        # ▼▼▼▼▼ 수정된 부분: 스타일시트를 적용하는 방식으로 변경 ▼▼▼▼▼
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("그룹 저장 위치 선택")
        msg_box.setText("새로운 그룹을 어디에 추가하시겠습니까?")
        
        # 스타일시트를 통해 전체적인 폰트 색상 및 배경을 지정합니다.
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {DARK_COLORS['bg_secondary']};
            }}
            QLabel {{
                color: {DARK_COLORS['text_primary']};
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {DARK_COLORS['accent_blue']};
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {DARK_COLORS['accent_blue_hover']};
            }}
        """)

        local_button = msg_box.addButton("Local (현재 프로젝트)", QMessageBox.ButtonRole.YesRole)
        global_button = msg_box.addButton("Global (모든 프로젝트)", QMessageBox.ButtonRole.NoRole)
        msg_box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        clicked_button = msg_box.clickedButton()
        if clicked_button == local_button:
            target_path = self.current_project_path
        elif clicked_button == global_button:
            target_path = self.global_dir
        else:
            return

        text, ok = CustomInputDialog.getText(self, '최상위 그룹 추가', '새 그룹의 이름을 입력하세요:')
        if ok and text:
            try:
                new_group_path = target_path / text
                if new_group_path.exists():
                    raise FileExistsError
                
                new_group_path.mkdir()

                box = StoryBox(title=text.capitalize(), variable_name=text, level='upper')
                box.subgroup_add_requested.connect(self._on_subgroup_add_requested)
                
                # TODO: Local/Global 섹션을 구분하여 올바른 위치에 위젯 추가 필요
                self.story_box_layout.addWidget(box)
                self.story_boxes[text] = box
                QMessageBox.information(self, "성공", f"그룹 '{text}'을(를) 추가했습니다.")

            except FileExistsError:
                QMessageBox.warning(self, "오류", f"이미 '{text}' 이름의 그룹이 해당 위치에 존재합니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"그룹 추가 중 오류 발생: {e}")
    
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
        self.right_output_panel = StableImageWidget()
        h_splitter.addWidget(left_input_panel)
        h_splitter.addWidget(self.right_output_panel)
        h_splitter.setSizes([400, 600])
        top_h_layout.addWidget(h_splitter)
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet(DARK_STYLES['compact_card'])
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setSpacing(10)
        # --- 고정 프롬프트 영역 ---
        prompt_panel_layout = QHBoxLayout()
        
        # 선행 프롬프트
        prefix_group = QWidget()
        prefix_layout = QVBoxLayout(prefix_group)
        prefix_layout.setContentsMargins(0,0,0,0)
        prefix_label = QLabel("선행 고정 프롬프트")
        prefix_label.setStyleSheet(DARK_STYLES['label_style'])
        self.prefix_prompt_edit = QTextEdit()
        self.prefix_prompt_edit.setPlaceholderText("#Action을 수행 할 대상 혹은 먼저 배치될 프롬프트들을 기입합니다... 이곳에 작성한 텍스트는 별도로 저장되지 않습니다.")
        self.prefix_prompt_edit.setStyleSheet(DARK_STYLES['dark_text_edit'])
        self.prefix_prompt_edit.setFixedHeight(160)
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_prompt_edit)
        
        # 후행 프롬프트
        postfix_group = QWidget()
        postfix_layout = QVBoxLayout(postfix_group)
        postfix_layout.setContentsMargins(0,0,0,0)
        postfix_label = QLabel("후행 고정 프롬프트")
        postfix_label.setStyleSheet(DARK_STYLES['label_style'])
        self.postfix_prompt_edit = QTextEdit()
        self.postfix_prompt_edit.setPlaceholderText("#아티스트 태그, 퀄리티 프롬프트 등을 기입합니다... 이곳에 작성한 텍스트는 별도로 저장되지 않습니다.")
        self.postfix_prompt_edit.setStyleSheet(DARK_STYLES['dark_text_edit'])
        self.postfix_prompt_edit.setFixedHeight(160)
        postfix_layout.addWidget(postfix_label)
        postfix_layout.addWidget(self.postfix_prompt_edit)
        
        prompt_panel_layout.addWidget(prefix_group)
        prompt_panel_layout.addWidget(postfix_group)
        bottom_layout.addLayout(prompt_panel_layout)

        # --- 저장 버튼 및 경로 표시 영역 ---
        save_panel = QFrame()
        save_panel.setFixedHeight(100)
        save_panel_layout = QHBoxLayout(save_panel)
        
        save_button = QPushButton("💾 저장")
        save_button.setStyleSheet(DARK_STYLES['secondary_button'])
        save_button.setFixedWidth(120)

        self.variable_name_input = QLineEdit()
        self.variable_name_input.setPlaceholderText("변수명입력...")
        self.variable_name_input.setStyleSheet(f"""
            {DARK_STYLES['compact_lineedit']}
            background-color: {DARK_COLORS['bg_primary']};
        """)
        self.variable_name_input.setProperty("autocomplete_ignore", True)
        self.variable_name_input.setFixedWidth(200) # 적절한 너비로 고정
        
        self.save_path_label = QLabel("저장되는 경로: 선택되지 않음")
        self.save_path_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}")
        save_button.clicked.connect(self._on_save_item_clicked)
        
        save_panel_layout.addWidget(save_button)
        save_panel_layout.addWidget(self.variable_name_input)
        save_panel_layout.addWidget(self.save_path_label)
        save_panel_layout.addStretch(1)
        bottom_layout.addWidget(save_panel)
        v_splitter.addWidget(top_panel)
        v_splitter.addWidget(bottom_panel)
        v_splitter.setStretchFactor(0, 8)
        v_splitter.setStretchFactor(1, 2)
        main_v_layout.addWidget(v_splitter)
        return workshop_widget
    
    def _on_workshop_generate_clicked(self):
        self.save_settings()
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
        prompt_parts = [
            self.prefix_prompt_edit.toPlainText().strip(),
            positive_prompt.strip(),
            self.postfix_prompt_edit.toPlainText().strip()
        ]
        final_parts = [part for part in prompt_parts if part]
        final_prompt = ", ".join(final_parts)
        override_params = {
            "input": final_prompt,
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

    def _on_story_box_expanded(self, expanded_box: StoryBox):
        """하나의 박스가 펼쳐지면 다른 박스를 접는 계층적 로직."""
        if expanded_box.level == 'upper':
            # 1. UpperLevel 박스가 펼쳐진 경우
            # 다른 UpperLevel 박스가 열려 있었다면 닫는다.
            if self.expanded_upper_box and self.expanded_upper_box is not expanded_box:
                self.expanded_upper_box.collapse()
            
            # 이전에 다른 그룹의 하위 그룹이 열려 있었다면 닫는다.
            if self.expanded_lower_box:
                self.expanded_lower_box.collapse()
                self.expanded_lower_box = None
            
            # 현재 펼쳐진 UpperLevel 박스로 기록한다.
            self.expanded_upper_box = expanded_box

        elif expanded_box.level == 'lower':
            # 2. LowerLevel 박스가 펼쳐진 경우
            # 같은 부모 아래의 다른 LowerLevel 박스가 열려 있었다면 닫는다.
            if (self.expanded_lower_box and 
                self.expanded_lower_box is not expanded_box and
                self.expanded_lower_box.parent_box is expanded_box.parent_box):
                self.expanded_lower_box.collapse()
            
            # 현재 펼쳐진 LowerLevel 박스로 기록한다.
            self.expanded_lower_box = expanded_box
            
            # 이 하위 그룹의 부모가 아닌 다른 상위 그룹이 열려있다면 닫는다.
            if self.expanded_upper_box and self.expanded_upper_box is not expanded_box.parent_box:
                self.expanded_upper_box.collapse()
            
            # 현재 상위 그룹을 이 하위 그룹의 부모로 설정한다.
            self.expanded_upper_box = expanded_box.parent_box

    def _on_story_box_focused(self, focused_box: StoryBox):
        """하나의 박스가 포커스되면 다른 박스의 포커스를 해제합니다."""
        # 이전에 포커스된 박스가 있고, 지금 포커스된 박스와 다르다면 포커스를 해제합니다.
        if self.active_story_box and self.active_story_box is not focused_box:
            self.active_story_box.set_focused(False)
        
        # 새로 포커스된 박스에 포커스를 설정하고 기록합니다.
        focused_box.set_focused(True)
        self.active_story_box = focused_box
        if self.save_path_label:
            path_text = focused_box.variable_name
            if focused_box.level == 'lower' and focused_box.parent_box:
                path_text = f"{focused_box.parent_box.variable_name} / {path_text}"
            self.save_path_label.setText(f"저장되는 경로: {path_text}")

    def _on_story_box_collapsed(self, collapsed_box: StoryBox):
        """하위 그룹 박스가 접혔을 때 호출됩니다."""
        # 접힌 박스가 현재 펼쳐진 하위 그룹과 동일한지 확인
        if self.expanded_lower_box and self.expanded_lower_box is collapsed_box:
            self.expanded_lower_box = None
            # 부모가 존재하면 부모에게 포커스를 반환
            if collapsed_box.parent_box:
                self._on_story_box_focused(collapsed_box.parent_box)

    def _on_add_project_clicked(self):
        """새 프로젝트 추가 버튼 클릭 시 호출됩니다."""
        text, ok = CustomInputDialog.getText(self, '새 프로젝트 생성', '새 프로젝트의 이름을 입력하세요:')
        if ok and text:
            try:
                # 유효하지 않은 이름 검사
                if text in ["__pycache__", "global"]:
                    raise ValueError(f"'{text}'는 사용할 수 없는 프로젝트 이름입니다.")

                new_project_path = self.projects_base_dir / text
                if new_project_path.exists():
                    raise FileExistsError
                
                new_project_path.mkdir()
                print(f"✅ 새 프로젝트 폴더 '{text}'를 생성했습니다.")
                
                # 프로젝트 목록 새로고침
                self._show_project_selection_ui()

            except FileExistsError:
                QMessageBox.warning(self, "오류", f"이미 '{text}' 이름의 프로젝트가 존재합니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"프로젝트 생성 중 오류 발생: {e}")

    def save_settings(self):
        """Workshop의 프롬프트들을 JSON 파일에 저장합니다."""
        settings_path = self.projects_base_dir / "save.json"
        try:
            settings_data = {
                "prefix_prompt": self.prefix_prompt_edit.toPlainText(),
                "positive_prompt": self.positive_prompt_edit.toPlainText(),
                "postfix_prompt": self.postfix_prompt_edit.toPlainText(),
                "negative_prompt": self.negative_prompt_edit.toPlainText(),
            }
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
            print(f"✅ Storyteller 설정 저장 완료: {settings_path}")
        except Exception as e:
            print(f"❌ Storyteller 설정 저장 실패: {e}")

    def load_settings(self):
        """JSON 파일에서 Workshop 프롬프트들을 불러옵니다."""
        settings_path = self.projects_base_dir / "save.json"
        if not settings_path.exists():
            return
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            self.prefix_prompt_edit.setText(settings_data.get("prefix_prompt", ""))
            self.positive_prompt_edit.setText(settings_data.get("positive_prompt", ""))
            self.postfix_prompt_edit.setText(settings_data.get("postfix_prompt", ""))
            self.negative_prompt_edit.setText(settings_data.get("negative_prompt", ""))
            print(f"✅ Storyteller 설정 로드 완료: {settings_path}")
        except Exception as e:
            print(f"❌ Storyteller 설정 로드 실패: {e}")

    def _on_save_item_clicked(self):
        """'저장' 버튼 클릭 시 아이템을 생성하고 저장하는 전체 로직."""
        # 1. 입력값 유효성 검사
        if not self.active_story_box:
            QMessageBox.warning(self, "오류", "아이템을 저장할 그룹 또는 하위 그룹을 먼저 선택(클릭)해주세요.")
            return
        if self.active_story_box.level == 'upper':
            QMessageBox.warning(self, "오류", "최상위 그룹에는 아이템을 직접 저장할 수 없습니다.\n하위 그룹을 선택하거나 생성해주세요.")
            return
        
        variable_name = self.variable_name_input.text()
        if not variable_name:
            QMessageBox.warning(self, "오류", "저장할 아이템의 변수명을 입력해주세요.")
            return

        # 2. 이미지 가져오기 및 처리
        source_pixmap = self.right_output_panel._pixmap
        if not source_pixmap or source_pixmap.isNull():
            QMessageBox.warning(self, "오류", "저장할 이미지가 없습니다. 먼저 이미지를 생성해주세요.")
            return

        try:
            # QPixmap -> PIL Image 변환
            pil_image = Image.fromqpixmap(source_pixmap)
            
            # 중앙 75% 크롭
            w, h = pil_image.size
            crop_w, crop_h = int(w * 0.75), int(h * 0.75)
            left = (w - crop_w) // 2
            top = (h - crop_h) // 2
            right = left + crop_w
            bottom = top + crop_h
            cropped_image = pil_image.crop((left, top, right, bottom))

            # 128x128 썸네일 생성
            cropped_image.thumbnail((128, 128), Image.Resampling.LANCZOS)
            
            # PIL Image -> QPixmap 변환
            thumbnail_pixmap = QPixmap.fromImage(ImageQt(cropped_image))

        except Exception as e:
            QMessageBox.critical(self, "오류", f"이미지 처리 중 오류가 발생했습니다: {e}")
            return
            
        # 3. StoryItemWidget 생성 및 저장
        group_box = self.active_story_box
        group_name = f"{group_box.parent_box.variable_name}/{group_box.variable_name}"
        
        item_widget = StoryItemWidget(
            project_path=str(self.current_project_path),
            group_name=group_name,
            variable_name=variable_name
        )
        item_widget.thumbnail_label.setPixmap(thumbnail_pixmap)
        
        # 생성에 사용된 프롬프트 정보도 함께 저장
        item_widget.data = {
            "prefix": self.prefix_prompt_edit.toPlainText(),
            "positive": self.positive_prompt_edit.toPlainText(),
            "postfix": self.postfix_prompt_edit.toPlainText(),
            "negative": self.negative_prompt_edit.toPlainText(),
        }
        
        item_widget.save_data() # 파일로 저장

        # 4. UI에 위젯 추가
        group_box.add_item(item_widget)

        self.save_settings()
        
        # 5. 완료 처리
        self.variable_name_input.clear()
        self.app_context.main_window.status_bar.showMessage(f"✅ 아이템 '{variable_name}' 저장 완료!", 3000)