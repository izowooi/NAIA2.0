"""
NAIA Main Controller
메인 윈도우의 이벤트 핸들러와 비즈니스 로직을 담당하는 컨트롤러
"""

import os
import json
import pandas as pd
import requests
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtGui import QTextCursor
from PIL import Image
from ui.theme import DARK_COLORS, get_dynamic_styles
from ui.scaling_manager import get_scaled_font_size
from core.search_result_model import SearchResultModel
from utils.load_generation_params import GenerationParamsManager


class MainController:
    """메인 윈도우의 비즈니스 로직과 이벤트 핸들링을 담당하는 컨트롤러"""
    
    def __init__(self, main_window):
        """
        Args:
            main_window: ModernMainWindow 인스턴스
        """
        self.main_window = main_window
        
    # === 스케일링 관련 메서드 ===
    
    def on_scaling_changed(self, new_scale):
        """스케일링 변경 시 호출"""
        print(f"UI 스케일링이 {new_scale:.2f}x로 변경되었습니다.")
        self.main_window.apply_dynamic_styles()
        # 메뉴바에 UI 설정 추가할 것이라면 여기서 업데이트
        self.refresh_all_ui_elements()
    
    def refresh_all_ui_elements(self):
        """모든 UI 요소 새로고침"""
        try:
            # DARK_STYLES를 새로 생성하여 최신 스케일링 적용
            from ui import theme
            theme.DARK_STYLES = theme.get_legacy_dark_styles()
            
            dynamic_styles = get_dynamic_styles()
            
            # 기존 위젯들의 스타일 업데이트
            from PyQt6.QtWidgets import QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QTabWidget, QApplication
            
            # 애플리케이션 전체에서 위젯 검색 (더 포괄적)
            app = QApplication.instance()
            all_widgets = app.allWidgets() if app else []
            
            # QPushButton 업데이트 - 더 정확한 스타일 매칭
            buttons_to_update = [w for w in all_widgets if isinstance(w, QPushButton)]
            for widget in buttons_to_update:
                current_style = widget.styleSheet()
                
                # Primary button 식별 (파란색 배경)
                if ("#1976D2" in current_style or "accent_blue" in current_style or 
                    "background-color: #1976D2" in current_style):
                    widget.setStyleSheet(dynamic_styles.get('primary_button', ''))
                
                # Secondary button 식별 (회색 배경 + 테두리)
                elif ("#2B2B2B" in current_style or "bg_tertiary" in current_style or
                      "border: 1px solid" in current_style):
                    widget.setStyleSheet(dynamic_styles.get('secondary_button', ''))
                
                # Compact button 식별 (작은 버튼들)
                elif ("compact" in widget.objectName().lower() or 
                      widget.text() in ["💾 설정 저장", "복원", "🔍 검색", "🎲 랜덤"]):
                    widget.setStyleSheet(dynamic_styles.get('compact_button', ''))
                
                # 기본적으로 DARK_STYLES를 사용하는 버튼들은 모두 업데이트
                elif current_style and len(current_style.strip()) > 50:  # 복잡한 스타일이 있는 경우
                    # 버튼 타입을 추정하여 적절한 스타일 적용
                    if "4CAF50" in current_style or "success" in current_style:
                        # 성공/저장 버튼은 primary로 처리
                        widget.setStyleSheet(dynamic_styles.get('primary_button', ''))
                    elif widget.isCheckable():
                        # 체크 가능한 버튼은 toggle_button으로 처리
                        widget.setStyleSheet(dynamic_styles.get('toggle_button', ''))
                    else:
                        # 기타 복잡한 스타일의 버튼은 secondary로 처리
                        widget.setStyleSheet(dynamic_styles.get('secondary_button', ''))
            
            # QLabel 업데이트 (전체 애플리케이션에서)
            labels_to_update = [w for w in all_widgets if isinstance(w, QLabel)]
            for widget in labels_to_update:
                style = widget.styleSheet()
                if 'label_style' in style or not style or 'font-size:' in style:
                    widget.setStyleSheet(dynamic_styles.get('label_style', ''))
            
            # QLineEdit 업데이트 (전체 애플리케이션에서)
            lineedits_to_update = [w for w in all_widgets if isinstance(w, QLineEdit)]
            for widget in lineedits_to_update:
                if widget.styleSheet():  # 기존 스타일이 있는 경우에만 업데이트
                    widget.setStyleSheet(dynamic_styles.get('compact_lineedit', ''))
                
            # QTextEdit 업데이트 (전체 애플리케이션에서)
            textedits_to_update = [w for w in all_widgets if isinstance(w, QTextEdit)]
            for widget in textedits_to_update:
                current_style = widget.styleSheet()
                if current_style:  # 기존 스타일이 있는 경우에만 업데이트
                    if "transparent" in current_style:
                        widget.setStyleSheet(dynamic_styles.get('dark_text_edit', ''))
                    else:
                        widget.setStyleSheet(dynamic_styles.get('compact_textedit', ''))
            
            # QCheckBox 업데이트 (전체 애플리케이션에서)
            checkboxes_to_update = [w for w in all_widgets if isinstance(w, QCheckBox)]
            for widget in checkboxes_to_update:
                widget.setStyleSheet(dynamic_styles.get('dark_checkbox', ''))
            
            # CollapsibleBox 업데이트 (전체 애플리케이션에서)
            from ui.collapsible import EnhancedCollapsibleBox, CollapsibleBox
            collapsible_widgets = [w for w in all_widgets if isinstance(w, (EnhancedCollapsibleBox, CollapsibleBox))]
            for widget in collapsible_widgets:
                widget.setStyleSheet(dynamic_styles.get('collapsible_box', ''))
            
            # Tab UI 업데이트 (전체 애플리케이션에서)
            tab_widgets = [w for w in all_widgets if isinstance(w, QTabWidget)]
            for widget in tab_widgets:
                widget.setStyleSheet(dynamic_styles.get('dark_tabs', ''))
            
            # QComboBox 업데이트 (전체 애플리케이션에서)
            from PyQt6.QtWidgets import QComboBox, QSpinBox, QDoubleSpinBox, QSlider
            comboboxes_to_update = [w for w in all_widgets if isinstance(w, QComboBox)]
            for widget in comboboxes_to_update:
                if widget.styleSheet():  # 기존 스타일이 있는 경우에만 업데이트
                    widget.setStyleSheet(dynamic_styles.get('compact_combobox', ''))
            
            # QSpinBox & QDoubleSpinBox 업데이트 (전체 애플리케이션에서)
            spinboxes_to_update = [w for w in all_widgets if isinstance(w, (QSpinBox, QDoubleSpinBox))]
            for widget in spinboxes_to_update:
                if widget.styleSheet():
                    widget.setStyleSheet(dynamic_styles.get('compact_spinbox', ''))
            
            # QSlider 업데이트 (전체 애플리케이션에서)
            sliders_to_update = [w for w in all_widgets if isinstance(w, QSlider)]
            for widget in sliders_to_update:
                if widget.styleSheet():
                    widget.setStyleSheet(dynamic_styles.get('compact_slider', ''))
            
            # 폰트 크기가 하드코딩된 위젯들 업데이트
            if hasattr(self.main_window, 'progress_label'):
                scaled_size = get_scaled_font_size(16)
                self.main_window.progress_label.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; font-size: {scaled_size}px; margin-right: 10px;")
                
            if hasattr(self.main_window, 'result_label1'):
                scaled_size = get_scaled_font_size(18)  
                self.main_window.result_label1.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; font-family: 'Pretendard'; font-size: {scaled_size}px;")
                
            if hasattr(self.main_window, 'result_label2'):
                scaled_size = get_scaled_font_size(18)
                self.main_window.result_label2.setStyleSheet(f"color: {DARK_COLORS['text_secondary']}; font-family: 'Pretendard'; font-size: {scaled_size}px;")
                
            print(f"🔄 동적 스케일링 적용 완료:")
            print(f"   - 버튼: {len(buttons_to_update)}개")
            print(f"   - 라벨: {len(labels_to_update)}개") 
            print(f"   - 입력창: {len(lineedits_to_update)}개")
            print(f"   - 텍스트박스: {len(textedits_to_update)}개")
            print(f"   - 체크박스: {len(checkboxes_to_update)}개")
            print(f"   - CollapsibleBox: {len(collapsible_widgets)}개")
            print(f"   - Tab: {len(tab_widgets)}개")
            print(f"   - 콤보박스: {len(comboboxes_to_update)}개")
            print(f"   - 스핀박스: {len(spinboxes_to_update)}개")
            print(f"   - 슬라이더: {len(sliders_to_update)}개")
                
        except Exception as e:
            print(f"UI 요소 새로고침 중 오류: {e}")
    
    # === 신호 연결 메서드 ===
    
    def connect_signals(self):
        """신호들을 연결"""
        mw = self.main_window  # 축약형
        
        mw.search_btn.clicked.connect(mw.trigger_search)
        mw.save_settings_btn.clicked.connect(self.save_all_current_settings)
        mw.restore_btn.clicked.connect(mw.restore_search_results)
        mw.deep_search_btn.clicked.connect(mw.open_depth_search_tab)
        mw.random_prompt_btn.clicked.connect(mw.trigger_random_prompt)
        mw.image_window.instant_generation_requested.connect(self.on_instant_generation_requested)
        mw.generate_button_main.clicked.connect(
            mw.generation_controller.execute_generation_pipeline
        )
        mw.prompt_gen_controller.prompt_generated.connect(self.on_prompt_generated)
        mw.prompt_gen_controller.generation_error.connect(self.on_generation_error)
        mw.prompt_gen_controller.prompt_popped.connect(self.on_prompt_popped)
        mw.prompt_gen_controller.resolution_detected.connect(self.on_resolution_detected)
        mw.image_window.load_prompt_to_main_ui.connect(mw.set_positive_prompt)
        mw.image_window.instant_generation_requested.connect(self.on_instant_generation_requested)
        self.connect_checkbox_signals()
        mw.workflow_load_btn.clicked.connect(self._load_custom_workflow_from_image)
        mw.workflow_default_btn.clicked.connect(self._on_workflow_type_changed)
        mw.image_window.instant_generation_requested.connect(self.on_instant_generation_requested)
        if hasattr(mw.image_window, 'generate_with_image_requested'):
            mw.image_window.generate_with_image_requested.connect(self.on_generate_with_image_requested)
            print("✅ generate_with_image_requested 시그널이 연결되었습니다.")
        else:
            print("⚠️ generate_with_image_requested 시그널을 찾을 수 없습니다.")
        if hasattr(mw.image_window, 'send_to_inpaint_requested'):
            mw.image_window.send_to_inpaint_requested.connect(self.on_send_to_inpaint_requested)
        
    def connect_automation_signals(self):
        """자동화 관련 신호 연결"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def connect_checkbox_signals(self):
        """체크박스 신호 연결"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
    
    # === 검색 관련 이벤트 핸들러 ===
    
    def update_search_progress(self, completed: int, total: int):
        """검색 진행률 업데이트"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def on_partial_search_result(self, partial_df: pd.DataFrame):
        """부분 검색 결과 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def on_search_complete(self, total_count: int):
        """검색 완료 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def on_search_error(self, error_message: str):
        """검색 오류 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    # === 생성 관련 이벤트 핸들러 ===
    
    def on_prompt_generated(self, prompt_text: str):
        """프롬프트 생성 완료 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def on_generation_error(self, error_message: str):
        """생성 오류 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def on_instant_generation_requested(self, tags_dict):
        """즉시 생성 요청 처리"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
    
    # === 설정 관리 메서드 ===
    
    def load_generation_parameters(self):
        """생성 파라미터 로드"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def save_generation_parameters(self):
        """생성 파라미터 저장"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def save_all_current_settings(self):
        """모든 현재 설정 저장"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
    
    # === API 테스트 메서드 ===
    
    def test_webui(self, url):
        """WebUI API 테스트"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
        
    def test_comfyui(self, url):
        """ComfyUI API 테스트"""
        # 이 메서드는 메인 파일에서 이동해올 예정
        pass
    
    # === 기타 이벤트 핸들러 메서드 ===
    
    def on_prompt_popped(self, remaining_count: int):
        """프롬프트 팝 이벤트 처리"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, 'on_prompt_popped'):
            self.main_window.on_prompt_popped(remaining_count)
        
    def on_resolution_detected(self, width: int, height: int):
        """해상도 감지 이벤트 처리"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, 'on_resolution_detected'):
            self.main_window.on_resolution_detected(width, height)
            
    def on_generate_with_image_requested(self, tags_dict):
        """이미지와 함께 생성 요청 처리"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, 'on_generate_with_image_requested'):
            self.main_window.on_generate_with_image_requested(tags_dict)
            
    def on_send_to_inpaint_requested(self, history_item):
        """인페인트 전송 요청 처리"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, 'on_send_to_inpaint_requested'):
            self.main_window.on_send_to_inpaint_requested(history_item)
            
    def _load_custom_workflow_from_image(self):
        """이미지에서 커스텀 워크플로우 로드"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, '_load_custom_workflow_from_image'):
            self.main_window._load_custom_workflow_from_image()
            
    def _on_workflow_type_changed(self):
        """워크플로우 타입 변경 처리"""
        # 메인 윈도우에 위임
        if hasattr(self.main_window, '_on_workflow_type_changed'):
            self.main_window._on_workflow_type_changed()