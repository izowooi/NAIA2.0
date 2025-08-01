import io
from PIL import Image
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDoubleSpinBox, QFrame, QSlider)
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from PIL.ImageQt import ImageQt
import numpy as np
from .theme import DARK_STYLES, DARK_COLORS
from .inpaint_window import InpaintWindow
from core.context import AppContext

class Img2ImgPanel(QFrame):
    """
    Img2Img UI를 위한 커스텀 패널 (슬라이더 및 이미지 크롭 적용).
    """
    def __init__(self, app_context: AppContext, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        
        # [2단계] 상태 관리 변수 추가
        self.mode = 'img2img'  # 'img2img' 또는 'inpaint'
        self.original_pil_image: Image.Image = None
        self.background_pixmap: QPixmap = None
        self.full_mask_pil: Image.Image = None
        self.small_mask_pil: Image.Image = None
        
        self.init_ui()
        self.setVisible(False)

    def init_ui(self):
        self.setStyleSheet(f"""
            Img2ImgPanel {{
                background-color: transparent;
                border: 1px solid {DARK_COLORS['border_light']};
                border-radius: 8px;
            }}
        """)
        self.setMinimumHeight(220)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(15)

        # 상단: 타이틀 + 닫기 버튼
        header_layout = QHBoxLayout()
        title_label = QLabel("Image2Image (NAI Only)")
        title_label.setStyleSheet("font-size: 24px; font-weight: 600; color: white; background-color: transparent;")

        subtitle_label = QLabel("Transform your image.")
        subtitle_label.setStyleSheet("font-size: 14px; color: #CCCCCC; background-color: transparent;")

        title_vbox = QVBoxLayout()
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(subtitle_label)

        close_button = QPushButton("X")
        close_button.setFixedSize(24, 24)
        close_button.setStyleSheet("QPushButton { border-radius: 12px; background-color: #555; color: white; font-weight: bold; } QPushButton:hover { background-color: #777; }")
        close_button.clicked.connect(self.hide_panel)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header_layout)

        # 중앙: 파라미터 컨트롤 (슬라이더)
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(15)

        # [수정] 일관된 슬라이더 스타일 정의
        slider_style = f"""
            QSlider::groove:horizontal {{
                background: #22253F;
                height: 12px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: #F5F3C2;
                width: 18px;  /* 사각 형태를 위해 너비 조정 */
                height: 18px;
                margin: -4px 0;
                border-radius: 2px; /* 모서리가 둥근 사각형 */
            }}
            QSlider::handle:horizontal:hover {{
                background: {DARK_COLORS['accent_blue_hover']};
            }}
            QSlider::sub-page:horizontal {{
                background: #525252;
                border-radius: 4px;
            }}
        """

        # Strength
        strength_group = QWidget()
        strength_hlayout = QHBoxLayout(strength_group)
        strength_hlayout.setContentsMargins(0, 0, 0, 0)
        strength_label = QLabel("Strength:")
        strength_label.setStyleSheet("font-size: 16px; color: white; background-color: transparent;")
        self.strength_value_label = QLabel("0.50")
        self.strength_value_label.setStyleSheet("font-size: 16px; color: #AAA; min-width: 40px; text-align: right; background-color: transparent;")
        self.strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.strength_slider.setRange(1, 99)
        self.strength_slider.setValue(50)
        self.strength_slider.setStyleSheet(slider_style) # [수정] 스타일 적용
        self.strength_slider.valueChanged.connect(self._update_strength_label)
        strength_hlayout.addWidget(strength_label)
        strength_hlayout.addWidget(self.strength_slider)
        strength_hlayout.addWidget(self.strength_value_label)
        controls_layout.addWidget(strength_group)

        # Noise
        noise_group = QWidget()
        noise_hlayout = QHBoxLayout(noise_group)
        noise_hlayout.setContentsMargins(0, 0, 0, 0)
        noise_label = QLabel("Noise:")
        noise_label.setStyleSheet("font-size: 16px; color: white; background-color: transparent;")
        self.noise_value_label = QLabel("0.05")
        self.noise_value_label.setStyleSheet("font-size: 16px; color: #AAA; min-width: 40px; text-align: right; background-color: transparent;")
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(0, 99)
        self.noise_slider.setValue(5)
        self.noise_slider.setStyleSheet(slider_style) # [수정] 스타일 적용
        self.noise_slider.valueChanged.connect(self._update_noise_label)
        noise_hlayout.addWidget(noise_label)
        noise_hlayout.addWidget(self.noise_slider)
        noise_hlayout.addWidget(self.noise_value_label)
        controls_layout.addWidget(noise_group)

        main_layout.addLayout(controls_layout)
        main_layout.addStretch(1)

        # 하단: Inpaint 버튼
        self.inpaint_button = QPushButton("Inpaint Image")
        self.inpaint_button.setStyleSheet(DARK_STYLES['secondary_button'])
        self.inpaint_button.clicked.connect(self._on_inpaint_button_clicked) # [2단계] 연결 메서드 변경
        self.inpaint_button.setFixedWidth(200)
        main_layout.addWidget(self.inpaint_button, alignment=Qt.AlignmentFlag.AlignRight)

    def _on_inpaint_button_clicked(self):
        if not self.original_pil_image:
            return

        result = InpaintWindow.get_inpaint_data(self.original_pil_image, self.full_mask_pil, self)
        
        if result is None:
            print("Inpaint 작업이 취소되었습니다.")
            return

        if "full_mask_image" in result:
            print("🎨 Inpaint 모드로 전환합니다.")
            self.mode = 'inpaint'
            self.full_mask_pil = result["full_mask_image"]
            self.small_mask_pil = result["small_mask_image"]
            
            # [3단계 수정] Inpaint 결과의 미리보기 이미지로 배경 업데이트
            preview_pil = result["preview_image"]
            q_image = ImageQt(preview_pil.convert("RGBA"))
            self.background_pixmap = QPixmap.fromImage(q_image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.update() # 패널 다시 그리기 요청

            self._update_ui_for_mode()
        else:
            print("🖼️ Img2Img 모드로 전환합니다 (마스크 없음).")
            self.mode = 'img2img'
            self.full_mask_pil = None
            self.small_mask_pil = None
            self._set_cropped_background() # 원본 크롭 이미지로 배경 복원
            self.update() # 패널 다시 그리기 요청
            self._update_ui_for_mode()

    # [2단계] 모드에 따라 UI를 업데이트하는 헬퍼 메서드
    def _update_ui_for_mode(self):
        if self.mode == 'inpaint':
            self.inpaint_button.setText("Edit Mask")
            self.inpaint_button.setStyleSheet(DARK_STYLES['primary_button']) # 강조 색상으로 변경
        else: # 'img2img'
            self.inpaint_button.setText("Inpaint Image")
            self.inpaint_button.setStyleSheet(DARK_STYLES['secondary_button'])

    def _update_strength_label(self, value):
        """Strength 슬라이더 값 변경 시 라벨 업데이트"""
        strength_value = value / 100.0
        self.strength_value_label.setText(f"{strength_value:.2f}")

    def _update_noise_label(self, value):
        """Noise 슬라이더 값 변경 시 라벨 업데이트"""
        noise_value = value / 100.0
        self.noise_value_label.setText(f"{noise_value:.2f}")

    def paintEvent(self, event):
        """배경 이미지를 먼저 그리고, 그 위에 기본 위젯들을 그립니다."""
        painter = QPainter(self)
        if self.background_pixmap:
            painter.drawPixmap(self.rect(), self.background_pixmap)

            # 어두운 오버레이 씌우기
            painter.fillRect(self.rect(), QColor(0, 0, 0, 155))

        # QFrame의 기본 paintEvent를 호출하여 테두리 등을 그리게 함
        super().paintEvent(event)

    def set_image(self, pil_image: Image.Image):
        """외부에서 이미지를 받아 패널을 활성화하고 모든 상태를 초기화합니다."""
        # [3단계 수정] 새 이미지 로드 시, 모드와 마스크 데이터를 초기화
        self.mode = 'img2img'
        self.full_mask_pil = None
        self.small_mask_pil = None
        self._update_ui_for_mode()

        self.original_pil_image = pil_image
        self._set_cropped_background() # 배경은 원본 크롭 이미지로 설정
        self.update() 
        self.setVisible(True)

    def _set_cropped_background(self):
        """원본 이미지의 중앙 상단을 기준으로 크롭하여 배경 이미지 설정."""
        if not self.original_pil_image:
            return

        width, height = self.original_pil_image.size
        panel_width = 832  # 적절한 너비 값 설정
        aspect_ratio = height / width

        crop_width = min(width, panel_width)
        crop_height = int(crop_width * aspect_ratio * 0.55)

        left = (width - crop_width) // 2
        top = max(0, (height // 2) - (crop_height // 2) - (height // 4)) # 중앙보다 살짝 위
        right = left + crop_width
        bottom = top + crop_height

        cropped_image = self.original_pil_image.crop((left, top, right, bottom))
        q_image = ImageQt(cropped_image.convert("RGBA"))
        self.background_pixmap = QPixmap.fromImage(q_image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

    def resizeEvent(self, event):
        """패널 크기 변경 시 배경 이미지 리사이즈"""
        super().resizeEvent(event)
        if self.original_pil_image:
            self._set_cropped_background()
            self.update()

    def hide_panel(self):
        """패널을 숨기고 모든 상태를 초기화합니다."""
        self.setVisible(False)
        self.mode = 'img2img'
        self.original_pil_image = None
        self.background_pixmap = None
        self.full_mask_pil = None
        self.small_mask_pil = None
        self._update_ui_for_mode() # UI 상태도 초기화

    def get_parameters(self) -> dict | None:
        if not self.isVisible() or not self.original_pil_image:
            return None

        # 공통 파라미터 생성
        byte_arr = io.BytesIO()
        width, height = self.original_pil_image.size
        self.original_pil_image.save(byte_arr, format='PNG')
        params = {
            "image_bytes": byte_arr.getvalue(),
            "strength": self.strength_slider.value() / 100.0,
            "noise": self.noise_slider.value() / 100.0,
            "width" : width,
            "height" : height
        }

        # Inpaint 모드일 경우 마스크 추가
        if self.mode == 'inpaint':
            params["type"] = "inpaint"
            api_mode = self.app_context.get_api_mode()
            
            mask_to_use = self.small_mask_pil if api_mode == "NAI" else self.full_mask_pil
            
            # 🔥 수정: 모든 API에 대해 완벽한 이진 PNG 전송
            mask_array = np.array(mask_to_use)
            
            # 완벽한 이진화 강제 (혹시 모를 중간값 제거)
            mask_array = np.where(mask_array > 127, 255, 0).astype(np.uint8)
            
            # 완벽한 이진 마스크를 PNG로 변환
            mask_image_clean = Image.fromarray(mask_array, mode='L')
            mask_byte_arr = io.BytesIO()
            
            if api_mode == "NAI":
                # NAI: 무압축 PNG로 저장하여 완벽한 품질 보장
                mask_image_clean.save(mask_byte_arr, format='PNG', compress_level=0, optimize=False)
                params["mask_bytes"] = mask_byte_arr.getvalue()
                print(f"✅ 무압축 PNG 마스크 전송 (NAI, Size: {mask_array.shape}, Unique: {np.unique(mask_array)})")
            else:
                # WebUI: 가벼운 압축 허용
                mask_image_clean.save(mask_byte_arr, format='PNG', compress_level=1, optimize=False)
                params["mask_bytes"] = mask_byte_arr.getvalue()
                print(f"✅ PNG 마스크 전송 (WebUI, Size: {mask_array.shape})")
        else:
            params["type"] = "img2img"

        return params