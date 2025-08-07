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
        
        # 검색 컨트롤러 시그널 연결
        mw.search_controller.search_progress.connect(self.update_search_progress)
        mw.search_controller.partial_search_result.connect(self.on_partial_search_result)
        mw.search_controller.search_complete.connect(self.on_search_complete)
        mw.search_controller.search_error.connect(self.on_search_error)
        
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
        """자동화 모듈과의 시그널 연결"""
        # 자동화 모듈 찾기
        if self.main_window.middle_section_controller:
            for module in self.main_window.middle_section_controller.module_instances:
                if hasattr(module, 'automation_controller'):
                    self.main_window.automation_module = module
                    break
        
        if hasattr(self.main_window, 'automation_module') and self.main_window.automation_module:
            try:
                # 콜백 함수 등록 (시그널 대신)
                self.main_window.automation_module.set_automation_status_callback(
                    self.main_window.update_automation_status
                )
                
                self.main_window.automation_module.set_generation_delay_callback(
                    self.main_window.on_generation_delay_changed
                )
                
                # [신규] 자동 생성 상태 확인 콜백 등록
                self.main_window.automation_module.set_auto_generate_status_callback(
                    self.get_auto_generate_status
                )

                # [신규] 자동화 활성 상태 확인 콜백 등록 (누락된 부분)
                self.main_window.automation_module.set_automation_active_status_callback(
                    self.main_window.get_automation_active_status
                )
                
                print("✅ 자동화 모듈 콜백 연결 완료")
            except Exception as e:
                print(f"⚠️ 자동화 모듈 콜백 연결 실패: {e}")
        else:
            print("⚠️ 자동화 모듈을 찾을 수 없습니다.")
        
    def connect_checkbox_signals(self):
        """체크박스 시그널을 연결하는 메서드 (init에서 호출)"""
        try:
            prompt_fixed_checkbox = self.main_window.generation_checkboxes.get("프롬프트 고정")
            if prompt_fixed_checkbox:
                prompt_fixed_checkbox.toggled.connect(self.update_random_prompt_button_state)
                
            # 초기 상태 설정
            self.update_random_prompt_button_state()
            
        except Exception as e:
            print(f"❌ 체크박스 시그널 연결 오류: {e}")
    
    # === Helper Methods ===
    
    def get_auto_generate_status(self) -> bool:
        """현재 자동 생성 체크박스 상태를 반환"""
        try:
            auto_generate_checkbox = self.main_window.generation_checkboxes.get("자동 생성")
            if auto_generate_checkbox:
                return auto_generate_checkbox.isChecked()
            return False
        except Exception as e:
            print(f"⚠️ 자동 생성 상태 확인 실패: {e}")
            return False

    def update_random_prompt_button_state(self):
        """generation_checkboxes 상태에 따라 random_prompt_btn을 활성화/비활성화"""
        try:
            # "프롬프트 고정" 체크박스가 체크되어 있으면 버튼 비활성화
            prompt_fixed_checkbox = self.main_window.generation_checkboxes.get("프롬프트 고정")
            
            if prompt_fixed_checkbox and prompt_fixed_checkbox.isChecked():
                self.main_window.random_prompt_btn.setEnabled(False)
                self.main_window.random_prompt_btn.setText("프롬프트 고정됨")
            else:
                self.main_window.random_prompt_btn.setEnabled(True)
                self.main_window.random_prompt_btn.setText("랜덤/다음 프롬프트")
                
        except Exception as e:
            print(f"❌ 버튼 상태 업데이트 오류: {e}")
    
    # === 검색 관련 이벤트 핸들러 ===
    
    def update_search_progress(self, completed: int, total: int):
        """검색 진행률에 따라 UI 업데이트"""
        percentage = int((completed / total) * 100) if total > 0 else 0
        self.main_window.progress_label.setText(f"{completed}/{total}")
        self.main_window.search_btn.setText(f"검색 중 ({percentage}%)")
        
    def on_partial_search_result(self, partial_df: pd.DataFrame):
        """부분 검색 결과를 받아 UI에 즉시 반영"""
        self.main_window.search_results.append_dataframe(partial_df)
        self.main_window.result_label1.setText(f"검색: {self.main_window.search_results.get_count()}")
        self.main_window.result_label2.setText(f"남음: {self.main_window.search_results.get_count()}")
        
    def on_search_complete(self, total_count: int):
        """검색 완료 시 호출되는 슬롯, 결과 파일 저장"""
        self.main_window.search_btn.setEnabled(True)
        self.main_window.search_btn.setText("검색")
        self.main_window.progress_label.setVisible(False)
        self.main_window.status_bar.showMessage(f"✅ 검색 완료! {total_count}개의 결과를 찾았습니다.", 5000)

        # [신규] 검색 결과 Parquet 파일로 저장
        if not self.main_window.search_results.is_empty():
            try:
                self.main_window.search_results.get_dataframe().to_parquet('naia_temp_rows.parquet')
            except Exception as e:
                self.main_window.status_bar.showMessage(f"⚠️ 결과 파일 저장 실패: {e}", 5000)
        
    def on_search_error(self, error_message: str):
        """검색 오류 발생 시 호출되는 슬롯"""
        self.main_window.search_btn.setEnabled(True)
        self.main_window.search_btn.setText("검색")
        self.main_window.progress_label.setVisible(False)
        self.main_window.status_bar.showMessage(f"❌ 검색 오류: {error_message}", 5000)
        
    # === 생성 관련 이벤트 핸들러 ===
    
    def on_prompt_generated(self, prompt_text: str):
        """프롬프트 생성 완료 처리"""
        # MainWindow의 실제 구현 호출
        self.main_window.on_prompt_generated(prompt_text)
        
    def on_generation_error(self, error_message: str):
        """생성 오류 처리"""
        # MainWindow의 실제 구현 호출
        self.main_window.on_generation_error(error_message)
        
    def on_instant_generation_requested(self, tags_dict):
        """즉시 생성 요청 처리"""
        # MainWindow의 실제 구현 호출 (있는 경우)
        if hasattr(self.main_window, 'on_instant_generation_requested'):
            self.main_window.on_instant_generation_requested(tags_dict)
    
    # === 설정 관리 메서드 ===
    
    def load_generation_parameters(self):
        """생성 파라미터 로드"""
        # 기존 방식 대신 모드별 로드
        current_mode = self.main_window.app_context.get_api_mode()
        self.main_window.generation_params_manager.load_mode_settings(current_mode)
        
    def save_generation_parameters(self):
        """생성 파라미터 저장"""
        # 기존 방식 대신 모드별 저장
        current_mode = self.main_window.app_context.get_api_mode()
        self.main_window.generation_params_manager.save_mode_settings(current_mode)
        
    def save_all_current_settings(self):
        """모든 현재 설정 저장"""
        try:
            current_mode = self.main_window.app_context.get_api_mode()
            
            # 버튼 상태 변경 (저장 중 표시)
            self.main_window.save_settings_btn.setText("💾 저장 중...")
            self.main_window.save_settings_btn.setEnabled(False)
            
            saved_items = []
            failed_items = []
            
            # 1. 메인 생성 파라미터 저장
            try:
                self.main_window.generation_params_manager.save_mode_settings(current_mode)
                saved_items.append("메인 생성 파라미터")
            except Exception as e:
                failed_items.append(f"메인 생성 파라미터: {str(e)}")
            
            # 2. 모든 ModeAware 모듈 설정 저장
            if self.main_window.app_context and self.main_window.app_context.mode_manager:
                try:
                    self.main_window.app_context.mode_manager.save_all_current_mode()
                    
                    # 저장된 모듈 수 계산
                    mode_aware_count = len(self.main_window.app_context.mode_manager.registered_modules)
                    if mode_aware_count > 0:
                        saved_items.append(f"모드 인식 모듈 ({mode_aware_count}개)")
                    
                except Exception as e:
                    failed_items.append(f"모드 인식 모듈: {str(e)}")
               
            # 결과 메시지 생성
            if saved_items and not failed_items:
                # 모든 저장 성공
                message = f"✅ 설정 저장 완료 ({current_mode} 모드)\n저장된 항목: {', '.join(saved_items)}"
                self.main_window.status_bar.showMessage(f"✅ 모든 설정이 저장되었습니다 ({current_mode} 모드)", 4000)
                
            elif saved_items and failed_items:
                # 일부 저장 성공, 일부 실패
                message = f"⚠️ 설정 부분 저장 완료 ({current_mode} 모드)\n✅ 저장됨: {', '.join(saved_items)}\n❌ 실패: {', '.join(failed_items)}"
                self.main_window.status_bar.showMessage(f"⚠️ 일부 설정 저장 실패", 4000)
                
            else:
                # 모든 저장 실패
                message = f"❌ 설정 저장 실패 ({current_mode} 모드)\n실패 항목: {', '.join(failed_items)}"
                self.main_window.status_bar.showMessage("❌ 설정 저장 실패", 4000)
            
            print(message)
            
            # 성공한 항목이 있으면 토스트 메시지도 표시
            if saved_items:
                # QMessageBox로 간단한 알림 표시 (자동으로 사라지지 않음, 사용자가 확인 필요)
                msg = QMessageBox(self.main_window)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("설정 저장 완료")
                msg.setText(f"현재 모드({current_mode})의 설정이 저장되었습니다.")
                
                details = f"저장된 항목:\n• " + "\n• ".join(saved_items)
                if failed_items:
                    details += f"\n\n실패한 항목:\n• " + "\n• ".join(failed_items)
                msg.setDetailedText(details)
                
                # 자동으로 닫히도록 타이머 설정 (3초 후 자동 닫기)
                timer = QTimer()
                timer.timeout.connect(msg.accept)
                timer.setSingleShot(True)
                timer.start(3000)  # 3초 후 자동 닫기
                
                msg.exec()
            
        except Exception as e:
            error_message = f"❌ 설정 저장 중 예외 발생: {str(e)}"
            print(error_message)
            self.main_window.status_bar.showMessage("❌ 설정 저장 중 오류 발생", 4000)
            
        finally:
            # 버튼 상태 복원
            self.main_window.save_settings_btn.setText("💾 설정 저장")
            self.main_window.save_settings_btn.setEnabled(True)
    
    # === API 테스트 메서드 ===
    
    def test_webui(self, url):
        """WebUI 연결 테스트 함수"""
        import requests
        # ignore http or https, check both.
        url = url.replace('http://', '').replace('https://', '').rstrip('/')
        # just checking connection, so any api is okay.
        try:
            if "127.0" not in url: res = requests.get(f"https://{url}/sdapi/v1/progress?skip_current_image=true", timeout=1)
            else: res = requests.get(f"http://{url}/sdapi/v1/progress?skip_current_image=true", timeout=1)
            if res.status_code == 200 and 'progress' in res.json():
                return f'https://{url}'
            else:
                raise Exception('invalid status')
        except Exception:
            try:
                res = requests.get(f"http://{url}/sdapi/v1/progress?skip_current_image=true", timeout=1)
                if res.status_code == 200 and 'progress' in res.json():
                    return f'http://{url}'
                else:
                    raise Exception('invalid status')
            except Exception:
                pass
        return None
        
    def test_comfyui(self, url):
        """ComfyUI 연결 테스트 함수 (test_webui와 유사한 패턴)"""
        import requests
        import json
        
        # URL 정규화 및 프로토콜 테스트
        test_urls = []
        clean_url = url.replace('https://', '').replace('http://', '')
        
        # 포트가 없으면 기본 ComfyUI 포트(8188) 추가
        if ':' not in clean_url:
            clean_url = f"{clean_url}:8188"
        
        # HTTP와 HTTPS 모두 테스트
        test_urls.append(f"http://{clean_url}")
        test_urls.append(f"https://{clean_url}")
        
        for test_url in test_urls:
            try:
                print(f"🔍 ComfyUI 연결 테스트: {test_url}")
                
                # /system_stats 엔드포인트로 연결 테스트
                response = requests.get(f"{test_url}/system_stats", timeout=8)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # ComfyUI 응답 구조 확인
                        if 'system' in data or 'devices' in data:
                            print(f"✅ ComfyUI 연결 성공: {test_url}")
                            return test_url
                    except json.JSONDecodeError:
                        continue
                
            except requests.exceptions.ConnectTimeout:
                print(f"⏰ ComfyUI 연결 시간 초과: {test_url}")
                continue
            except requests.exceptions.ConnectionError:
                print(f"❌ ComfyUI 연결 실패: {test_url}")
                continue
            except Exception as e:
                print(f"❌ ComfyUI 테스트 중 예외: {test_url} - {e}")
                continue
        
        print(f"❌ 모든 ComfyUI 연결 시도 실패: {url}")
        return None
    
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