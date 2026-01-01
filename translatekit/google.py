"""
Google翻译服务实现
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class GoogleTranslator(TranslatorBase):
    """Google翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "google_translator"
    SUPPORTED_LANGUAGES = {
        "af": "afrikaans", "sq": "albanian", "am": "amharic", "ar": "arabic",
        "hy": "armenian", "as": "assamese", "ay": "aymara", "az": "azerbaijani",
        "bm": "bambara", "eu": "basque", "be": "belarusian", "bn": "bengali",
        "bho": "bhojpuri", "bs": "bosnian", "bg": "bulgarian", "ca": "catalan",
        "ceb": "cebuano", "ny": "chichewa", "zh-CN": "chinese (simplified)",
        "zh-TW": "chinese (traditional)", "co": "corsican", "hr": "croatian",
        "cs": "czech", "da": "danish", "dv": "dhivehi", "doi": "dogri", "nl": "dutch",
        "en": "english", "eo": "esperanto", "et": "estonian", "ee": "ewe",
        "tl": "filipino", "fi": "finnish", "fr": "french", "fy": "frisian",
        "gl": "galician", "ka": "georgian", "de": "german", "el": "greek",
        "gn": "guarani", "gu": "gujarati", "ht": "haitian creole", "ha": "hausa",
        "haw": "hawaiian", "iw": "hebrew", "hi": "hindi", "hmn": "hmong",
        "hu": "hungarian", "is": "icelandic", "ig": "igbo", "ilo": "ilocano",
        "id": "indonesian", "ga": "irish", "it": "italian", "ja": "japanese",
        "jw": "javanese", "kn": "kannada", "kk": "kazakh", "km": "khmer",
        "rw": "kinyarwanda", "gom": "konkani", "ko": "korean", "kri": "krio",
        "ku": "kurdish (kurmanji)", "ckb": "kurdish (sorani)", "ky": "kyrgyz",
        "lo": "lao", "la": "latin", "lv": "latvian", "ln": "lingala", "lt": "lithuanian",       
        "lg": "luganda", "lb": "luxembourgish", "mk": "macedonian", "mai": "maithili",
        "mg": "malagasy", "ms": "malay", "ml": "malayalam", "mt": "maltese",
        "mi": "maori", "mr": "marathi", "mni-Mtei": "meiteilon (manipuri)", "lus": "mizo",
        "mn": "mongolian", "my": "myanmar", "ne": "nepali", "no": "norwegian",
        "or": "odia (oriya)", "om": "oromo", "ps": "pashto", "fa": "persian",
        "pl": "polish", "pt": "portuguese", "pa": "punjabi", "qu": "quechua",
        "ro": "romanian", "ru": "russian", "sm": "samoan", "sa": "sanskrit",
        "gd": "scots gaelic", "nso": "sepedi", "sr": "serbian", "st": "sesotho",
        "sn": "shona", "sd": "sindhi", "si": "sinhala", "sk": "slovak", "sl": "slovenian",      
        "so": "somali", "es": "spanish", "su": "sundanese", "sw": "swahili",
        "sv": "swedish", "tg": "tajik", "ta": "tamil", "tt": "tatar", "te": "telugu",
        "th": "thai", "ti": "tigrinya", "ts": "tsonga", "tr": "turkish", "tk": "turkmen",       
        "ak": "twi", "uk": "ukrainian", "ur": "urdu", "ug": "uyghur", "uz": "uzbek",
        "vi": "vietnamese", "cy": "welsh", "xh": "xhosa", "yi": "yiddish", "yo": "yoruba",      
        "zu": "zulu","auto": "auto"
    }
    
    # Google翻译API端点
    BASE_ENDPOINT = "https://translate.google.com/m"
    
    METADATA = Metadata(
        console_url="https://translate.google.com/",
        description="Google翻译服务实现，基于网页版Google翻译API",
        documentation_url="https://translate.google.com/intl/en/about/",
        short_description="Google翻译服务",
        usage_documentation="需要网络连接，无需API密钥，基于网页版接口"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Google翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)
        self._alt_element_query = {"class": "result-container"}

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Google翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 验证输入文本
        if not text.strip():
            return {"translated_text": text}
        if len(text) > 5000:
            raise APIError("Google翻译支持的最大文本长度为5000字符")
            
        # 构建请求参数
        params = {
            'sl': source_lang,
            'tl': target_lang,
            'q': text
        }

        # 发送请求
        response = self._session.get(self.BASE_ENDPOINT, params=params, proxies=self.proxies, timeout=self.config.timeout)
        response.raise_for_status()
        
        # 解析响应
        return {
            'response_text': response.text,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'original_text': text
        }

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        response_text = response['response_text']
        original_text = response['original_text']
        source_lang = response['source_lang']
        target_lang = response['target_lang']
        
        soup = BeautifulSoup(response_text, "html.parser")
        
        # 尝试查找主要翻译结果
        element = soup.find("div", {"class": "t0"})
        if not element:
            element = soup.find("div", self._alt_element_query)
            if not element:
                raise APIError(f"无法找到翻译结果: {response_text[:200]}...")
                
        translated_text = element.get_text(strip=True)
        
        # 检查是否返回了原文本（翻译失败的情况）
        if translated_text == original_text.strip():
            # 检查是否是因为字符相同导致的假阳性
            to_translate_alpha = "".join(ch for ch in original_text.strip() if ch.isalnum())
            translated_alpha = "".join(ch for ch in translated_text if ch.isalnum())
            if to_translate_alpha and translated_alpha and to_translate_alpha == translated_alpha:
                # 可能是相同语言的翻译，直接返回原文
                return original_text.strip()
                
        return translated_text

