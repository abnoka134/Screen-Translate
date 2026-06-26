import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import re
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QApplication, QTextEdit
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor
from src.capture import capture_screen_area
from src.config import SUPPORTED_LANGUAGES
from src.core_ocr import extract_text_from_image
from src.translator import translate_online, translate_offline, LANGUAGE_MAP

class TranslationWorker(QThread):

    translation_finished = pyqtSignal(str)
    status_updated = pyqtSignal(str)

    def __init__(self, x, y, w, h, api_key, ocr_langs, nllb_src, nllb_tgt, src_name="Tiếng Việt", tgt_name="Tiếng Anh"):
        super().__init__()
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.api_key = api_key
        self.ocr_langs = ocr_langs
        self.nllb_src = nllb_src
        self.nllb_tgt = nllb_tgt
        
        self.src_name = src_name
        self.tgt_name = tgt_name

    def run(self):
        temp_image_path = "assets/temp_capture.png"
        try:
            self.status_updated.emit("Đang chụp màn hình...")
            os.makedirs("assets", exist_ok=True)
            capture_screen_area(self.x, self.y, self.w, self.h, output_path=temp_image_path)
            
            self.status_updated.emit("Đang bóc tách chữ...")
            extracted_text = extract_text_from_image(temp_image_path, lang_list=self.ocr_langs)
            
            if not extracted_text:
                self.translation_finished.emit("Không tìm thấy văn bản nào trong vùng quét.")
                return
                
            self.status_updated.emit("Đang biên dịch ngôn ngữ...")
            
            if self.nllb_src == "auto":
                has_japanese = bool(re.search(r'[\u3040-\u30ff\u4e00-\u9faf]', extracted_text))
                final_src_lang = "jpn_Jpan" if has_japanese else "eng_Latn"
            else:
                final_src_lang = self.nllb_src
                
            deepl_target_lang = LANGUAGE_MAP.get(self.tgt_name, "EN-US")
            
            online_res = translate_online(
                text=extracted_text, 
                api_key=self.api_key,
                tgt_lang_name=deepl_target_lang
            )
            if not online_res: 
                self.status_updated.emit("Đang kích hoạt NLLB...")
                
                final_translation = translate_offline(
                    extracted_text, 
                    src_lang=self.nllb_src, 
                    tgt_lang=self.nllb_tgt
                )
                print(f"Đã chuyển về Offline thành công.")
            else:
                final_translation = online_res
                
            self.translation_finished.emit(final_translation)
            
        except Exception as worker_err:
            self.status_updated.emit(f"❌ Lỗi luồng chạy ngầm: {str(worker_err)}")
        
        finally:
            if os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                    print("Đã dọn dẹp file ảnh tạm để bảo vệ bộ nhớ.")
                except Exception:
                    pass

