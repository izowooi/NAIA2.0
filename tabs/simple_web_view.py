from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, QStandardPaths, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFrame
from interfaces.base_tab_module import BaseTabModule
from ui.theme import DARK_STYLES, DARK_COLORS
import os
import sys

class SimpleWebViewTabModule(BaseTabModule):
    """API 주소를 홈페이지로 하는 간단한 웹뷰 탭 모듈"""

    def __init__(self):
        super().__init__()
        self.web_view_widget: SimpleWebViewTab = None
        self.api_url = None

    def get_tab_title(self) -> str:
        return "🌐 API 웹뷰"
        
    def get_tab_order(self) -> int:
        return 10  # 다른 탭들보다 뒤에 위치
    
    def get_tab_type(self) -> str:
        return 'dynamic'  # 동적 탭으로 설정
    
    def can_close_tab(self) -> bool:
        return True  # 닫기 가능

    def setup(self, api_url: str, **kwargs):
        """동적 생성 시 API URL을 설정"""
        self.api_url = api_url

    def create_widget(self, parent: QWidget) -> QWidget:
        if self.web_view_widget is None:
            self.web_view_widget = SimpleWebViewTab(parent)
            # API URL이 설정되어 있으면 로드
            if self.api_url:
                QTimer.singleShot(100, lambda: self.web_view_widget.load_url(self.api_url))
        return self.web_view_widget

class SimpleWebViewTab(QWidget):
    """태그 추출 기능이 제거된 간단한 웹뷰 탭"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_web_profile()
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)
        
        # 주소 입력 바
        address_layout = QHBoxLayout()
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("URL을 입력하세요...")
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        
        self.go_button = QPushButton("이동")
        self.go_button.clicked.connect(self.navigate_to_url)
        
        self.back_button = QPushButton("←")
        self.forward_button = QPushButton("→")
        self.refresh_button = QPushButton("⟳")
        
        address_layout.addWidget(self.back_button)
        address_layout.addWidget(self.forward_button)
        address_layout.addWidget(self.refresh_button)
        address_layout.addWidget(self.address_bar)
        address_layout.addWidget(self.go_button)
        main_layout.addLayout(address_layout)
        
        # 웹뷰 생성
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        main_layout.addWidget(self.browser, 1)

        # 버튼 연결
        self.back_button.clicked.connect(self.browser.back)
        self.forward_button.clicked.connect(self.browser.forward)
        self.refresh_button.clicked.connect(self.browser.reload)
        self.browser.urlChanged.connect(self.update_address_bar)
        
        self.update_address_bar(self.browser.url())
        
    def setup_web_profile(self):
        """웹 프로필 설정"""
        try:
            app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            profile_path = os.path.join(app_data_path, "simple_web_profile")
            os.makedirs(profile_path, exist_ok=True)
            
            self.profile = QWebEngineProfile("SimpleWebProfile")
            self.profile.setPersistentStoragePath(profile_path)
            
            # 저장 설정
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
            
            self.page = QWebEnginePage(self.profile)
            
            # 기본 웹 설정
            settings = self.page.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, False)
            
            print("간단한 웹뷰 설정 완료")
            
        except Exception as e:
            print(f"웹뷰 설정 중 오류: {e}")
    
    def navigate_to_url(self):
        """주소창의 URL로 이동"""
        url = self.address_bar.text().strip()
        if not url:
            return
            
        # URL 형식 검증 및 보정
        if not url.startswith(('http://', 'https://')):
            if '.' in url and ' ' not in url:
                url = 'https://' + url
            else:
                url = f'https://www.google.com/search?q={url}'
        
        self.load_url(url)
    
    def update_address_bar(self, qurl):
        """주소 표시줄 업데이트"""
        self.address_bar.setText(qurl.toString())

    def load_url(self, url):
        """URL 로드"""
        if isinstance(url, str):
            qurl = QUrl(url)
        else:
            qurl = url
            
        self.browser.load(qurl)
        self.address_bar.setText(qurl.toString())

def setup_webengine_ssl_fix():
    """WebEngine SSL 및 CSP 에러 해결 설정"""
    flags = [
        # SSL 관련
        '--ignore-ssl-errors',
        '--ignore-certificate-errors',
        '--ignore-certificate-errors-spki-list',
        '--allow-running-insecure-content',
        '--disable-web-security',
        
        # CSP (Content Security Policy) 해결
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-ipc-flooding-protection',
        
        # GPU/WebGL 관련 (에러 억제)
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        
        # 기타 에러 억제
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-default-apps',
        '--no-first-run',
        '--disable-background-networking',
        
        # 로깅 레벨 조정 (에러 메시지 줄이기)
        '--log-level=3',
        '--silent-debugger-extension-api',
    ]
    
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = ' '.join(flags)
    os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
    
    print("WebEngine 고급 설정 완료")

# 강화된 콘솔 출력 필터링
class ErrorFilter:
    """에러 메시지 필터링"""
    def __init__(self):
        self.original_stderr = sys.stderr
        
    def write(self, text):
        ignore_patterns = [
            'ssl_client_socket_impl.cc',
            'Permissions-Policy header',
            'Failed to create WebGPU',
            'font-size:0;color:transparent',
            'cloudflare.com/cdn-cgi',
            'handshake failed',
            'net_error -101',
            'Content Security Policy directive',
            'script-src',
            'unsafe-eval',
            'unsafe-inline',
            'Refused to load the script',
            'Refused to execute inline script',
            'Refused to evaluate a string as JavaScript',
            '[Report Only]'
        ]
        
        if not any(pattern in text for pattern in ignore_patterns):
            self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()

def enable_error_filtering():
    """에러 필터링 활성화"""
    sys.stderr = ErrorFilter()
    print("웹뷰 에러 필터링 활성화")