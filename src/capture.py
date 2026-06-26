import os
import mss
import mss.tools
from PIL import Image, ImageGrab

def capture_screen_area(x, y, w, h, output_path="assets/temp_capture.png"):

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    x1 = x
    y1 = y
    x2 = x + w
    y2 = y + h
    
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
    screenshot.save(output_path)
    
    print(f"Đã chụp pixel thật: Gốc({x1}, {y1}) -> Rìa({x2}, {y2}) | Kích thước: {w}x{h}")