class MainControlWindow(QWidget):

    def __init__(self, api_key="YOUR_API_KEY_HERE"):
        super().__init__()
        self.api_key = api_key
        self.selector_window = None
        self.subtitle_window = None
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Dashboard Control")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(520, 90)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e24; color: #ffffff;
                font-family: 'Segoe UI', Arial; font-size: 13px;
            }
            QLabel { font-weight: bold; color: #00FF00; }
            QComboBox {
                background-color: #2a2a35; border: 1px solid #444;
                border-radius: 4px; padding: 4px 8px; color: white; min-width: 100px;
            }
            QComboBox::drop-down { border: none; }
            QPushButton {
                font-weight: bold; border-radius: 4px; 
                padding: 6px 12px; color: white; border: none;
            }
            QPushButton#btn_toggle { background-color: #00aa00; }
            QPushButton#btn_toggle:hover { background-color: #00cc00; }
            QPushButton#btn_translate { background-color: #0066cc; }
            QPushButton#btn_translate:hover { background-color: #0088ff; }
        """)

        layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        
        self.lbl_src = QLabel("Nguồn:")
        self.combo_src = QComboBox()
        self.combo_src.addItems(SUPPORTED_LANGUAGES.keys())
        
        self.lbl_tgt = QLabel("Đích:")
        self.combo_tgt = QComboBox()
        tgt_options = [lang for lang in SUPPORTED_LANGUAGES.keys() if lang != "Tự động nhận diện"]
        self.combo_tgt.addItems(tgt_options)
        
        default_tgt_index = self.combo_tgt.findText("Tiếng Việt")
        if default_tgt_index >= 0:
            self.combo_tgt.setCurrentIndex(default_tgt_index)

        self.btn_toggle_frames = QPushButton("Mở Vùng Quét")
        self.btn_toggle_frames.setObjectName("btn_toggle")
        self.btn_toggle_frames.clicked.connect(self.toggle_helper_windows)

        self.btn_trigger_translate = QPushButton("Dịch Ngay")
        self.btn_trigger_translate.setObjectName("btn_translate")
        self.btn_trigger_translate.clicked.connect(self.start_translation_process)

        control_layout.addWidget(self.lbl_src)
        control_layout.addWidget(self.combo_src)
        control_layout.addWidget(self.lbl_tgt)
        control_layout.addWidget(self.combo_tgt)
        control_layout.addWidget(self.btn_toggle_frames)
        control_layout.addWidget(self.btn_trigger_translate)
        
        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #aaa; font-size: 11px; font-weight: normal;")
        
        layout.addLayout(control_layout)
        layout.addWidget(self.lbl_status)
        self.setLayout(layout)

    def toggle_helper_windows(self):
        if self.selector_window is None or not self.selector_window.isVisible():
            if not self.selector_window:
                self.selector_window = ScreenSelector()
            if not self.subtitle_window:
                self.subtitle_window = SubtitleWindow()
                
            self.selector_window.show()
            self.subtitle_window.hide()
            
            self.btn_toggle_frames.setText("Ẩn Vùng Quét")
            self.btn_toggle_frames.setStyleSheet("background-color: #aa0000;")
        else:
            self.selector_window.hide()
            if self.subtitle_window:
                self.subtitle_window.hide()
            self.btn_toggle_frames.setText("Mở Vùng Quét")
            self.btn_toggle_frames.setStyleSheet("background-color: #00aa00;")

    def start_translation_process(self):
        if not self.selector_window or not self.selector_window.isVisible():
            self.lbl_status.setText("Trạng thái: Chưa bật khung quét!")
            return

        if self.worker and self.worker.isRunning():
            return

        if self.subtitle_window:
            self.subtitle_window.hide()

        x, y, w, h = self.selector_window.get_coordinates()
        current_src = self.combo_src.currentText()
        current_tgt = self.combo_tgt.currentText()
        
        src_config = SUPPORTED_LANGUAGES[current_src]
        tgt_config = SUPPORTED_LANGUAGES[current_tgt]

        self.worker = TranslationWorker(
        x=x, y=y, w=w, h=h, api_key=self.api_key,
        ocr_langs=src_config["ocr"], nllb_src=src_config["nllb"], nllb_tgt=tgt_config["nllb"],
        src_name=current_src,
        tgt_name=current_tgt
    )

        self.worker.status_updated.connect(lambda msg: self.lbl_status.setText(f"Trạng thái: {msg}"))
        self.worker.translation_finished.connect(self.handle_translation_result)
        self.worker.start()

    def handle_translation_result(self, result_text):
        self.lbl_status.setText("Trạng thái: Đã dịch xong")
        if self.subtitle_window:
            self.subtitle_window.update_text(result_text)
            self.subtitle_window.show()

    def closeEvent(self, event):

        print("Đang tiến hành đóng ứng dụng...")
        
        if self.worker and self.worker.isRunning():
            print("Phát hiện luồng dịch đang chạy ngầm, tiến hành hủy bỏ...")
            self.worker.terminate()
            self.worker.wait()
            print("Đã hủy luồng dịch thành công.")

        if self.selector_window:
            self.selector_window.close()
        if self.subtitle_window:
            self.subtitle_window.close()
            
        print("Ứng dụng đã được đóng hoàn toàn.")
        event.accept()
        
class ScreenSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setGeometry(100, 100, 450, 280)

        self.drag_position = QPoint()
        self.is_resizing = False
        self.is_moving = False
        self.border_margin = 12

    def paintEvent(self, event):
        painter = QPainter(self)
        
        painter.fillRect(self.rect(), QColor(0, 0, 0, 2))
        
        pen = QPen(QColor(0, 255, 0), 4)
        painter.setPen(pen)
        rect = QRect(2, 2, self.width() - 4, self.height() - 4)
        painter.drawRect(rect)

    def evaluate_cursor_position(self, pos):
        w, h = self.width(), self.height()
        m = self.border_margin
        
        self.resize_edges = {
            "left": pos.x() < m, 
            "right": pos.x() > w - m,
            "top": pos.y() < m, 
            "bottom": pos.y() > h - m
        }
        
        if (self.resize_edges["left"] and self.resize_edges["top"]) or (self.resize_edges["right"] and self.resize_edges["bottom"]):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif (self.resize_edges["right"] and self.resize_edges["top"]) or (self.resize_edges["left"] and self.resize_edges["bottom"]):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif self.resize_edges["left"] or self.resize_edges["right"]:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif self.resize_edges["top"] or self.resize_edges["bottom"]:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            w, h = self.width(), self.height()
            m = self.border_margin
            
            if pos.x() < m or pos.x() > w - m or pos.y() < m or pos.y() > h - m:
                self.is_resizing = True
            else:
                self.is_moving = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        global_pos = event.globalPosition().toPoint()
        
        if not event.buttons() == Qt.MouseButton.LeftButton:
            self.evaluate_cursor_position(pos)
            return

        if self.is_resizing:
            geo = self.geometry()
            left, top, right, bottom = geo.left(), geo.top(), geo.right(), geo.bottom()
            
            if self.resize_edges["left"]: left = global_pos.x()
            if self.resize_edges["right"]: right = global_pos.x()
            if self.resize_edges["top"]: top = global_pos.y()
            if self.resize_edges["bottom"]: bottom = global_pos.y()
            
            if right - left > 100 and bottom - top > 80:
                self.setGeometry(QRect(QPoint(left, top), QPoint(right, bottom)))
                
        elif self.is_moving:
            self.move(global_pos - self.drag_position)
            
        event.accept()

    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        self.is_moving = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def get_coordinates(self):
    
        geo = self.geometry()
        
        try:
            dpi_ratio = self.screen().devicePixelRatio()
        except Exception:
            dpi_ratio = 1.0
            
        x = int((geo.x() + 4) * dpi_ratio)
        y = int((geo.y() + 4) * dpi_ratio)
        w = int((geo.width() - 8) * dpi_ratio)
        h = int((geo.height() - 8) * dpi_ratio)
        
        return x, y, w, h

class SubtitleWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.setGeometry(200, 750, 650, 110)
        self.drag_position = QPoint()
        
        self.is_resizing = False
        self.is_moving = False
        self.border_margin = 10
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 5, 0)
        top_bar_layout.addStretch()

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 0, 0, 150); color: white;
                font-size: 14px; font-weight: bold; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: rgba(255, 0, 0, 230); }
        """)
        self.btn_close.clicked.connect(self.hide)
        
        top_bar_layout.addWidget(self.btn_close)
        main_layout.addLayout(top_bar_layout)
        
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setMouseTracking(False) 
        
        self.text_display.setStyleSheet("""
            QTextEdit {
                color: #FFFFFF; font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px; font-weight: bold;
                background-color: rgba(15, 15, 20, 220); 
                border-radius: 6px; padding: 10px; 
                border: 1px solid rgba(0, 255, 0, 120);
            }
        """)
        self.text_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_layout.addWidget(self.text_display)
        self.setLayout(main_layout)
        self.is_resizing = False
        self.is_moving = False
        self.border_margin = 10  
        self.resize_edges = {"left": False, "right": False, "top": False, "bottom": False}

    def evaluate_cursor_position(self, pos):
        w, h = self.width(), self.height()
        m = self.border_margin
        
        self.resize_edges = {
            "left": pos.x() < m, 
            "right": pos.x() > w - m,
            "top": pos.y() < m, 
            "bottom": pos.y() > h - m
        }
        
        if (self.resize_edges["left"] and self.resize_edges["top"]) or (self.resize_edges["right"] and self.resize_edges["bottom"]):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif (self.resize_edges["right"] and self.resize_edges["top"]) or (self.resize_edges["left"] and self.resize_edges["bottom"]):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif self.resize_edges["left"] or self.resize_edges["right"]:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif self.resize_edges["top"] or self.resize_edges["bottom"]:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            w, h = self.width(), self.height()
            m = self.border_margin
            
            if pos.x() < m or pos.x() > w - m or pos.y() < m or pos.y() > h - m:
                self.is_resizing = True
            else:
                self.is_moving = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        global_pos = event.globalPosition().toPoint()
        
        if not event.buttons() == Qt.MouseButton.LeftButton:
            self.evaluate_cursor_position(pos)
            return

        if self.is_resizing:
            geo = self.geometry()
            left, top, right, bottom = geo.left(), geo.top(), geo.right(), geo.bottom()
            
            if self.resize_edges["left"]: left = global_pos.x()
            if self.resize_edges["right"]: right = global_pos.x()
            if self.resize_edges["top"]: top = global_pos.y()
            if self.resize_edges["bottom"]: bottom = global_pos.y()
            
            if right - left > 200 and bottom - top > 60:
                self.setGeometry(QRect(QPoint(left, top), QPoint(right, bottom)))
                
        elif self.is_moving:
            self.move(global_pos - self.drag_position)
            
        event.accept()

    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        self.is_moving = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        event.accept()

    def update_text(self, new_text):
        self.text_display.setPlainText(new_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainControlWindow()
    window.show()
    sys.exit(app.exec())