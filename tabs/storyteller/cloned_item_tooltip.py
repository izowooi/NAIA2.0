from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QCheckBox, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont
from ui.theme import DARK_STYLES, DARK_COLORS

class ClonedItemTooltip(QDialog):
    """ClonedStoryItem 더블클릭 시 표시되는 툴팁 다이얼로그"""
    
    def __init__(self, item_data, variable_name, mouse_pos, is_character=False, cloned_item_ref=None, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.variable_name = variable_name
        self.mouse_pos = mouse_pos
        self.is_character = is_character
        self.cloned_item_ref = cloned_item_ref
        self.checkbox_widgets = {}
        
        # 포커스 아웃 감지를 위한 설정
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.init_ui()
        self.position_tooltip()
        
        # 포커스 설정
        self.setFocus()
    
    def init_ui(self):
        """UI 초기화"""
        # 다이얼로그 설정
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)  # 닫힐 때 자동 삭제
        self.setModal(False)  # 모달리스 다이얼로그
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 메인 프레임 (테두리와 배경색을 위해)
        main_frame = QFrame()
        main_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DARK_COLORS['bg_primary']};
                border: 2px solid #333333;
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(main_frame)
        
        # 프레임 내부 레이아웃
        frame_layout = QVBoxLayout(main_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(8)
        
        # === 상단: 제목 + 닫기 버튼 ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel(f"{self.variable_name} - Quick View")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 0px;
            }}
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        close_button = QPushButton("✕")
        close_button.setFixedSize(24, 24)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:pressed {
                background-color: #cc3333;
            }
        """)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)
        
        frame_layout.addLayout(header_layout)
        
        # === 메인 콘텐츠 영역 ===
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        
        # === 왼쪽 패널: Positive/Negative 프롬프트 ===
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel)
        
        # === 오른쪽 패널: Explain + Additional Properties ===
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel)
        
        frame_layout.addLayout(content_layout)
        
        # 다이얼로그 크기 설정
        self.setFixedSize(600, 400)
    
    def create_left_panel(self) -> QWidget:
        """왼쪽 패널 생성 (Positive/Negative 프롬프트)"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Positive Prompt
        pos_label = QLabel("Positive Prompt:")
        pos_label.setStyleSheet(DARK_STYLES['label_style'])
        left_layout.addWidget(pos_label)
        
        pos_text = QTextEdit()
        pos_text.setReadOnly(True)
        pos_text.setStyleSheet(DARK_STYLES['compact_textedit'])
        pos_text.setFixedHeight(120)
        
        # 데이터에서 positive_prompt 추출
        description = self.item_data.get('description', {})
        positive_prompt = description.get('positive_prompt', '데이터 없음')
        pos_text.setText(positive_prompt)
        left_layout.addWidget(pos_text)
        
        # Negative Prompt
        neg_label = QLabel("Negative Prompt:")
        neg_label.setStyleSheet(DARK_STYLES['label_style'])
        left_layout.addWidget(neg_label)
        
        neg_text = QTextEdit()
        neg_text.setReadOnly(True)
        neg_text.setStyleSheet(DARK_STYLES['compact_textedit'])
        neg_text.setFixedHeight(120)
        
        # 데이터에서 negative_prompt 추출
        negative_prompt = description.get('negative_prompt', '')
        neg_text.setText(negative_prompt)
        left_layout.addWidget(neg_text)
        
        left_widget.setFixedWidth(280)
        return left_widget
    
    def create_right_panel(self) -> QWidget:
        """오른쪽 패널 생성 (Explain + Additional Properties)"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # === Explain 섹션 ===
        explain_label = QLabel("Explain:")
        explain_label.setStyleSheet(DARK_STYLES['label_style'])
        right_layout.addWidget(explain_label)
        
        explain_text = QTextEdit()
        explain_text.setReadOnly(True)
        explain_text.setStyleSheet(DARK_STYLES['compact_textedit'])
        explain_text.setFixedHeight(80)
        
        # 데이터에서 explain 추출
        appendix = self.item_data.get('appendix', {})
        explain_content = appendix.get('explain', '설명 없음')
        explain_text.setText(explain_content)
        right_layout.addWidget(explain_text)
        
        # === Additional Properties 섹션 ===
        props_label = QLabel("Additional Properties:")
        props_label.setStyleSheet(DARK_STYLES['label_style'])
        right_layout.addWidget(props_label)
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid #444;
                border-radius: 4px;
                background-color: {DARK_COLORS['bg_secondary']};
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #666666;
            }}
        """)
        
        # 스크롤 가능한 위젯 생성
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: none;
            }}
        """)
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(6)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Additional Properties 위젯들 생성
        self.create_additional_properties(scroll_layout, appendix)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setFixedHeight(220)  # 스크롤 영역 높이 제한
        right_layout.addWidget(scroll_area)
        
        right_widget.setFixedWidth(280)
        return right_widget
    
    def create_additional_properties(self, layout, appendix_data):
        """Additional Properties 위젯들 동적 생성"""
        if not appendix_data:
            no_data_label = QLabel("추가 속성 없음")
            no_data_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; padding: 10px;")
            layout.addWidget(no_data_label)
            return
        
        # explain 제외한 모든 appendix 항목들 처리
        for key, value in appendix_data.items():
            if key == 'explain':
                continue
            
            # ▼▼▼▼▼ [수정] ClonedStoryItem의 상태를 반영한 체크박스 생성 ▼▼▼▼▼
            checkbox = QCheckBox(key)
            
            # ClonedStoryItem에서 현재 상태 가져오기
            if self.cloned_item_ref:
                current_state = self.cloned_item_ref.get_appendix_enabled(key)
                checkbox.setChecked(current_state)
            else:
                checkbox.setChecked(False)  # 기본값
            
            checkbox.setStyleSheet(DARK_STYLES['dark_checkbox'])
            
            # ▼▼▼▼▼ [추가] 체크박스 상태 변경 시 즉시 ClonedStoryItem에 반영 ▼▼▼▼▼
            checkbox.stateChanged.connect(lambda state, k=key: self._on_checkbox_changed(k, state == 2))
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            
            # 체크박스 추적을 위해 저장
            self.checkbox_widgets[key] = checkbox
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            
            layout.addWidget(checkbox)
            
            # 값 텍스트박스 생성
            value_text = QTextEdit()
            value_text.setReadOnly(True)
            value_text.setStyleSheet(DARK_STYLES['dark_text_edit'])
            value_text.setFixedHeight(60)
            value_text.setText(str(value))
            layout.addWidget(value_text)
    
    def position_tooltip(self):
        """마우스 위치를 기준으로 툴팁 위치 설정"""
        if not self.mouse_pos:
            return
        
        # 화면 크기 정보
        screen = self.screen()
        if screen:
            screen_geometry = screen.availableGeometry()
            
            # 기본 위치: 마우스 오른쪽 아래
            x = self.mouse_pos.x() + 10
            y = self.mouse_pos.y() + 10
            
            # 화면 경계 체크 및 조정
            tooltip_width = self.width()
            tooltip_height = self.height()
            
            # 오른쪽 경계 체크
            if x + tooltip_width > screen_geometry.right():
                x = self.mouse_pos.x() - tooltip_width - 10
            
            # 아래쪽 경계 체크
            if y + tooltip_height > screen_geometry.bottom():
                y = self.mouse_pos.y() - tooltip_height - 10
            
            # 최종 위치 설정
            self.move(x, y)
    
    def keyPressEvent(self, event):
        """ESC 키로 닫기"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def _on_checkbox_changed(self, key: str, checked: bool):
        """체크박스 상태 변경 시 ClonedStoryItem에 즉시 반영"""
        if self.cloned_item_ref:
            self.cloned_item_ref.set_appendix_enabled(key, checked)
            status = "활성화" if checked else "비활성화"
            print(f"  🔄 툴팁에서 {self.variable_name}의 {key} {status}")

    def closeEvent(self, event):
        """툴팁이 닫힐 때 최종 상태를 ClonedStoryItem에 저장"""
        if self.cloned_item_ref:
            # 모든 체크박스 상태를 수집하여 일괄 업데이트
            final_states = {}
            for key, checkbox in self.checkbox_widgets.items():
                final_states[key] = checkbox.isChecked()
            
            self.cloned_item_ref.update_appendix_states(final_states)
            print(f"  📋 툴팁 종료: {self.variable_name} appendix 상태 최종 저장")
        
        super().closeEvent(event)