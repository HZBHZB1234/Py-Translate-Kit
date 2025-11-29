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
        "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar",
        "armenian": "hy", "assamese": "as", "aymara": "ay", "azerbaijani": "az",
        "bambara": "bm", "basque": "eu", "belarusian": "be", "bengali": "bn",
        "bhojpuri": "bho", "bosnian": "bs", "bulgarian": "bg", "catalan": "ca",
        "cebuano": "ceb", "chichewa": "ny", "chinese (simplified)": "zh-CN",
        "chinese (traditional)": "zh-TW", "corsican": "co", "croatian": "hr",
        "czech": "cs", "danish": "da", "dhivehi": "dv", "dogri": "doi",
        "dutch": "nl", "english": "en", "esperanto": "eo", "estonian": "et",
        "ewe": "ee", "filipino": "tl", "finnish": "fi", "french": "fr",
        "frisian": "fy", "galician": "gl", "georgian": "ka", "german": "de",
        "greek": "el", "guarani": "gn", "gujarati": "gu", "haitian creole": "ht",
        "hausa": "ha", "hawaiian": "haw", "hebrew": "iw", "hindi": "hi",
        "hmong": "hmn", "hungarian": "hu", "icelandic": "is", "igbo": "ig",
        "ilocano": "ilo", "indonesian": "id", "irish": "ga", "italian": "it",
        "japanese": "ja", "javanese": "jw", "kannada": "kn", "kazakh": "kk",
        "khmer": "km", "kinyarwanda": "rw", "konkani": "gom", "korean": "ko",
        "krio": "kri", "kurdish (kurmanji)": "ku", "kurdish (sorani)": "ckb",
        "kyrgyz": "ky", "lao": "lo", "latin": "la", "latvian": "lv",
        "lingala": "ln", "lithuanian": "lt", "luganda": "lg", "luxembourgish": "lb",
        "macedonian": "mk", "maithili": "mai", "malagasy": "mg", "malay": "ms",
        "malayalam": "ml", "maltese": "mt", "maori": "mi", "marathi": "mr",
        "meiteilon (manipuri)": "mni-Mtei", "mizo": "lus", "mongolian": "mn",
        "myanmar": "my", "nepali": "ne", "norwegian": "no", "odia (oriya)": "or",
        "oromo": "om", "pashto": "ps", "persian": "fa", "polish": "pl",
        "portuguese": "pt", "punjabi": "pa", "quechua": "qu", "romanian": "ro",
        "russian": "ru", "samoan": "sm", "sanskrit": "sa", "scots gaelic": "gd",
        "sepedi": "nso", "serbian": "sr", "sesotho": "st", "shona": "sn",
        "sindhi": "sd", "sinhala": "si", "slovak": "sk", "slovenian": "sl",
        "somali": "so", "spanish": "es", "sundanese": "su", "swahili": "sw",
        "swedish": "sv", "tajik": "tg", "tamil": "ta", "tatar": "tt",
        "telugu": "te", "thai": "th", "tigrinya": "ti", "tsonga": "ts",
        "turkish": "tr", "turkmen": "tk", "twi": "ak", "ukrainian": "uk",
        "urdu": "ur", "uyghur": "ug", "uzbek": "uz", "vietnamese": "vi",
        "welsh": "cy", "xhosa": "xh", "yiddish": "yi", "yoruba": "yo",
        "zulu": "zu", "auto": "auto"
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
        # Google翻译不需要API密钥，因此重新设置配置
        config = config or self.DEFAULT_CONFIG
        if not config.api_key:
            config.api_key = {}  # Google翻译不需要API密钥
        
        super().__init__(config, **kwargs)
        
        # 设置代理
        self.proxies = kwargs.get('proxies', None)
        self._alt_element_query = {"class": "result-container"}

    def validate_config(self):
        """验证配置 - Google翻译不需要特殊配置验证"""
        # Google翻译不需要API密钥，但需要验证基本配置
        if not self.config.target_lang:
            raise ConfigurationError("目标语言未配置")

    def validate_language(self, lang_code: str, lang_type: str = 'target') -> bool:
        """验证语言代码 - 支持语言代码和语言名称两种格式"""
        supported = self.get_supported_languages()
        
        # 如果是'auto'且为源语言，返回True
        if lang_code == 'auto' and lang_type == 'source':
            return True
            
        # 检查是否是语言代码（如'en'）
        for name, code in supported.items():
            if code == lang_code:
                return True
                
        # 检查是否是语言名称（如'english'）
        return lang_code in supported

    def _validate_languages(self, source_lang: str, target_lang: str):
        """验证语言对"""
        if not self.validate_language(source_lang, 'source'):
            raise ValueError(f"不支持的源语言: {source_lang}")
            
        if not self.validate_language(target_lang, 'target'):
            raise ValueError(f"不支持的目标语言: {target_lang}")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
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
        response = requests.get(self.BASE_ENDPOINT, params=params, proxies=self.proxies, timeout=self.config.timeout)
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

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Google翻译特殊API方法的引用规范
        """
        return {
            "get_language_support": {
                "description": "获取Google翻译支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_language_support()"
            }
        }

    def get_language_support(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()
