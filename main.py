import sys
import os
import keyboard
from PyQt6.QtWidgets import QApplication

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.gui import MainControlWindow

def init_global_hotkeys(control_window):
    try:
        keyboard.add_hotkey('ctrl+shift+z', control_window.start_translation_process)
        print("Hệ thống phím tắt 'Ctrl + Shift + Z' đã kích hoạt thành công!")
    except Exception as e:
        print(f"Không thể cài đặt phím tắt hệ thống: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    MY_API_KEY = "bd4a0dc9-050e-4d43-b17f-415cd3c006f4:fx"
    
    controller = MainControlWindow(api_key=MY_API_KEY)
    controller.show()
    
    init_global_hotkeys(controller)
    
    app.aboutToQuit.connect(keyboard.unhook_all)
    
    sys.exit(app.exec())