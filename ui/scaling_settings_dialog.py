"""
UI 스케일링 설정 다이얼로그
사용자가 UI 크기를 조정할 수 있는 설정 창
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, 
    QPushButton, QGroupBox, QSpinBox, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.scaling_manager import get_scaling_manager, get_scaled_font_size
from ui.theme import DARK_COLORS


class ScalingSettingsDialog(QDialog):
    """UI 스케일링 설정 다이얼로그"""
    
    scaling_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scaling_manager = get_scaling_manager()
        self.setup_ui()
        self.load_current_settings()
        self.connect_signals()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("UI 크기 설정")
        self.setModal(True)
        #self.setFixedSize(500, 800)
        
        # 다이얼로그 스타일 설정
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_COLORS['bg_primary']};
                color: {DARK_COLORS['text_primary']};
                font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title = QLabel("UI 크기 및 스케일링 설정")
        title.setStyleSheet(f"""
            font-size: {get_scaled_font_size(18)}px;
            font-weight: bold;
            color: {DARK_COLORS['text_primary']};
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 현재 정보 표시
        self.info_group = self.create_info_group()
        layout.addWidget(self.info_group)
        
        # 스케일링 설정 그룹
        self.scaling_group = self.create_scaling_group()
        layout.addWidget(self.scaling_group)
        
        # 미리보기 그룹
        self.preview_group = self.create_preview_group()
        layout.addWidget(self.preview_group)
        
        # 버튼 그룹
        button_layout = self.create_button_layout()
        layout.addLayout(button_layout)
    
    def create_info_group(self):
        """현재 상태 정보 그룹 생성"""
        group = QGroupBox("현재 상태")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {DARK_COLORS['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        
        # 현재 해상도 정보
        self.resolution_label = QLabel()
        self.dpi_label = QLabel()
        self.current_scale_label = QLabel()
        
        for label in [self.resolution_label, self.dpi_label, self.current_scale_label]:
            label.setStyleSheet(f"""
                color: {DARK_COLORS['text_secondary']};
                font-size: {get_scaled_font_size(14)}px;
                margin: 2px 0;
            """)
            layout.addWidget(label)
        
        return group
    
    def create_scaling_group(self):
        """스케일링 설정 그룹 생성"""
        group = QGroupBox("스케일링 설정")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {DARK_COLORS['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        
        # 자동 스케일링 체크박스
        self.auto_scaling_cb = QCheckBox("자동 스케일링 (DPI 기반)")
        self.auto_scaling_cb.setStyleSheet(f"""
            QCheckBox {{
                font-size: {get_scaled_font_size(14)}px;
                color: {DARK_COLORS['text_primary']};
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        layout.addWidget(self.auto_scaling_cb)
        
        # 수동 스케일링 컨트롤
        manual_layout = QHBoxLayout()
        
        manual_label = QLabel("수동 스케일:")
        manual_label.setStyleSheet(f"color: {DARK_COLORS['text_primary']}; font-size: {get_scaled_font_size(14)}px;")
        manual_layout.addWidget(manual_label)
        
        # 스케일 슬라이더
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 200)  # 0.5x ~ 2.0x
        self.scale_slider.setValue(100)
        self.scale_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {DARK_COLORS['bg_secondary']};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {DARK_COLORS['accent_blue']};
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DARK_COLORS['accent_blue_hover']};
            }}
        """)
        manual_layout.addWidget(self.scale_slider)
        
        # 스케일 값 표시
        self.scale_value_label = QLabel("100%")
        self.scale_value_label.setStyleSheet(f"""
            color: {DARK_COLORS['text_primary']};
            font-size: {get_scaled_font_size(14)}px;
            font-weight: bold;
            min-width: 50px;
        """)
        manual_layout.addWidget(self.scale_value_label)
        
        layout.addLayout(manual_layout)
        
        # 해상도별 권장 설정
        preset_layout = QHBoxLayout()
        
        preset_label = QLabel("빠른 설정:")
        preset_label.setStyleSheet(f"color: {DARK_COLORS['text_primary']}; font-size: {get_scaled_font_size(14)}px;")
        preset_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "자동 감지",
            "FHD (1920x1080) - 80%", 
            "QHD (2560x1440) - 100%",
            "4K (3840x2160) - 150%"
        ])
        self.preset_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {DARK_COLORS['text_primary']};
                font-size: {get_scaled_font_size(14)}px;
            }}
            QComboBox:hover {{
                border: 1px solid {DARK_COLORS['border_light']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {DARK_COLORS['text_secondary']};
            }}
        """)
        preset_layout.addWidget(self.preset_combo)
        
        layout.addLayout(preset_layout)
        
        return group
    
    def create_preview_group(self):
        """미리보기 그룹 생성"""
        group = QGroupBox("미리보기")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {DARK_COLORS['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        
        # 미리보기 텍스트
        self.preview_label = QLabel("이 텍스트로 크기를 미리 확인해보세요")
        self.preview_label.setStyleSheet(f"""
            color: {DARK_COLORS['text_primary']};
            border: 1px solid {DARK_COLORS['border']};
            border-radius: 4px;
            padding: 10px;
            background-color: {DARK_COLORS['bg_secondary']};
        """)
        layout.addWidget(self.preview_label)
        
        return group
    
    def create_button_layout(self):
        """버튼 레이아웃 생성"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 기본값 복원 버튼
        self.reset_btn = QPushButton("기본값 복원")
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_COLORS['bg_tertiary']};
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 4px;
                padding: 8px 16px;
                color: {DARK_COLORS['text_primary']};
                font-size: {get_scaled_font_size(14)}px;
            }}
            QPushButton:hover {{
                background-color: {DARK_COLORS['bg_hover']};
            }}
        """)
        layout.addWidget(self.reset_btn)
        
        # 취소 버튼
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_COLORS['bg_tertiary']};
                border: 1px solid {DARK_COLORS['border']};
                border-radius: 4px;
                padding: 8px 16px;
                color: {DARK_COLORS['text_primary']};
                font-size: {get_scaled_font_size(14)}px;
            }}
            QPushButton:hover {{
                background-color: {DARK_COLORS['bg_hover']};
            }}
        """)
        layout.addWidget(self.cancel_btn)
        
        # 적용 버튼
        self.apply_btn = QPushButton("적용")
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_COLORS['accent_blue']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: {DARK_COLORS['text_primary']};
                font-size: {get_scaled_font_size(14)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DARK_COLORS['accent_blue_hover']};
            }}
        """)
        layout.addWidget(self.apply_btn)
        
        return layout
    
    def connect_signals(self):
        """시그널 연결"""
        self.auto_scaling_cb.toggled.connect(self.on_auto_scaling_toggled)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.reset_btn.clicked.connect(self.reset_to_default)
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self.apply_settings)
    
    def load_current_settings(self):
        """현재 설정 로드"""
        # 현재 상태 정보 업데이트
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                geometry = screen.geometry()
                self.resolution_label.setText(f"해상도: {geometry.width()} x {geometry.height()}")
                self.dpi_label.setText(f"DPI: {screen.physicalDotsPerInch():.1f}")
        
        current_scale = self.scaling_manager.get_scale_factor()
        self.current_scale_label.setText(f"현재 스케일: {current_scale:.2f}x ({current_scale*100:.0f}%)")
        
        # 설정 값 로드
        self.auto_scaling_cb.setChecked(self.scaling_manager.is_auto_scaling_enabled())
        user_scale = self.scaling_manager.get_user_scale_factor()
        self.scale_slider.setValue(int(user_scale * 100))
        self.update_scale_label()
        self.update_preview()
    
    def on_auto_scaling_toggled(self, checked):
        """자동 스케일링 토글"""
        self.scale_slider.setEnabled(not checked)
        self.preset_combo.setEnabled(not checked)
        if checked:
            self.preset_combo.setCurrentIndex(0)
    
    def on_scale_changed(self, value):
        """스케일 슬라이더 변경"""
        self.update_scale_label()
        self.update_preview()
    
    def on_preset_changed(self, index):
        """프리셋 변경"""
        if index == 0:  # 자동 감지
            self.auto_scaling_cb.setChecked(True)
        else:
            self.auto_scaling_cb.setChecked(False)
            scales = [100, 80, 100, 150]  # 각 프리셋의 스케일 값
            if index < len(scales):
                self.scale_slider.setValue(scales[index])
    
    def update_scale_label(self):
        """스케일 라벨 업데이트"""
        value = self.scale_slider.value()
        self.scale_value_label.setText(f"{value}%")
    
    def update_preview(self):
        """미리보기 업데이트"""
        scale_factor = self.scale_slider.value() / 100.0
        base_font_size = 14
        preview_font_size = int(base_font_size * scale_factor)
        
        self.preview_label.setStyleSheet(f"""
            color: {DARK_COLORS['text_primary']};
            border: 1px solid {DARK_COLORS['border']};
            border-radius: 4px;
            padding: 10px;
            background-color: {DARK_COLORS['bg_secondary']};
            font-size: {preview_font_size}px;
        """)
    
    def reset_to_default(self):
        """기본값으로 복원"""
        self.auto_scaling_cb.setChecked(True)
        self.scale_slider.setValue(100)
        self.preset_combo.setCurrentIndex(0)
    
    def apply_settings(self):
        """설정 적용"""
        auto_enabled = self.auto_scaling_cb.isChecked()
        user_scale = self.scale_slider.value() / 100.0
        
        self.scaling_manager.set_auto_scaling_enabled(auto_enabled)
        self.scaling_manager.set_user_scale_factor(user_scale)
        
        self.scaling_changed.emit(self.scaling_manager.get_scale_factor())
        self.accept()