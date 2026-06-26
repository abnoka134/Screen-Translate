import os
import re
import time
import deepl
import ctranslate2
from transformers import NllbTokenizer
_nllb_translator = None
_nllb_tokenizer = None

LANGUAGE_MAP = {
    "Tiếng Việt": "VI",
    "Tiếng Anh": "EN-US",
    "Tiếng Nhật": "JA",
    "Tiếng Trung": "ZH",
    "Tiếng Hàn": "KO",
    "Tiếng Pháp": "FR",
    "Tiếng Đức": "DE"
}

def translate_online(text, api_key, src_lang_name="EN", tgt_lang_name="VI"):

    if not text.strip():
        return ""
        
    try:
        translator = deepl.Translator(api_key)
        
        result = translator.translate_text(
            text, 
            target_lang=tgt_lang_name
        )
        return result.text
        
    except Exception as e:
        print(f"⚠️ Lỗi kết nối DeepL: {str(e)}")
        return ""

def translate_offline(text, src_lang="eng_Latn", tgt_lang="vie_Latn"):
    global _nllb_translator, _nllb_tokenizer
    
    model_path = "models/nllb-200-ct2-converted"
    tokenizer_path = "models/nllb-200-ct2"
    
    if not os.path.exists(model_path):
        return "Lỗi: Thư mục mô hình converted không tồn tại."
    
    if isinstance(text, list):
        text = " ".join(text)
        
    clean_text = str(text).strip().replace("\n", " ").replace("\r", " ")
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    clean_text = re.sub(r'\s+([.,!?;:])', r'\1', clean_text)
    clean_text = re.sub(r'([.,!?;:])(?=[a-zA-Z])', r'\1 ', clean_text)
    
    if not clean_text:
        return "Văn bản đầu vào trống."
        
    try:
        if _nllb_translator is None:
            print("Đang nạp mô hình NLLB-200...")
            _nllb_translator = ctranslate2.Translator(model_path, device="cpu")
            
            _nllb_tokenizer = NllbTokenizer.from_pretrained(
                tokenizer_path,
                src_lang=src_lang,
                tgt_lang=tgt_lang
            )
            
        _nllb_tokenizer.src_lang = src_lang
        _nllb_tokenizer.tgt_lang = tgt_lang
        
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        batch_source_tokens = []
        batch_target_prefixes = []
        
        for sentence in sentences:
            source_ids = _nllb_tokenizer(sentence, return_tensors=None)["input_ids"]
            source_tokens = _nllb_tokenizer.convert_ids_to_tokens(source_ids)
            batch_source_tokens.append(source_tokens)
            batch_target_prefixes.append([tgt_lang])
            
        if not batch_source_tokens:
            return ""

        results = _nllb_translator.translate_batch(
            batch_source_tokens, 
            target_prefix=batch_target_prefixes,
            beam_size=4,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
            max_decoding_length=1024
        )
        
        translated_sentences = []
        for result in results:
            target_tokens = result.hypotheses[0]
            if target_tokens and target_tokens[0] == tgt_lang:
                target_tokens = target_tokens[1:]
                
            sentence_text = _nllb_tokenizer.decode(
                _nllb_tokenizer.convert_tokens_to_ids(target_tokens),
                skip_special_tokens=True
            )
            translated_sentences.append(sentence_text.strip())
            
        return " ".join(translated_sentences)
        
    except Exception as e:
        return f"Lỗi xử lý dịch thuật Offline: {str(e)}"