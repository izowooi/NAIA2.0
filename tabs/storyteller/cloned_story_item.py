import json
import uuid
import copy
from PyQt6.QtGui import QMouseEvent, QDrag, QPixmap, QPainter, QAction
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QRect
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QMenu

class ClonedStoryItem(QWidget):
    """
    Testbench 전용 복제된 아이템 위젯 - 캐릭터 감지 기능 추가
    """
    remove_requested = pyqtSignal(object)  # 제거 요청 시그널
    swap_requested = pyqtSignal(object, str)
    
    def __init__(self, original_widget, origin_tag: str, parent_bench=None, parent=None):
        super().__init__(parent)
        
        # 고유 식별자
        self.instance_id = str(uuid.uuid4())
        self.variable_name = original_widget.variable_name
        self.origin_tag = origin_tag
        self.parent_bench = parent_bench
        
        # 원본 데이터 깊은 복사
        self.data = copy.deepcopy(original_widget.data)
        self.appendix_enabled = {}  # appendix 항목별 활성화 상태
        self._initialize_appendix_states()
        
        # 캐릭터 감지 플래그
        self.isCharacter = False
        
        # 툴팁 중복 생성 방지를 위한 참조
        self.current_tooltip = None
        
        # 원본 썸네일 복사
        self.original_pixmap = None
        if original_widget.thumbnail_label.pixmap():
            self.original_pixmap = QPixmap(original_widget.thumbnail_label.pixmap())
        
        # 캐릭터 감지 및 플래그 설정
        self._detect_character_type()
        
        # 위젯 초기화
        self.init_ui()
        self.setup_style()
        
        print(f"ClonedStoryItem created: {self.instance_id[:8]}... (Character: {self.isCharacter})")

    def _detect_character_type(self):
        """데이터에서 캐릭터 타입 감지"""
        try:
            description = self.data.get('description', {})
            if isinstance(description, dict):
                positive_prompt = description.get('positive_prompt', '').strip()
                if positive_prompt:
                    # 첫 번째 태그 추출 (콤마로 분리)
                    first_tag = positive_prompt.split(',')[0].strip().lower()
                    
                    # 캐릭터 관련 키워드 체크
                    character_keywords = ['girl', 'boy', 'other']
                    for keyword in character_keywords:
                        if keyword in first_tag:
                            self.isCharacter = True
                            print(f"  🎭 Character detected: '{first_tag}' contains '{keyword}'")
                            break
        except Exception as e:
            print(f"  ⚠️ Character detection error: {e}")
            self.isCharacter = False

    def init_ui(self):
        """UI 구성 요소 초기화"""
        # 위젯 고정 크기 설정
        self.setFixedSize(128, 164)
        
        # 썸네일 라벨 생성 (중앙 상단에 배치)
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setFixedSize(112, 112)
        self.thumbnail_label.setGeometry(8, 8, 112, 112)  # 중앙 정렬: (128-112)/2 = 8
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 캐릭터 여부에 따른 썸네일 스타일링
        if self.isCharacter:
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    background-color: #1a1a1a;
                    border: 2px solid #FFD700;
                    border-radius: 4px;
                }
            """)
        else:
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    background-color: #1a1a1a;
                    border: 1px solid #444;
                    border-radius: 4px;
                }
            """)
        
        # 썸네일 이미지 설정
        if self.original_pixmap and not self.original_pixmap.isNull():
            # 112x112에 맞춰 스케일링
            scaled_pixmap = self.original_pixmap.scaled(
                112, 112,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            self.thumbnail_label.setText("No Image")
            self.thumbnail_label.setStyleSheet(self.thumbnail_label.styleSheet() + """
                color: #666;
                font-size: 10px;
            """)
        
        self.name_label = QLabel(self.variable_name, self)
        self.name_label.setFixedSize(112, 28)
        self.name_label.setGeometry(8, 110, 112, 28)  # 4px 위로 올림 (124→120)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 캐릭터 여부에 따른 이름 라벨 스타일링
        if self.isCharacter:
            self.name_label.setStyleSheet("""
                QLabel {
                    color: #FFD700;
                    font-size: 16px;
                    font-weight: 600;
                    background-color: transparent;
                    border: none;
                    padding: 2px;
                }
            """)
        else:
            self.name_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 16px;
                    font-weight: 500;
                    background-color: transparent;
                    border: none;
                    padding: 2px;
                }
            """)
        
        # 제거 버튼 생성 (오른쪽 위 모서리)
        self.remove_button = QPushButton("×", self)
        self.remove_button.setFixedSize(18, 18)
        self.remove_button.setGeometry(106, 2, 18, 18)  # 오른쪽 위 모서리
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 9px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:pressed {
                background-color: #cc3333;
            }
        """)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        
        # 모든 요소를 최상위로 올리기
        self.thumbnail_label.raise_()
        self.name_label.raise_()
        self.remove_button.raise_()

    def setup_style(self):
        """위젯 전체 스타일 설정 - 캐릭터 여부에 따른 테두리 색상"""
        if self.isCharacter:
            # 캐릭터: 노란색 테두리
            self.setStyleSheet("""
                ClonedStoryItem {
                    background-color: #2d2d2d;
                    border: 2px solid #FFD700;
                    border-radius: 6px;
                }
                ClonedStoryItem:hover {
                    border: 2px solid #FFED4E;
                    background-color: #353535;
                }
            """)
        else:
            # 일반 아이템: 연회색 테두리
            self.setStyleSheet("""
                ClonedStoryItem {
                    background-color: #2d2d2d;
                    border: 2px solid #888888;
                    border-radius: 6px;
                }
                ClonedStoryItem:hover {
                    border: 2px solid #aaaaaa;
                    background-color: #353535;
                }
            """)

    def _on_remove_clicked(self):
        """제거 버튼 클릭 처리"""
        print(f"Remove requested for: {self.variable_name} ({self.instance_id[:8]}) - Character: {self.isCharacter}")
        self.remove_requested.emit(self)

    def mousePressEvent(self, event: QMouseEvent):
        """마우스 클릭 이벤트 - 드래그 준비"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            # 드래그 거리 확인 (최소 거리 이상 움직였을 때만 드래그 시작)
            if hasattr(self, 'drag_start_position'):
                distance = (event.pos() - self.drag_start_position).manhattanLength()
                if distance < 10:  # 최소 드래그 거리
                    return

            drag = QDrag(self)
            mime_data = QMimeData()
            
            # ▼▼▼▼▼ [수정] 드래그 데이터에 전체 데이터(self.data) 포함 ▼▼▼▼▼
            drag_data = {
                "source": "ClonedStoryItem",
                "instance_id": self.instance_id,
                "variable_name": self.variable_name,
                "isCharacter": self.isCharacter,
                "origin_tag": self.origin_tag,
                "full_data": self.data # 필요한 모든 데이터를 여기에 담음
            }
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            mime_data.setText(json.dumps(drag_data))
            drag.setMimeData(mime_data)
            
            drag_pixmap = self.create_drag_pixmap()
            drag.setPixmap(drag_pixmap)
            drag.setHotSpot(event.pos())
            
            drag.exec(Qt.DropAction.MoveAction)

    def start_drag(self, event: QMouseEvent):
        """드래그 앤 드롭 시작"""
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 드래그 데이터 설정 (캐릭터 플래그 포함)
        drag_data = {
            "source": "ClonedStoryItem",
            "instance_id": self.instance_id,
            "variable_name": self.variable_name,
            "isCharacter": self.isCharacter,
            "origin_tag": self.origin_tag 
        }
        mime_data.setText(json.dumps(drag_data))
        drag.setMimeData(mime_data)
        
        # 드래그 시각적 효과용 픽스맵 생성
        drag_pixmap = self.create_drag_pixmap()
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(event.pos())
        
        # 드래그 실행
        drop_action = drag.exec(Qt.DropAction.MoveAction)
        
        print(f"Drag completed for {self.variable_name}: {drop_action}")

    def create_drag_pixmap(self) -> QPixmap:
        """드래그 시 사용할 반투명 픽스맵 생성"""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # 위젯을 픽스맵에 그리기
        painter = QPainter(pixmap)
        painter.setOpacity(0.8)  # 반투명 효과
        self.render(painter)
        painter.end()
        
        return pixmap

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """더블클릭 이벤트 - 툴팁 다이얼로그 표시 (중복 방지)"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 이미 툴팁이 열려있으면 닫고 새로 열지 않음
            if self.current_tooltip and not self.current_tooltip.isHidden():
                return
            
            # 글로벌 마우스 좌표 계산
            global_pos = self.mapToGlobal(event.pos())
            
            # 툴팁 다이얼로그 생성 및 표시
            from .cloned_item_tooltip import ClonedItemTooltip
            
            self.current_tooltip = ClonedItemTooltip(
                item_data=self.data,
                variable_name=self.variable_name,
                mouse_pos=global_pos,
                is_character=self.isCharacter,
                cloned_item_ref=self,  # ▼▼▼ [추가] 자기 자신 참조 전달 ▼▼▼
                parent=None
            )
            
            # 툴팁이 닫힐 때 참조 제거
            self.current_tooltip.finished.connect(lambda: setattr(self, 'current_tooltip', None))
            
            char_status = "캐릭터" if self.isCharacter else "일반 아이템"
            print(f"Double-click on cloned item: {self.variable_name} ({char_status}) - 툴팁 표시")
            
            self.current_tooltip.show()
            
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        """마우스 진입 시 시각적 피드백"""
        if self.isCharacter:
            # 캐릭터: 밝은 노란색
            self.setStyleSheet("""
                ClonedStoryItem {
                    background-color: #353535;
                    border: 2px solid #FFED4E;
                    border-radius: 6px;
                }
            """)
        else:
            # 일반: 밝은 회색
            self.setStyleSheet("""
                ClonedStoryItem {
                    background-color: #353535;
                    border: 2px solid #aaaaaa;
                    border-radius: 6px;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """마우스 떠남 시 원래 스타일 복원"""
        self.setup_style()  # 원래 스타일로 복원
        super().leaveEvent(event)

    def _initialize_appendix_states(self):
        """appendix 항목들의 초기 활성화 상태 설정"""
        appendix = self.data.get('appendix', {})
        if isinstance(appendix, dict):
            for key, value in appendix.items():
                if key == 'explain':
                    continue  # explain은 항상 비활성화
                # 기본적으로 모든 appendix 항목을 비활성화로 시작
                self.appendix_enabled[key] = False
                print(f"  📋 {self.variable_name} appendix 초기화: {key} -> False")

    def set_appendix_enabled(self, key: str, enabled: bool):
        """특정 appendix 항목의 활성화 상태 설정"""
        if key != 'explain':  # explain은 제외
            self.appendix_enabled[key] = enabled
            print(f"  🔄 {self.variable_name} appendix 상태 변경: {key} -> {enabled}")

    def get_appendix_enabled(self, key: str) -> bool:
        """특정 appendix 항목의 활성화 상태 반환"""
        if key == 'explain':
            return False  # explain은 항상 비활성화
        return self.appendix_enabled.get(key, False)

    def get_all_appendix_states(self) -> dict:
        """모든 appendix 항목의 활성화 상태 반환"""
        return self.appendix_enabled.copy()

    def update_appendix_states(self, states: dict):
        """툴팁에서 받은 상태로 일괄 업데이트"""
        for key, enabled in states.items():
            if key != 'explain':
                self.appendix_enabled[key] = enabled
        print(f"  📋 {self.variable_name} appendix 상태 일괄 업데이트: {len(states)}개 항목")

    def get_enhanced_positive_prompt(self) -> str:
        """positive_prompt + 활성화된 appendix 항목들을 조합하여 반환"""
        try:
            # 기본 positive_prompt 추출
            description = self.data.get('description', {})
            base_positive = description.get('positive_prompt', '').strip()
            
            if not base_positive:
                return ""
            
            # appendix에서 활성화된 항목들 수집
            appendix = self.data.get('appendix', {})
            if not isinstance(appendix, dict):
                return base_positive
            
            enhanced_parts = [base_positive]
            
            # ▼▼▼▼▼ [수정] TODO 해결: 실제 체크박스 상태 반영 ▼▼▼▼▼
            for key, value in appendix.items():
                if key == 'explain':
                    continue
                
                # 실제 활성화 상태 확인
                is_enabled = self.get_appendix_enabled(key)
                
                if is_enabled and value and str(value).strip():
                    enhanced_parts.append(str(value).strip())
                    print(f"  🔗 {self.variable_name} appendix 추가: {key} -> {str(value)[:30]}{'...' if len(str(value)) > 30 else ''}")
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            
            # 최종 조합
            final_prompt = ", ".join(enhanced_parts)
            
            if len(enhanced_parts) > 1:
                print(f"  ✨ {self.variable_name} 향상된 프롬프트: {final_prompt[:60]}{'...' if len(final_prompt) > 60 else ''}")
            
            return final_prompt
            
        except Exception as e:
            print(f"⚠️ {self.variable_name} positive_prompt 처리 오류: {e}")
            # 오류 발생 시 기본 positive_prompt만 반환
            description = self.data.get('description', {})
            return description.get('positive_prompt', '')

    def get_display_info(self) -> dict:
        """디버깅용 정보 반환"""
        return {
            "instance_id": self.instance_id[:8],
            "variable_name": self.variable_name,
            "isCharacter": self.isCharacter,
            "size": f"{self.width()}x{self.height()}",
            "position": f"({self.x()}, {self.y()})",
            "has_pixmap": self.original_pixmap is not None and not self.original_pixmap.isNull()
        }
    
    def get_data(self) -> dict:
        """자신의 데이터를 저장 가능한 딕셔너리 형태로 반환합니다."""
        return {
            "instance_id": self.instance_id,
            "variable_name": self.variable_name,
            "origin_tag": self.origin_tag,
            "isCharacter": self.isCharacter,
            "appendix_enabled": self.appendix_enabled,
            "full_data": self.data
        }
    
    def contextMenuEvent(self, event: QMouseEvent):
        """우클릭 시 캐릭터 교체 메뉴를 표시합니다."""
        # adventure_character_bench에서 온 아이템일 경우에만 메뉴 표시
        if self.origin_tag != 'adventure_character_bench' or not self.parent_bench:
            return

        # 부모 Testbench에 자신을 제외한 다른 아이템 목록 요청
        other_items = self.parent_bench.get_other_items(self)
        if not other_items:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: #333; color: white; border: 1px solid #555; }}
            QMenu::item:selected {{ background-color: #555; }}
        """)
        
        # 메뉴 최상단에 정보 라벨 추가
        title_action = QAction("Switch to ...", self)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        # 다른 아이템들로 교체할 수 있는 액션 추가
        for item in other_items:
            action = QAction(item.variable_name, self)
            # lambda의 인자를 명시적으로 캡처하여 올바른 변수명이 전달되도록 함
            action.triggered.connect(
                lambda checked=False, source=self, target_name=item.variable_name: 
                source.swap_requested.emit(source, target_name)
            )
            menu.addAction(action)
        
        menu.exec(event.globalPos())