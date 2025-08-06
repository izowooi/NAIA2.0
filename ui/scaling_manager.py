"""
UI 스케일링 매니저
DPI 기반 자동 스케일링 및 사용자 정의 스케일링 지원
"""

import os
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QScreen


class ScalingManager(QObject):
    """UI 스케일링 관리 클래스"""
    
    scaling_changed = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self._base_dpi = 96.0  # Windows 기준 DPI
        self._qhd_dpi = 109.0  # QHD(2560x1440) 기준 DPI  
        self._fhd_dpi = 96.0   # FHD(1920x1080) 기준 DPI
        self._current_scale = 1.0
        self._user_scale_factor = 1.0
        self._auto_scaling_enabled = True
        
        self.settings_file = os.path.join('save', 'ui_scaling_settings.json')
        self.load_settings()
        self.calculate_scale_factor()
    
    def calculate_scale_factor(self):
        """현재 환경에 맞는 스케일 팩터 계산"""
        if not self._auto_scaling_enabled:
            self._current_scale = self._user_scale_factor
            return
            
        app = QApplication.instance()
        if not app:
            self._current_scale = 1.0
            return
            
        # 주 화면의 DPI 정보 가져오기
        primary_screen = app.primaryScreen()
        if not primary_screen:
            self._current_scale = 1.0
            return
            
        # 물리적 DPI와 논리적 DPI 모두 고려
        physical_dpi = primary_screen.physicalDotsPerInch()
        logical_dpi = primary_screen.logicalDotsPerInch()
        
        # 해상도 정보
        geometry = primary_screen.geometry()
        width = geometry.width()
        height = geometry.height()
        
        # DPI 기반 기본 스케일 계산
        dpi_scale = physical_dpi / self._base_dpi
        
        # 해상도별 추가 조정
        resolution_scale = self._get_resolution_scale_factor(width, height)
        
        # 최종 스케일 팩터 (사용자 설정 반영)
        base_scale = min(dpi_scale, resolution_scale)  # 더 작은 값 선택
        self._current_scale = base_scale * self._user_scale_factor
        
        # 스케일 팩터 범위 제한 (0.5 ~ 2.0)
        self._current_scale = max(0.5, min(2.0, self._current_scale))
        
        print(f"스케일링 정보:")
        print(f"  해상도: {width}x{height}")
        print(f"  물리적 DPI: {physical_dpi:.1f}")
        print(f"  논리적 DPI: {logical_dpi:.1f}")
        print(f"  DPI 스케일: {dpi_scale:.2f}")
        print(f"  해상도 스케일: {resolution_scale:.2f}")
        print(f"  사용자 스케일: {self._user_scale_factor:.2f}")
        print(f"  최종 스케일: {self._current_scale:.2f}")
    
    def _get_resolution_scale_factor(self, width, height):
        """해상도에 따른 스케일 팩터 조정"""
        # 기준 해상도별 권장 스케일 팩터
        resolution_scales = {
            # (width, height): scale_factor
            (3840, 2160): 1.5,   # 4K UHD
            (2560, 1440): 1.0,   # QHD (기준)
            (1920, 1080): 0.8,   # FHD
            (1680, 1050): 0.75,  # WSXGA+
            (1600, 900): 0.7,    # HD+
            (1366, 768): 0.65,   # WXGA
            (1280, 1024): 0.6,   # SXGA
            (1280, 720): 0.6,    # HD
        }
        
        # 정확히 일치하는 해상도가 있으면 사용
        if (width, height) in resolution_scales:
            return resolution_scales[(width, height)]
        
        # 비슷한 해상도 찾기 (픽셀 수 기준)
        current_pixels = width * height
        closest_scale = 1.0
        min_diff = float('inf')
        
        for (res_width, res_height), scale in resolution_scales.items():
            res_pixels = res_width * res_height
            diff = abs(current_pixels - res_pixels)
            if diff < min_diff:
                min_diff = diff
                closest_scale = scale
        
        return closest_scale
    
    def get_scale_factor(self):
        """현재 스케일 팩터 반환"""
        return self._current_scale
    
    def get_scaled_size(self, base_size):
        """기본 크기에 스케일 팩터 적용"""
        return int(base_size * self._current_scale)
    
    def get_scaled_font_size(self, base_font_size):
        """폰트 크기에 스케일 팩터 적용"""
        scaled_size = int(base_font_size * self._current_scale)
        return max(8, scaled_size)  # 최소 8px
    
    def set_user_scale_factor(self, factor):
        """사용자 정의 스케일 팩터 설정"""
        self._user_scale_factor = max(0.5, min(2.0, factor))
        self.calculate_scale_factor()
        self.save_settings()
        self.scaling_changed.emit(self._current_scale)
    
    def set_auto_scaling_enabled(self, enabled):
        """자동 스케일링 활성화/비활성화"""
        self._auto_scaling_enabled = enabled
        self.calculate_scale_factor()
        self.save_settings()
        self.scaling_changed.emit(self._current_scale)
    
    def is_auto_scaling_enabled(self):
        """자동 스케일링 활성화 상태 반환"""
        return self._auto_scaling_enabled
    
    def get_user_scale_factor(self):
        """사용자 정의 스케일 팩터 반환"""
        return self._user_scale_factor
    
    def save_settings(self):
        """설정 저장"""
        try:
            os.makedirs('save', exist_ok=True)
            settings = {
                'auto_scaling_enabled': self._auto_scaling_enabled,
                'user_scale_factor': self._user_scale_factor
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"UI 스케일링 설정 저장 실패: {e}")
    
    def load_settings(self):
        """설정 로드"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self._auto_scaling_enabled = settings.get('auto_scaling_enabled', True)
                    self._user_scale_factor = settings.get('user_scale_factor', 1.0)
        except Exception as e:
            print(f"UI 스케일링 설정 로드 실패: {e}")
            # 기본값 사용
            self._auto_scaling_enabled = True
            self._user_scale_factor = 1.0
    
    def refresh_scaling(self):
        """스케일링 정보 새로고침 (화면 변경 시 호출)"""
        self.calculate_scale_factor()
        self.scaling_changed.emit(self._current_scale)


# 전역 스케일링 매니저 인스턴스
_scaling_manager = None


def get_scaling_manager():
    """스케일링 매니저 싱글톤 인스턴스 반환"""
    global _scaling_manager
    if _scaling_manager is None:
        _scaling_manager = ScalingManager()
    return _scaling_manager


def get_scaled_size(base_size):
    """편의 함수: 스케일 적용된 크기 반환"""
    return get_scaling_manager().get_scaled_size(base_size)


def get_scaled_font_size(base_font_size):
    """편의 함수: 스케일 적용된 폰트 크기 반환"""
    return get_scaling_manager().get_scaled_font_size(base_font_size)


def get_current_scale_factor():
    """편의 함수: 현재 스케일 팩터 반환"""
    return get_scaling_manager().get_scale_factor()