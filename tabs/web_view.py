from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, QStandardPaths, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QTextEdit, QFrame
from interfaces.base_tab_module import BaseTabModule
from ui.theme import DARK_STYLES, DARK_COLORS
import os
import sys
import re
import json

class BrowserTabModule(BaseTabModule):
    """'Danbooru' 브라우저 탭을 위한 모듈"""
    generate_with_image_requested = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.browser_widget: BrowserTab = None

    def get_tab_title(self) -> str:
        return "📦 Danbooru"
        
    def get_tab_order(self) -> int:
        return 2

    def create_widget(self, parent: QWidget) -> QWidget:
        if self.browser_widget is None:
            self.browser_widget = BrowserTab(parent)
            self.browser_widget.generate_prompt_requested.connect(self.instant_generation_requested)
            self.browser_widget.generate_with_image_requested.connect(self.generate_with_image_requested)
            # ✅ URL 로드를 위젯 생성 직후가 아닌 약간 지연해서 실행
            QTimer.singleShot(100, lambda: self.browser_widget.load_url("https://danbooru.donmai.us/"))
        return self.browser_widget

class BrowserTab(QWidget):
    # 태그 추출 완료 시그널
    generate_prompt_requested = pyqtSignal(dict)
    generate_with_image_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # ✅ 순서 변경: 프로필 설정을 UI 초기화보다 먼저
        self.setup_selective_storage()
        self.init_ui()
        self.characteristic = self._load_list_from_file()
        self.extracted_tags_data = {}
        
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
        
        # ✅ 웹뷰 생성 시점 변경: 프로필이 이미 설정된 상태에서 생성
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)  # 이미 생성된 페이지 설정
        main_layout.addWidget(self.browser, 1)

        # --- 하단 패널 ---
        bottom_panel = QFrame()
        bottom_panel_layout = QVBoxLayout(bottom_panel)
        bottom_panel_layout.setContentsMargins(0, 8, 0, 0)

        # 태그 추출 결과 표시 영역 (기본 숨김)
        self.tags_display = QTextEdit()
        self.tags_display.setFixedHeight(150)
        self.tags_display.setReadOnly(True)
        self.tags_display.setStyleSheet(f"{DARK_STYLES['compact_textedit']} font-size: 16px;")
        self.tags_display.setPlaceholderText("Danbooru 페이지에서 '📝 태그 추출' 버튼을 클릭하세요...")
        self.tags_display.setVisible(False)
        bottom_panel_layout.addWidget(self.tags_display)

        # 하단 버튼 레이아웃 (항상 보임)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.extract_tags_button = QPushButton("📝 태그 추출")
        self.extract_tags_button.clicked.connect(self.extract_danbooru_tags)
        
        self.generate_prompt_button = QPushButton("프롬프트 생성")
        self.generate_prompt_button.setStyleSheet(f"{DARK_STYLES['primary_button']} background-color: {DARK_COLORS['accent_blue']};")
        self.generate_prompt_button.clicked.connect(self._on_generate_prompt_clicked)
        self.generate_prompt_button.setVisible(False)

        self.generate_with_image_button = QPushButton("프롬프트+이미지 생성")
        self.generate_with_image_button.setStyleSheet(f"{DARK_STYLES['primary_button']} background-color: {DARK_COLORS['warning']};")
        self.generate_with_image_button.clicked.connect(self._on_generate_with_image_clicked)
        self.generate_with_image_button.setVisible(False)
        
        self.close_button = QPushButton("닫기")
        self.close_button.setStyleSheet(DARK_STYLES['secondary_button'])
        self.close_button.clicked.connect(self._hide_generation_widgets)

        button_layout.addWidget(self.extract_tags_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.generate_prompt_button)
        button_layout.addWidget(self.generate_with_image_button)
        button_layout.addWidget(self.close_button)

        bottom_panel_layout.addLayout(button_layout)
        main_layout.addWidget(bottom_panel)

        self.back_button.clicked.connect(self.browser.back)
        self.forward_button.clicked.connect(self.browser.forward)
        self.refresh_button.clicked.connect(self.browser.reload)
        self.browser.urlChanged.connect(self.update_address_bar)
        
        self.update_address_bar(self.browser.url())
        
    def setup_selective_storage(self):
        """Danbooru 로그인 정보만 저장하는 선택적 스토리지 설정"""
        try:
            # ✅ 프로필과 페이지를 먼저 생성
            app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            profile_path = os.path.join(app_data_path, "browser_profile")
            os.makedirs(profile_path, exist_ok=True)
            
            self.profile = QWebEngineProfile("DanbooruOnlyProfile")
            self.profile.setPersistentStoragePath(profile_path)
            
            # 저장 설정
            self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
            
            # ✅ 페이지를 미리 생성해서 인스턴스 변수로 저장
            self.page = QWebEnginePage(self.profile)
            
            # 기본 웹 설정
            settings = self.page.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, False)
            
            print("Danbooru 브라우저 설정 완료")
            
        except Exception as e:
            print(f"브라우저 설정 중 오류: {e}")
    
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
        self.address_bar.setText(qurl.toString())
        
        url_str = qurl.toString()
        pattern = r'danbooru\.donmai\.us/posts/(\d+)'
        is_danbooru_post = bool(re.search(pattern, url_str))
        
        self.extract_tags_button.setEnabled(is_danbooru_post)
        
        # ▼▼▼▼▼ [수정] 버튼 스타일을 상태에 따라 명확하게 분리 ▼▼▼▼▼
        if is_danbooru_post:
            # 활성화 상태 (녹색)
            self.extract_tags_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DARK_COLORS['success']};
                    border: 1px solid {DARK_COLORS['border']};
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: 500;
                    color: {DARK_COLORS['text_primary']};
                    font-size: 20px;
                }}
                QPushButton:hover {{ background-color: #5CBF60; }}
            """)
        else:
            self._hide_generation_widgets()
            self.extract_tags_button.setStyleSheet(DARK_STYLES['secondary_button'])

    def load_url(self, url):
        """URL 로드"""
        if isinstance(url, str):
            qurl = QUrl(url)
        else:
            qurl = url
            
        self.browser.load(qurl)
        self.address_bar.setText(qurl.toString())
    
    def extract_danbooru_tags(self):
        """현재 Danbooru 페이지에서 태그 정보 추출"""
        current_url = self.browser.url().toString()
        
        # URL에서 ID 추출
        if 'danbooru.donmai.us/posts/' not in current_url:
            self.tags_display.setText("❌ Danbooru 포스트 페이지가 아닙니다.")
            self.tags_display.show()
            return
        
        # JavaScript로 페이지 HTML과 URL 가져오기
        js_code = """
        (function() {
            const result = {
                url: window.location.href,
                html: document.documentElement.outerHTML
            };
            return result;
        })();
        """
        
        self.page.runJavaScript(js_code, self.process_page_data)
    
    def process_page_data(self, page_data):
        """JavaScript에서 받은 페이지 데이터 처리"""
        if not page_data:
            self.tags_display.setText("❌ 페이지 데이터를 가져올 수 없습니다.")
            return
        
        try:
            # URL에서 ID 추출
            url = page_data['url']
            pattern = r'danbooru\.donmai\.us/posts/(\d+)'
            match = re.search(pattern, url)
            
            if match:
                post_id = int(match.group(1))
            else:
                post_id = None
                
            if not post_id:
                self.tags_display.setText("❌ 포스트 ID를 찾을 수 없습니다.")
                return
            
            # HTML에서 태그 추출
            html = page_data['html']
            tags_data = self.parse_danbooru_tags(html, post_id)
            
            # ✅ 핵심 수정: 추출된 태그 데이터를 인스턴스 변수에 저장
            self.extracted_tags_data = tags_data
            
            # 결과 표시
            self.display_extracted_tags(tags_data)
            
        except Exception as e:
            self.tags_display.setText(f"❌ 태그 추출 중 오류 발생: {str(e)}")
    
    def parse_danbooru_tags(self, html, post_id):
        """HTML에서 Danbooru 태그 정보 파싱"""
        tags_data = {
            'id': post_id,
            'artist': [],
            'copyright': [],
            'character': [],
            'general': [],
            'meta': []
        }
        
        # 각 태그 카테고리별로 추출
        categories = {
            'artist': r'<ul class="artist-tag-list">(.*?)</ul>',
            'copyright': r'<ul class="copyright-tag-list">(.*?)</ul>',
            'character': r'<ul class="character-tag-list">(.*?)</ul>',
            'general': r'<ul class="general-tag-list">(.*?)</ul>',
            'meta': r'<ul class="meta-tag-list">(.*?)</ul>'
        }
        
        for category, pattern in categories.items():
            # 해당 카테고리의 ul 태그 내용 찾기
            ul_match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if ul_match:
                ul_content = ul_match.group(1)
                
                # data-tag-name 속성 값들 추출
                tag_pattern = r'data-tag-name="([^"]*)"'
                tag_matches = re.findall(tag_pattern, ul_content)
                
                # HTML 엔티티 디코딩 및 정리
                for tag in tag_matches:
                    # HTML 엔티티 디코딩
                    tag = tag.replace('&amp;', '&')
                    tag = tag.replace('&lt;', '<')
                    tag = tag.replace('&gt;', '>')
                    tag = tag.replace('&quot;', '"')
                    tag = tag.replace('&#39;', "'")
                    
                    if tag and tag not in tags_data[category]:
                        tags_data[category].append(tag)
        
        return tags_data
    
    def display_extracted_tags(self, tags_data):
        """추출된 태그를 UI에 표시"""
        result_text = ""
        cs = tags_data.get('character', [])
        gs = tags_data.get('general', [])
        cs = [tag.replace("_", " ") for tag in cs]
        gs = [tag.replace("_", " ") for tag in gs]
        tags_to_move = [tag for tag in gs if tag in self.characteristic]
        for tag in tags_to_move:
            cs.append(tag)
            gs.remove(tag)
        cs_str = ', '.join(cs)
        gs_str = ', '.join(gs)
        result_text = f"CHARACTER : {cs_str}\n\nGENERAL : {gs_str}"
        
        self.tags_display.setText(result_text)
        self._show_generation_widgets()
        print("🎯 Danbooru 태그 추출 및 표시 완료")

    def _load_list_from_file(self):
        """지정된 파일에서 한 줄에 하나씩 있는 태그를 읽어 리스트로 반환합니다."""
        file_path = os.path.join('data', 'characteristic_list.txt')
        
        if not os.path.exists(file_path):
            print(f"⚠️ 필터 파일 없음: {file_path}")
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 비어있지 않은 라인만 읽어서 앞뒤 공백 제거 후 리스트에 추가
                tags = [line.strip() for line in f if line.strip()]
            return tags
        except Exception as e:
            print(f"❌ 필터 파일 로드 오류 : {e}")
            return []

    def _show_generation_widgets(self):
        """태그 표시창과 생성 버튼들을 보여줍니다."""
        self.tags_display.setVisible(True)
        self.generate_prompt_button.setVisible(True)
        self.generate_with_image_button.setVisible(True)

    def _hide_generation_widgets(self):
        """태그 표시창과 생성 버튼들을 숨깁니다."""
        self.tags_display.setVisible(False)
        self.generate_prompt_button.setVisible(False)
        self.generate_with_image_button.setVisible(False)

    def _on_generate_prompt_clicked(self):
        """프롬프트 생성 버튼 클릭 시 호출"""
        if self.extracted_tags_data:
            print(f"🚀 프롬프트 생성 시그널 발송: {self.extracted_tags_data}")
            self.generate_prompt_requested.emit(self.extracted_tags_data)
        else:
            print("❌ 추출된 태그 데이터가 없습니다.")

    def _on_generate_with_image_clicked(self):
        """프롬프트+이미지 생성 버튼 클릭 시 호출"""
        if self.extracted_tags_data:
            print(f"🚀 프롬프트+이미지 생성 시그널 발송: {self.extracted_tags_data}")
            self.generate_with_image_requested.emit(self.extracted_tags_data)
        else:
            print("❌ 추출된 태그 데이터가 없습니다.")

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
    
    print("WebEngine 고급 설정 완료 (CSP 포함)")

# 강화된 콘솔 출력 필터링
class ErrorFilter:
    """에러 메시지 필터링"""
    def __init__(self):
        self.original_stderr = sys.stderr
        
    def write(self, text):
        # CSP 관련 에러 패턴 추가
        ignore_patterns = [
            'ssl_client_socket_impl.cc',
            'Permissions-Policy header',
            'Failed to create WebGPU',
            'font-size:0;color:transparent',
            'cloudflare.com/cdn-cgi',
            'handshake failed',
            'net_error -101',
            # CSP 관련 패턴들 추가
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
    print("브라우저 에러 필터링 활성화 (CSP 포함)")