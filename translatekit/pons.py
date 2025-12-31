"""
Pons翻译服务实现
"""

import requests
from bs4 import BeautifulSoup
from requests.utils import requote_uri
from typing import Dict, Any, Optional, Union, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class PonsTranslator(TranslatorBase):
    """Pons翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "pons_translator"
    SUPPORTED_LANGUAGES = {
        "ar": "arabic", "bg": "bulgarian", "zh-cn": "chinese", "cs": "czech",
        "da": "danish", "nl": "dutch", "en": "english", "fr": "french",
        "de": "german", "el": "greek", "hu": "hungarian", "it": "italian",
        "la": "latin", "no": "norwegian", "pl": "polish", "pt": "portuguese",
        "ru": "russian", "sl": "slovenian", "es": "spanish", "sv": "swedish",
        "tr": "turkish", "elv": "elvish", "auto": "auto"
    }
    
    # Pons翻译API端点
    BASE_ENDPOINT = "https://en.pons.com/translate/"
    
    METADATA = Metadata(
        console_url="https://en.pons.com/",
        description="Pons翻译服务实现，提供词典和翻译功能",
        documentation_url="https://en.pons.com/help/",
        short_description="Pons翻译服务（词典翻译）",
        usage_documentation="无需API密钥，基于网页抓取，主要用于单词和短语翻译"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Pons翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持proxies等
        """
        config = config or self.DEFAULT_CONFIG
        self.proxies = kwargs.get('proxies', None)

        super().__init__(config, **kwargs)

    def validate_config(self):
        """验证配置 - Pons不需要特殊配置验证"""
        # Pons是免费服务，不需要API密钥，仅验证基本配置
        if not self.config.target_lang:
            raise ConfigurationError("目标语言未配置")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Pons翻译API（实际是网页抓取）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 构建URL
        url = f"{self.BASE_ENDPOINT}{source_lang}-{target_lang}/{text}"
        url = requote_uri(url)
        
        response = self.session.get(url, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("Pons API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            raise APIError(f"Pons API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
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
        try:
            elements = soup.find("div", {"class": "result_list"}).findAll("div", {"class": "target"})
        except AttributeError:
            raise APIError(f"在Pons中未找到 '{original_text}' 的翻译")

        if not elements:
            raise APIError(f"在Pons中未找到 '{original_text}' 的翻译")

        filtered_elements = []
        for el in elements:
            temp = []
            for e in el.findAll("a"):
                temp.append(e.get_text())
            translation = " ".join(temp).strip()
            if translation:  # 只添加非空结果
                filtered_elements.append(translation)

        if not filtered_elements:
            raise APIError(f"在Pons中未找到 '{original_text}' 的有效翻译")

        # 过滤掉空字符串和长度小于2的结果
        word_list = [word for word in filtered_elements if word and len(word) > 1]

        if not word_list:
            raise APIError(f"在Pons中未找到 '{original_text}' 的有效翻译")

        return word_list[0]

    def translate_word(self, word: str, return_all: bool = False, **kwargs) -> Union[str, List[str]]:
        """
        使用Pons翻译单词
        
        Args:
            word: 要翻译的单词
            return_all: 是否返回所有同义词翻译
            **kwargs: 额外参数
            
        Returns:
            翻译结果，单个字符串或字符串列表
        """
        if len(word) > 50:
            raise APIError("Pons翻译支持的最大单词长度为50字符")

        if self._same_source_target() or not word.strip():
            return word

        # 构建URL
        url = f"{self.BASE_ENDPOINT}{self.config.source_lang}-{self.config.target_lang}/{word}"
        url = requote_uri(url)
        
        response = self.session.get(url, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("Pons API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            raise APIError(f"Pons API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        response.close()

        try:
            elements = soup.find("div", {"class": "result_list"}).findAll("div", {"class": "target"})
        except AttributeError:
            raise APIError(f"在Pons中未找到 '{word}' 的翻译")

        if not elements:
            raise APIError(f"在Pons中未找到 '{word}' 的翻译")

        filtered_elements = []
        for el in elements:
            temp = []
            for e in el.findAll("a"):
                temp.append(e.get_text())
            translation = " ".join(temp).strip()
            if translation:  # 只添加非空结果
                filtered_elements.append(translation)

        if not filtered_elements:
            raise APIError(f"在Pons中未找到 '{word}' 的有效翻译")

        # 过滤掉空字符串和长度小于2的结果
        word_list = [word for word in filtered_elements if word and len(word) > 1]

        if not word_list:
            raise APIError(f"在Pons中未找到 '{word}' 的有效翻译")

        return word_list if return_all else word_list[0]

    def translate_words(self, words: List[str], **kwargs) -> List[str]:
        """
        批量翻译单词
        
        Args:
            words: 要翻译的单词列表
            
        Returns:
            翻译后的单词列表
        """
        if not words:
            raise APIError("单词列表不能为空")

        translated_words = []
        for word in words:
            translated_words.append(self.translate_word(word=word, **kwargs))
        return translated_words

    def validate_language(self, lang_code: str, lang_type: str = 'target') -> bool:
        """验证语言代码 - 支持语言代码和语言名称两种格式"""
        supported = self.get_supported_languages()
        
        # 如果是'auto'且为源语言，返回True
        if lang_code == 'auto' and lang_type == 'source':
            return True
            
        # 检查是否是语言代码
        for name, code in supported.items():
            if code == lang_code:
                return True
                
        # 检查是否是语言名称
        return lang_code in supported

    def _validate_languages(self, source_lang: str, target_lang: str):
        """验证语言对"""
        if not self.validate_language(source_lang, 'source'):
            raise ValueError(f"不支持的源语言: {source_lang}")
            
        if not self.validate_language(target_lang, 'target'):
            raise ValueError(f"不支持的目标语言: {target_lang}")

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Pons翻译特殊API方法的引用规范
        """
        return {
            "translate_word": {
                "description": "翻译单个单词，可选择返回所有同义词翻译",
                "parameters": {
                    "word": "要翻译的单词",
                    "return_all": "是否返回所有同义词翻译，默认False"
                },
                "return_type": "Union[str, List[str]] 单个翻译结果或翻译结果列表",
                "example": "translator.translate_word('hello', return_all=True)"
            },
            "translate_words": {
                "description": "批量翻译单词列表",
                "parameters": {
                    "words": "要翻译的单词列表"
                },
                "return_type": "List[str] 翻译后的单词列表",
                "example": "translator.translate_words(['hello', 'world'])"
            }
        }