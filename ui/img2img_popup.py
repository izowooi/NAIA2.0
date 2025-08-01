from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PIL import Image
from PIL.ImageQt import ImageQt
from .theme import DARK_STYLES, DARK_COLORS

class Img2ImgPopup(QDialog):
    def __init__(self, pil_image: Image.Image, parent=None):
        super().__init__(parent)
        self.pil_image = pil_image
        
        self.setWindowTitle("이미지 작업 선택")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # 팝업 스타일링
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_COLORS['bg_secondary']};
                border: 1px solid {DARK_COLORS['border_light']};
                border-radius: 8px;
            }}
        """)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. 타이틀(헤더)
        title_label = QLabel("이미지가 감지되었습니다. 수행할 작업을 선택하세요.")
        title_label.setStyleSheet(f"{DARK_STYLES['label_style']} font-weight: 600;")
        main_layout.addWidget(title_label)
        
        # 2. 이미지 미리보기
        image_preview_label = QLabel()
        image_preview_label.setFixedSize(512, 512)
        image_preview_label.setStyleSheet(f"background-color: {DARK_COLORS['bg_primary']}; border-radius: 4px;")
        image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # PIL 이미지를 QPixmap으로 변환하고 리사이즈
        q_image = ImageQt(self.pil_image.convert("RGBA"))
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image_preview_label.setPixmap(scaled_pixmap)
        main_layout.addWidget(image_preview_label)
        
        # 3. 버튼 2개
        img2img_button = QPushButton("Img2Img 탭으로 이미지 전송")
        img2img_button.setFixedSize(512, 40)
        img2img_button.setStyleSheet(DARK_STYLES['primary_button'])
        img2img_button.clicked.connect(self.on_img2img_selected)
        main_layout.addWidget(img2img_button)
        
        inpaint_button = QPushButton("Inpaint 탭으로 이미지 전송")
        inpaint_button.setFixedSize(512, 40)
        inpaint_button.setStyleSheet(DARK_STYLES['secondary_button'])
        inpaint_button.clicked.connect(self.on_inpaint_selected)
        main_layout.addWidget(inpaint_button)
        
        # 4. 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.setFixedSize(512, 40)
        close_button.setStyleSheet(DARK_STYLES['secondary_button'])
        close_button.clicked.connect(self.reject) # 다이얼로그 닫기
        main_layout.addWidget(close_button)

    def on_img2img_selected(self):
        print("Img2Img 탭으로 전송 (구현 필요)")
        # TODO: Img2Img 탭을 열고 self.pil_image를 전달하는 로직
        self.accept()

    def on_inpaint_selected(self):
        print("Inpaint 탭으로 전송 (구현 필요)")
        # TODO: Inpaint 탭(또는 Img2Img 탭의 Inpaint 모드)을 열고 self.pil_image를 전달하는 로직
        self.accept()
