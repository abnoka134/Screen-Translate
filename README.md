Hướng dẫn cài đặt
1. Yêu cầu
- Python 3.8+
2. Thiết lập môi trường
```
# Clone dự án
git clone [https://github.com/abnoka134/Screen-Translate.git](https://github.com/abnoka134/Screen-Translate.git)
cd Screen-Translate
```
Tạo môi trường ảo
`python -m venv env`
Kích hoạt môi trường
`env\Scripts\activate`
Cài đặt thư viện
`pip install -r requirements.txt`
3. Tải mô hình NLLB-200
Dự án sử dụng mô hình NLLB-200 từ Meta. Mô hình sẽ được tự động tải về máy khi chạy chương trình lần đầu tiên.
Sử dụng đoạn mã Python sau:
```
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
```
4. Chạy chương trình
Để chạy chương trình, sử dụng đoạn mã:
`python main.py`
