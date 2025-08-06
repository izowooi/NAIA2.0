import os, json
from pathlib import Path
import fnmatch, shutil
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
from ui.scaling_manager import get_scaled_font_size
from tabs.storyteller.story_box import StoryBox
from tabs.storyteller.story_item_widget import StoryItemWidget
from tabs.storyteller.custom_dialogs import CustomInputDialog, ConfirmationDialog, style_qmessagebox
from tabs.storyteller.item_editor import ItemEditorWidget
from tabs.storyteller.testbench_widget import TestbenchWidget
from tabs.storyteller.adventure_tab import AdventureTab

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
        title_label.setStyleSheet(f"{DARK_STYLES['label_style']} font-size: {get_scaled_font_size(18)}px; font-weight: 600;")
        
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
        is_global_section = (section_title == "Global")
        group_dirs = [d for d in path.iterdir() if d.is_dir()]
        
        if not group_dirs and not is_global_section:
            (path / "characters").mkdir(exist_ok=True)
            group_dirs.append(path / "characters")

        if group_dirs:
            title_label = QLabel(f"--- {section_title} Groups ---")
            title_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; margin-top: 10px;")
            self.story_box_layout.addWidget(title_label)

            for group_dir in sorted(group_dirs):
                group_name = group_dir.name
                box = StoryBox(title=group_name.capitalize(), variable_name=group_name, box_path=str(group_dir), level='upper', is_global=is_global_section)
                box.expanded.connect(self._on_story_box_expanded)
                box.focused.connect(self._on_story_box_focused)
                box.subgroup_add_requested.connect(self._on_subgroup_add_requested)
                box.delete_requested.connect(self._on_story_box_delete_requested)
                # 하위 그룹 (LowerLevel) 및 아이템 스캔
                subgroup_dirs = [d for d in group_dir.iterdir() if d.is_dir()]
                for subgroup_dir in sorted(subgroup_dirs):
                    subgroup_name = subgroup_dir.name
                    sub_box = StoryBox(title=subgroup_name, variable_name=subgroup_name, box_path=str(subgroup_dir), level='lower', parent_box=box, is_global=is_global_section)
                    sub_box.expanded.connect(self._on_story_box_expanded)
                    sub_box.focused.connect(self._on_story_box_focused)
                    sub_box.collapsed.connect(self._on_story_box_collapsed)
                    sub_box.delete_requested.connect(self._on_story_box_delete_requested)
                    item_files = [f for f in subgroup_dir.iterdir() if f.is_file() and f.suffix == '.json']
                    for item_file in item_files:
                        variable_name = item_file.stem
                        item_widget = StoryItemWidget(
                            group_path=str(subgroup_dir), 
                            variable_name=variable_name,
                            parent_box=sub_box
                        )
                        item_widget.edit_requested.connect(self._on_item_edit_requested)
                        sub_box.add_item(item_widget)

                    sub_box.collapse()
                    box.add_subgroup(sub_box)
                    self.story_boxes[f"{group_name}/{subgroup_name}"] = sub_box
                
                box.collapse()
                self.story_box_layout.addWidget(box)
                self.story_boxes[group_name] = box

    def find_item_widget(self, group_path: str, variable_name: str) -> StoryItemWidget | None:
        """전체 StoryBox 목록을 탐색하여 요청된 StoryItemWidget을 찾습니다."""
        for box in self.story_boxes.values():
            # box_path가 문자열로 저장되어 있으므로 Path 객체로 비교
            if box.level == 'lower' and Path(box.box_path) == Path(group_path):
                return box.items.get(variable_name)
        return None

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

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("그룹 저장 위치 선택")
        msg_box.setText("새로운 그룹을 어디에 추가하시겠습니까?")
        style_qmessagebox(msg_box)
        local_button = msg_box.addButton("Local (현재 프로젝트)", QMessageBox.ButtonRole.YesRole)
        global_button = msg_box.addButton("Global (모든 프로젝트)", QMessageBox.ButtonRole.NoRole)
        msg_box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == local_button: target_path = self.current_project_path
        elif clicked_button == global_button: target_path = self.global_dir
        else: return
        
        text, ok = CustomInputDialog.getText(self, '최상위 그룹 추가', '새 그룹의 이름을 입력하세요:')
        if ok and text:
            try:
                new_group_path = target_path / text
                if new_group_path.exists(): raise FileExistsError
                new_group_path.mkdir()

                box = StoryBox(
                    title=text.capitalize(), 
                    variable_name=text, 
                    box_path=str(new_group_path),
                    level='upper', 
                    is_global=(target_path == self.global_dir)
                )
                
                # ▼▼▼▼▼ [수정] 누락된 시그널 연결 추가 ▼▼▼▼▼
                box.expanded.connect(self._on_story_box_expanded)
                box.focused.connect(self._on_story_box_focused)
                box.collapsed.connect(self._on_story_box_collapsed)
                box.subgroup_add_requested.connect(self._on_subgroup_add_requested)
                box.delete_requested.connect(self._on_story_box_delete_requested)
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                
                self.story_box_layout.addWidget(box)
                self.story_boxes[text] = box
                
                info_box = QMessageBox(self); info_box.setIcon(QMessageBox.Icon.Information)
                info_box.setWindowTitle("성공"); info_box.setText(f"그룹 '{text}'을(를) 추가했습니다.")
                style_qmessagebox(info_box); info_box.exec()

            except FileExistsError:
                warn_box = QMessageBox(self); warn_box.setIcon(QMessageBox.Icon.Warning)
                warn_box.setWindowTitle("오류"); warn_box.setText(f"이미 '{text}' 이름의 그룹이 해당 위치에 존재합니다.")
                style_qmessagebox(warn_box); warn_box.exec()
            except Exception as e:
                crit_box = QMessageBox(self); crit_box.setIcon(QMessageBox.Icon.Critical)
                crit_box.setWindowTitle("오류"); crit_box.setText(f"그룹 추가 중 오류 발생: {e}")
                style_qmessagebox(crit_box); crit_box.exec()
    
    def _on_subgroup_add_requested(self, parent_group_name, new_group_name):
        """StoryBox에서 받은 하위 그룹 추가 요청을 처리합니다."""
        if not self.current_project_path: return
        try:
            parent_box = self.story_boxes.get(parent_group_name)
            if not parent_box: raise ValueError(f"부모 그룹 '{parent_group_name}'을 찾을 수 없습니다.")
            
            parent_path = Path(parent_box.box_path)
            new_group_path = parent_path / new_group_name
            new_group_path.mkdir(exist_ok=False)

            sub_box = StoryBox(
                title=new_group_name, 
                variable_name=new_group_name, 
                box_path=str(new_group_path),
                level='lower', 
                parent_box=parent_box, 
                is_global=parent_box.is_global
            )
            
            # ▼▼▼▼▼ [수정] 누락된 시그널 연결 추가 ▼▼▼▼▼
            sub_box.expanded.connect(self._on_story_box_expanded)
            sub_box.focused.connect(self._on_story_box_focused)
            sub_box.collapsed.connect(self._on_story_box_collapsed)
            sub_box.delete_requested.connect(self._on_story_box_delete_requested)

            parent_box.add_subgroup(sub_box)
            self.story_boxes[f"{parent_group_name}/{new_group_name}"] = sub_box
            
            info_box = QMessageBox(self); info_box.setIcon(QMessageBox.Icon.Information)
            info_box.setWindowTitle("성공"); info_box.setText(f"하위 그룹 '{new_group_name}'을(를) 추가했습니다.")
            style_qmessagebox(info_box); info_box.exec()

        except FileExistsError:
            warn_box = QMessageBox(self); warn_box.setIcon(QMessageBox.Icon.Warning)
            warn_box.setWindowTitle("오류"); warn_box.setText(f"이미 '{new_group_name}' 이름의 하위 그룹이 존재합니다.")
            style_qmessagebox(warn_box); warn_box.exec()
        except Exception as e:
            crit_box = QMessageBox(self); crit_box.setIcon(QMessageBox.Icon.Critical)
            crit_box.setWindowTitle("오류"); crit_box.setText(f"하위 그룹 추가 중 오류 발생: {e}")
            style_qmessagebox(crit_box); crit_box.exec()

    def _create_right_panel(self) -> QWidget:
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(DARK_STYLES['dark_tabs'])
        workshop_tab = self._create_workshop_ui()
        adventure_tab = AdventureTab(self.app_context, self)
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
        self.item_editor = ItemEditorWidget(self)
        self.item_editor.hide() # 기본적으로 숨김
        self.item_editor.item_saved.connect(self._on_item_saved)
        self.item_editor.item_deleted.connect(self._on_item_deleted)
        self.item_editor.regeneration_requested.connect(self._on_item_regeneration_requested)
        self.item_editor.assign_to_workshop_requested.connect(self._on_assign_to_workshop_requested)
        main_v_layout.addWidget(self.item_editor)
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

        workshop_bench_config = {
            'placeholder_text': "[Testbench] Drag & Drop left widget items to here…",
            'accept_filter': None # 모든 아이템 허용
        }
        self.testbench = TestbenchWidget(storyteller_tab=self, config=workshop_bench_config)
        self.testbench.setMaximumHeight(180)
        bottom_layout.addWidget(self.testbench)
        self.testbench.setMaximumHeight(180) # 아이템 한 줄 + 약간의 여유 높이
        bottom_layout.addWidget(self.testbench)

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
        save_panel_layout = QHBoxLayout(save_panel)
        save_panel_layout.setContentsMargins(0, 0, 0, 0)
        
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
        try:
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if char_module and char_module.activate_checkbox.isChecked():
                char_module.activate_checkbox.setChecked(False)
                print("ℹ️ Workshop 생성: 캐릭터 모듈을 비활성화했습니다.")
                self.app_context.main_window.status_bar.showMessage("캐릭터 모듈이 임시 비활성화되었습니다.", 2000)
        except Exception as e:
            print(f"⚠️ 캐릭터 모듈 비활성화 실패: {e}")
        
        # === Positive Prompt 구성 ===
        prompt_parts = [
            self.prefix_prompt_edit.toPlainText().strip(),
            positive_prompt.strip(),
            self.postfix_prompt_edit.toPlainText().strip()
        ]
        
        # TestBench 아이템들 체크
        testbench_items = self.testbench.get_all_cloned_items()
        character_items = []  # 캐릭터 아이템들
        regular_items = []    # 일반 아이템들
        num_of_boy = 0
        num_of_girl = 0
        num_of_other = 0
        
        if testbench_items:
            print(f"🎯 TestBench에서 {len(testbench_items)}개 아이템 발견")
            
            # 아이템들을 캐릭터/일반으로 분류
            is_naid4 = self._should_use_character_module()
            for item in testbench_items:
                if hasattr(item, 'data') and isinstance(item.data, dict):
                    description = item.data.get('description', {})
                    pp = description.get('positive_prompt', '').strip()
                    identity = pp.split(",")[0] if pp else ""
                    if "boy" in identity.lower():
                        num_of_boy += 1
                    elif "girl" in identity.lower():
                        num_of_girl += 1
                    elif "other" in identity.lower():
                        num_of_other += 1
            
                if is_naid4 and hasattr(item, 'isCharacter') and item.isCharacter:
                    character_items.append(item)
                else:
                    regular_items.append(item)
            
            print(f"  🎭 캐릭터 아이템: {len(character_items)}개")
            print(f"  📝 일반 아이템: {len(regular_items)}개")
            
            # === Character Module 연동 (NAI + NAID4 조건) ===
            if character_items and is_naid4:
                self._update_character_module_with_testbench(character_items)
            
            # === 일반 아이템들의 Positive Prompt 처리 ===
            if regular_items:
                testbench_positive_parts = []
                
                for item in regular_items:
                    if hasattr(item, 'data') and isinstance(item.data, dict):
                        # description 섹션에서 positive_prompt 추출
                        description = item.data.get('description', {})
                        if isinstance(description, dict):
                            if item.isCharacter: item_positive = item.get_enhanced_positive_prompt()
                            else: item_positive = description.get('positive_prompt', '').strip()
                            if item_positive:
                                testbench_positive_parts.append(item_positive)
                                print(f"  📝 {item.variable_name}: {item_positive[:50]}{'...' if len(item_positive) > 50 else ''}")
                
                # 일반 아이템 프롬프트들을 메인 프롬프트 다음에 추가
                if testbench_positive_parts:
                    testbench_combined = ", ".join(testbench_positive_parts)
                    # positive_prompt 다음, postfix_prompt 이전에 삽입
                    prompt_parts.insert(-1, testbench_combined)  # 마지막 요소(postfix) 앞에 삽입
                    print(f"✅ 일반 아이템 프롬프트 추가 완료: {len(testbench_positive_parts)}개")
        
        # 최종 positive prompt 조합
        final_parts = [part for part in prompt_parts if part]
        final_prompt = ", ".join(final_parts)

        # ▼▼▼▼▼ [추가] 인물 태그 재배치 로직 ▼▼▼▼▼
        # 인물 태그 세트 정의
        person_sets = {
            "boys": {"1boy", "2boys", "3boys", "4boys", "5boys", "6+boys"},
            "girls": {"1girl", "2girls", "3girls", "4girls", "5girls", "6+girls"},
            "others": {"1other", "2others", "3others", "4others", "5others", "6+others"}
        }

        # final_prompt를 태그 리스트로 분할 및 정리
        tags = [tag.strip() for tag in final_prompt.split(',') if tag.strip()]
        if num_of_boy > 0:
            _num = num_of_boy
            _tag = f"{_num}boy" if _num == 1 else f"{_num}boys"
            tags.append(_tag)
        if num_of_girl > 0:
            _num = num_of_girl
            _tag = f"{_num}girl" if _num == 1 else f"{_num}girls"
            tags.append(_tag)
        if num_of_other > 0:
            _num = num_of_other
            _tag = f"{_num}other" if _num == 1 else f"{_num}others"
            tags.append(_tag)

        # 인물 태그 수집 및 제거
        found_person_tags = []

        # boys -> girls -> others 순서로 탐색하여 태그 수집
        for category in ["boys", "girls", "others"]:
            person_tag_set = person_sets[category]
            
            # 현재 카테고리의 태그들을 찾아서 제거
            i = 0
            while i < len(tags):
                if tags[i] in person_tag_set:
                    # 발견된 인물 태그를 found_person_tags에 추가하고 원본에서 제거
                    found_person_tags.append(tags.pop(i))
                    print(f"  👥 인물 태그 발견 및 재배치: {found_person_tags[-1]} ({category})")
                else:
                    i += 1

        # ▼▼▼▼▼ [추가] 동일 그룹 내 최대 인원수 태그만 남기기 ▼▼▼▼▼
        if found_person_tags:
            # 각 그룹별로 최대 인원수 태그 찾기
            group_max_tags = {}
            
            for tag in found_person_tags:
                # 태그에서 인원수 추출 함수
                def extract_number(tag):
                    if tag.startswith("6+"):
                        return 6  # 6+는 6으로 처리
                    else:
                        # 숫자 부분만 추출 (1boy -> 1, 2girls -> 2 등)
                        import re
                        match = re.match(r'(\d+)', tag)
                        return int(match.group(1)) if match else 0
                
                # 그룹 분류 및 최대값 업데이트
                for group_name, group_set in person_sets.items():
                    if tag in group_set:
                        current_num = extract_number(tag)
                        if group_name not in group_max_tags or extract_number(group_max_tags[group_name]) < current_num:
                            if group_name in group_max_tags:
                                print(f"  🔄 {group_name} 그룹 태그 교체: {group_max_tags[group_name]} -> {tag}")
                            else:
                                print(f"  ✅ {group_name} 그룹 최대 태그 설정: {tag}")
                            group_max_tags[group_name] = tag
                        else:
                            print(f"  ❌ {group_name} 그룹 중복 태그 제거: {tag} (현재 최대: {group_max_tags[group_name]})")
                        break
            
            # 최종 인물 태그 리스트 생성 (boys -> girls -> others 순서 유지)
            final_person_tags = []
            for group_name in ["boys", "girls", "others"]:
                if group_name in group_max_tags:
                    final_person_tags.append(group_max_tags[group_name])
            
            print(f"  📋 최종 인물 태그: {final_person_tags}")
        else:
            final_person_tags = []

        # 발견된 인물 태그들을 맨 앞에 배치
        if final_person_tags:
            final_tags = final_person_tags + tags
            final_prompt = ", ".join(final_tags)
            print(f"  🎯 최종 프롬프트 (인물 태그 우선 배치): {final_prompt}")
        else:
            print(f"  📝 최종 프롬프트 (인물 태그 없음): {final_prompt}")

        # === Negative Prompt 구성 ===
        negative_parts = [
            self.negative_prompt_edit.toPlainText().strip()
        ]
        
        # TestBench 일반 아이템들에서 negative prompt 추가 (캐릭터는 Character Module에서 처리)
        if regular_items:
            testbench_negative_parts = []
            
            for item in regular_items:
                if hasattr(item, 'data') and isinstance(item.data, dict):
                    # description 섹션에서 negative_prompt 추출
                    description = item.data.get('description', {})
                    if isinstance(description, dict):
                        item_negative = description.get('negative_prompt', '').strip()
                        if item_negative:
                            testbench_negative_parts.append(item_negative)
                            print(f"  🚫 {item.variable_name} negative: {item_negative[:30]}{'...' if len(item_negative) > 30 else ''}")
            
            # TestBench negative 프롬프트들 추가
            if testbench_negative_parts:
                testbench_negative_combined = ", ".join(testbench_negative_parts)
                negative_parts.append(testbench_negative_combined)
                print(f"✅ 일반 아이템 negative 프롬프트 추가 완료: {len(testbench_negative_parts)}개")
        
        # 최종 negative prompt 조합 (Main Window의 negative prompt 포함)
        main_negative = ""
        try:
            main_negative = self.app_context.main_window.negative_prompt_textedit.toPlainText().strip()
        except Exception as e:
            print(f"⚠️ Main Window negative prompt 가져오기 실패: {e}")
        
        # Main Window negative + Workshop negative + TestBench negative 순서로 조합
        all_negative_parts = []
        if main_negative:
            all_negative_parts.append(main_negative)
        
        final_negative_parts = [part for part in negative_parts if part]
        if final_negative_parts:
            all_negative_parts.extend(final_negative_parts)
        
        final_negative = ", ".join(all_negative_parts) if all_negative_parts else ""
        
        # 생성 파라미터 설정
        override_params = {
            "input": final_prompt,
            "negative_prompt": final_negative,
            "width": 1024,
            "height": 1024,
            "random_resolution": False
        }
        
        # 디버깅 로그
        print(f"🎨 최종 Positive Prompt: {final_prompt[:100]}{'...' if len(final_prompt) > 100 else ''}")
        print(f"🚫 최종 Negative Prompt: {final_negative[:100]}{'...' if len(final_negative) > 100 else ''}")
        
        # 생성 파이프라인 실행
        auto_generate_checkbox = self.app_context.main_window.generation_checkboxes.get("자동 생성")
        if auto_generate_checkbox.isChecked(): auto_generate_checkbox.setChecked(False)  # 자동 생성 해제
        self.app_context.subscribe("generation_completed_for_redirect", self._on_workshop_image_generated)
        gen_controller = self.app_context.main_window.generation_controller
        gen_controller.execute_generation_pipeline(overrides=override_params)

    def _should_use_character_module(self) -> bool:
        """Character Module 사용 조건 체크"""
        try:
            # NAI 모드 체크
            if self.app_context.current_api_mode != 'NAI':
                return False
            
            # NAID4 모델 체크
            model_text = self.app_context.main_window.model_combo.currentText()
            if 'NAID4' not in model_text:
                return False
            
            # Character Module 존재 체크
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if not char_module:
                return False
            
            print("✅ Character Module 사용 조건 충족: NAI + NAID4")
            return True
            
        except Exception as e:
            print(f"⚠️ Character Module 조건 체크 실패: {e}")
            return False

    def _should_use_character_module(self) -> bool:
        """Character Module 사용 조건 체크"""
        try:
            # NAI 모드 체크
            if self.app_context.current_api_mode != 'NAI':
                return False
            
            # NAID4 모델 체크
            model_text = self.app_context.main_window.model_combo.currentText()
            if 'NAID4' not in model_text:
                return False
            
            # Character Module 존재 체크
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if not char_module:
                return False
            
            print("✅ Character Module 사용 조건 충족: NAI + NAID4")
            return True
            
        except Exception as e:
            print(f"⚠️ Character Module 조건 체크 실패: {e}")
            return False

    def _update_character_module_with_testbench(self, character_items):
        """TestBench 캐릭터 아이템들을 Character Module에 업데이트"""
        try:
            char_module = self.app_context.middle_section_controller.get_module_instance("CharacterModule")
            if not char_module:
                return
            
            characters = []
            ucs = []
            
            for item in character_items:
                if hasattr(item, 'data') and isinstance(item.data, dict):
                    # 향상된 positive_prompt 추출 (appendix 포함)
                    if hasattr(item, 'get_enhanced_positive_prompt'):
                        positive = item.get_enhanced_positive_prompt()
                    else:
                        # fallback: 기본 description에서 positive_prompt 추출
                        description = item.data.get('description', {})
                        positive = description.get('positive_prompt', '').strip() if isinstance(description, dict) else ''
                    
                    # negative_prompt는 기본 방식 유지 (appendix 적용 안 함)
                    description = item.data.get('description', {})
                    negative = description.get('negative_prompt', '').strip() if isinstance(description, dict) else ''
                    
                    if positive:
                        characters.append(positive)
                        ucs.append(negative)  # negative가 없어도 빈 문자열로 추가
                        print(f"  🎭 캐릭터 추가: {item.variable_name} -> {positive[:40]}{'...' if len(positive) > 40 else ''}")
            
            # Character Module의 modifiable_clone 업데이트
            if characters:
                char_module.modifiable_clone = {
                    'characters': characters,
                    'uc': ucs
                }
                
                # Character Module 활성화
                if hasattr(char_module, 'activate_checkbox'):
                    char_module.activate_checkbox.setChecked(True)
                
                # UI 업데이트
                if hasattr(char_module, 'update_processed_display'):
                    char_module.update_processed_display(characters, ucs)
                
                print(f"✅ Character Module 업데이트 완료: {len(characters)}개 캐릭터")
                self.app_context.main_window.status_bar.showMessage(f"🎭 {len(characters)}개 캐릭터를 Character Module에 적용했습니다.", 3000)
            
        except Exception as e:
            print(f"❌ Character Module 업데이트 실패: {e}")
            import traceback
            traceback.print_exc()

    def _on_workshop_image_generated(self, result: dict):
        self.app_context.subscribers["generation_completed_for_redirect"].remove(self._on_workshop_image_generated)
        image_object = result
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
            # if self.expanded_upper_box and self.expanded_upper_box is not expanded_box:
            #     self.expanded_upper_box.collapse()
            
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
            # if self.expanded_upper_box and self.expanded_upper_box is not expanded_box.parent_box:
            #     self.expanded_upper_box.collapse()
            
            # 현재 상위 그룹을 이 하위 그룹의 부모로 설정한다.
            self.expanded_upper_box = expanded_box.parent_box

    def _on_story_box_focused(self, focused_box: StoryBox):
        """하나의 박스가 포커스되면 다른 박스의 포커스를 해제합니다."""
        # ▼▼▼▼▼ [신규] 디버깅을 위한 로깅 추가 ▼▼▼▼▼
        # print(f"DEBUG: 포커스 요청 - {focused_box.level} 레벨, {focused_box.variable_name}")
        # if self.active_story_box:
           #  print(f"DEBUG: 현재 활성화된 박스 - {self.active_story_box.level} 레벨, {self.active_story_box.variable_name}")
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        
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
        """'저장' 버튼 클릭 시 아이템을 생성 또는 업데이트하고 저장하는 전체 로직."""
        self.save_settings()

        # 1. 입력값 유효성 검사
        if not self.active_story_box or self.active_story_box.level == 'upper':
            warn_box = QMessageBox(self); warn_box.setIcon(QMessageBox.Icon.Warning); warn_box.setWindowTitle("오류"); warn_box.setText("아이템을 저장할 하위 그룹을 먼저 선택(클릭)해주세요.")
            style_qmessagebox(warn_box); warn_box.exec()
            return
        
        variable_name = self.variable_name_input.text()
        if not variable_name:
            warn_box = QMessageBox(self); warn_box.setIcon(QMessageBox.Icon.Warning); warn_box.setWindowTitle("오류"); warn_box.setText("저장할 아이템의 변수명을 입력해주세요.")
            style_qmessagebox(warn_box); warn_box.exec()
            return

        source_pixmap = self.right_output_panel._pixmap
        if not source_pixmap or source_pixmap.isNull():
            warn_box = QMessageBox(self); warn_box.setIcon(QMessageBox.Icon.Warning); warn_box.setWindowTitle("오류"); warn_box.setText("저장할 이미지가 없습니다. 먼저 이미지를 생성해주세요.")
            style_qmessagebox(warn_box); warn_box.exec()
            return

        # 2. 이미지 처리 (공통 로직)
        try:
            pil_image = Image.fromqpixmap(source_pixmap)
            
            # 안전한 PNG 변환을 위한 처리
            if pil_image.mode != 'RGBA':
                # RGBA 모드로 변환
                pil_image = pil_image.convert('RGBA')
            
            # 메모리 상에서 PNG로 변환하여 안정성 확보
            from io import BytesIO
            png_buffer = BytesIO()
            pil_image.save(png_buffer, format='PNG')
            png_buffer.seek(0)
            
            # PNG 데이터로부터 새로운 PIL 이미지 생성
            pil_image = Image.open(png_buffer)
            
            # 기존 크롭 및 썸네일 로직
            w, h = pil_image.size
            crop_w, crop_h = int(w * 0.75), int(h * 0.75)
            left, top = (w - crop_w) // 2, (h - crop_h) // 2
            right, bottom = left + crop_w, top + crop_h
            cropped_image = pil_image.crop((left, top, right, bottom))
            cropped_image.thumbnail((128, 128), Image.Resampling.LANCZOS)
            
            thumbnail_pixmap = QPixmap.fromImage(ImageQt(cropped_image))
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"이미지 처리 중 오류가 발생했습니다: {e}")
            return
        
        # 3. 중복 변수명 확인 및 분기 처리
        group_box = self.active_story_box
        existing_item_widget = group_box.items.get(variable_name)

        if existing_item_widget:
            # --- 중복된 경우: 기존 아이템 업데이트 ---
            text = f"'{variable_name}' 아이템이 이미 존재합니다."
            warning_text = "기존 아이템의 썸네일과 프롬프트 정보를 덮어쓰시겠습니까?"
            
            if ConfirmationDialog.ask(self, "덮어쓰기 확인", text, warning_text):
                # ▼▼▼▼▼ [수정] 업데이트 시에도 새로운 데이터 구조 적용 ▼▼▼▼▼
                existing_item_widget.thumbnail_label.setPixmap(thumbnail_pixmap)
                # 기존 appendix 정보는 유지하면서 description과 workshop만 업데이트
                existing_item_widget.data["description"] = {
                    "positive_prompt": self.positive_prompt_edit.toPlainText(),
                    "negative_prompt": self.negative_prompt_edit.toPlainText()
                }
                existing_item_widget.data["workshop"] = {
                    "prefix_prompt": self.prefix_prompt_edit.toPlainText(),
                    "postfix_prompt": self.postfix_prompt_edit.toPlainText()
                }
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                existing_item_widget.save_data()
                self.app_context.main_window.status_bar.showMessage(f"✅ 아이템 '{variable_name}' 업데이트 완료!", 3000)
            else:
                self.app_context.main_window.status_bar.showMessage("ℹ️ 아이템 업데이트가 취소되었습니다.", 3000)

        else:
            # --- 중복이 아닌 경우: 새 아이템 생성 ---
            parent_box = group_box.parent_box
            group_path = (self.global_dir if parent_box.is_global else self.current_project_path) / parent_box.variable_name / group_box.variable_name
            
            item_widget = StoryItemWidget(group_path=str(group_path), variable_name=variable_name, parent_box=group_box)
            item_widget.edit_requested.connect(self._on_item_edit_requested)
            item_widget.thumbnail_label.setPixmap(thumbnail_pixmap)

            # ▼▼▼▼▼ [수정] 새 아이템 생성 시 새로운 데이터 구조 적용 ▼▼▼▼▼
            item_widget.data = {
                "description": {
                    "positive_prompt": self.positive_prompt_edit.toPlainText(),
                    "negative_prompt": self.negative_prompt_edit.toPlainText()
                },
                "appendix": {
                    "explain": "이 item에 대한 description을 작성해주세요."
                },
                "workshop": {
                    "prefix_prompt": self.prefix_prompt_edit.toPlainText(),
                    "postfix_prompt": self.postfix_prompt_edit.toPlainText()
                }
            }
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

            item_widget.save_data()
            group_box.add_item(item_widget)
            self.app_context.main_window.status_bar.showMessage(f"✅ 새 아이템 '{variable_name}' 저장 완료!", 3000)

        self.variable_name_input.clear()

    def _on_item_edit_requested(self, item_widget: StoryItemWidget):
        """아이템 위젯에서 편집 요청이 오면 에디터를 엽니다."""
        self.item_editor.open_for_item(item_widget)

    def _on_item_saved(self, item_widget: StoryItemWidget, new_data: dict):
        """에디터에서 저장 요청이 오면 데이터를 업데이트하고 파일을 저장합니다."""
        item_widget.data = new_data
        item_widget.save_data()
        item_widget.load_data() # 썸네일 등 UI 새로고침
        self.app_context.main_window.status_bar.showMessage(f"✅ '{item_widget.variable_name}' 아이템이 수정되었습니다.", 3000)

    def _on_item_deleted(self, item_widget: StoryItemWidget):
        """에디터에서 삭제 요청이 오면 파일과 위젯을 제거합니다."""
        try:
            # 1. 파일 삭제
            if item_widget.json_path.exists():
                item_widget.json_path.unlink()
            
            # 2. UI에서 위젯 제거
            parent_box = item_widget.parent_box
            if parent_box:
                parent_box.remove_item(item_widget.variable_name)
            else:
                # 부모가 없는 경우를 대비한 안전장치
                item_widget.deleteLater()

            self.app_context.main_window.status_bar.showMessage(f"✅ '{item_widget.variable_name}' 아이템이 삭제되었습니다.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"아이템 삭제 중 오류 발생: {e}")

    def _on_item_regeneration_requested(self, item_widget: StoryItemWidget, override_params: dict):
        """에디터에서 재생성 요청이 오면, 이미지 생성 후 썸네일을 업데이트합니다."""
        self.app_context.main_window.status_bar.showMessage(f"🔄 '{item_widget.variable_name}' 이미지 재생성 중...")
        
        # 결과를 에디터로 리디렉션하기 위한 임시 핸들러
        def on_regeneration_finished(result: dict):
            self.app_context.subscribers["generation_completed_for_redirect"].remove(on_regeneration_finished)
            image_object = result.get("image")
            if image_object:
                # 썸네일 생성 및 업데이트 로직 (on_save_item_clicked 참조)
                # ...
                # self.item_editor.update_thumbnail(new_pixmap)
                # self.item_editor.current_item_widget.data['thumbnail_base64'] = ...
                print("TODO: 썸네일 업데이트 로직 구현")

        self.app_context.subscribe("generation_completed_for_redirect", on_regeneration_finished)
        gen_controller = self.app_context.main_window.generation_controller
        gen_controller.execute_generation_pipeline(overrides=override_params)

    def _on_assign_to_workshop_requested(self, prompt_data: dict):
        """에디터의 프롬프트 데이터를 Workshop의 입력창들로 복사합니다."""
        self.prefix_prompt_edit.setText(prompt_data.get("prefix", ""))
        self.positive_prompt_edit.setText(prompt_data.get("positive", ""))
        self.postfix_prompt_edit.setText(prompt_data.get("postfix", ""))
        self.negative_prompt_edit.setText(prompt_data.get("negative", ""))
        
        self.app_context.main_window.status_bar.showMessage("✅ 프롬프트 정보가 Workshop에 할당되었습니다.", 3000)

    def _on_story_box_delete_requested(self, box_to_delete: StoryBox):
        """StoryBox 삭제 요청을 받아 확인 후 폴더와 위젯을 삭제합니다."""
        title = box_to_delete.title
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("그룹 삭제 확인")
        msg_box.setText(f"'{title}' 그룹을 정말로 삭제하시겠습니까?")
        msg_box.setInformativeText("이 작업은 되돌릴 수 없으며, 모든 하위 그룹과 아이템이 영구적으로 삭제됩니다.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        style_qmessagebox(msg_box)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            if self.active_story_box is box_to_delete:
                self.active_story_box = None
            if self.expanded_upper_box is box_to_delete:
                self.expanded_upper_box = None
            if self.expanded_lower_box is box_to_delete:
                self.expanded_lower_box = None
            try:
                # 1. 파일 시스템에서 폴더 재귀적으로 삭제
                path_to_delete = Path(box_to_delete.box_path)
                if path_to_delete.exists():
                    shutil.rmtree(path_to_delete)
                    print(f"🗑️ 폴더 삭제 완료: {path_to_delete}")

                # 2. self.story_boxes 딕셔너리에서 해당 박스와 모든 자식 박스들 제거
                keys_to_delete = []
                for key, box in self.story_boxes.items():
                    if box is box_to_delete or (hasattr(box, 'parent_box') and box.parent_box is box_to_delete):
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del self.story_boxes[key]
                print(f"🗑️ 추적 목록에서 '{title}' 및 하위 그룹 제거 완료.")

                # 3. UI에서 위젯 제거
                box_to_delete.deleteLater()
                
                self.app_context.main_window.status_bar.showMessage(f"✅ '{title}' 그룹이 삭제되었습니다.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"그룹 삭제 중 오류 발생: {e}")