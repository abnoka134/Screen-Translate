import easyocr
import os
import re

_ocr_readers = {}

def extract_text_from_image(image_path, lang_list=["en"]):
    global _ocr_readers
    
    if not lang_list:
        lang_list = ["en"]
        
    cache_key = tuple(sorted(lang_list))
    
    if cache_key not in _ocr_readers:
        try:
            print(f"Đang tải cấu hình mô hình OCR: {lang_list}...")
            _ocr_readers[cache_key] = easyocr.Reader(lang_list, gpu=True)
        except Exception as e:
            print(f"Lỗi khởi tạo OCR cấu hình riêng, tự động nạp fallback ['en']: {str(e)}")
            _ocr_readers[cache_key] = easyocr.Reader(["en"], gpu=True)
            
    reader = _ocr_readers[cache_key]
    
    if not os.path.exists(image_path):
        print(f"Không tìm thấy file ảnh mục tiêu: {image_path}")
        return ""
        
    results = reader.readtext(image_path, detail=0, paragraph=True)
    if not results:
        return ""
        
    extracted_lines = [res[1] for res in results]
    raw_text = " ".join(results)
    
    is_japanese_or_chinese = bool(re.search(r'[\u3040-\u30ff\u4e00-\u9faf]', raw_text))
    
    if is_japanese_or_chinese:
        raw_text = raw_text.replace(" ", "")
    else:
        raw_text = re.sub(r'\s+', ' ', raw_text)
        
    print(f"Văn bản gốc: {raw_text}")
    return raw_text.strip()