"""
Linguee翻译服务实现
"""

import requests
from bs4 import BeautifulSoup
from requests.utils import requote_uri
from typing import Dict, Any, Optional, Union, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class LingueeTranslator(TranslatorBase):
    """Linguee翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "linguee_translator"
    SUPPORTED_LANGUAGES = {
        "maltese": "maltese", "english": "english", "german": "german",
        "bulgarian": "bulgarian", "polish": "polish", "portuguese": "portuguese",
        "hungarian": "hungarian", "romanian": "romanian", "russian": "russian",
        "dutch": "dutch", "slovakian": "slovakian", "greek": "greek",
        "slovenian": "slovenian", "danish": "danish", "italian": "italian",
        "spanish": "spanish", "finnish": "finnish", "chinese": "chinese",
        "french": "french", "czech": "czech", "laotian": "laotian",
        "swedish": "swedish", "latvian": "latvian", "estonian": "estonian",
        "japanese": "japanese", "auto": "auto"
    }
    
    # Linguee翻译API端点
    BASE_ENDPOINT = "https://www.linguee.com/"
    
    METADATA = Metadata(
        console_url="https://www.linguee.com/",
        description="Linguee翻译服务实现，提供词典和翻译记忆功能",
        documentation_url="https://www.linguee.com/help",
        short_description="Linguee翻译服务（词典和翻译记忆）",
        usage_documentation="无需API密钥，基于网页抓取，主要用于单词和短语翻译"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Linguee翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Linguee翻译API（实际是网页抓取）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 构建URL
        url = f"{self.BASE_ENDPOINT}{source_lang}-{target_lang}/search/?source={source_lang}&query={text}"
        url = requote_uri(url)
        
        response = self._session.get(url, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("Linguee API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            raise APIError(f"Linguee API错误: {response.status_code} - {response.text}")

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
        element_query = {"class": "dictLink featured"}
        elements = soup.find_all("a", element_query)

        if not elements:
            raise APIError(f"在Linguee中未找到 '{original_text}' 的翻译")

        filtered_elements = []
        for el in elements:
            try:
                pronoun = el.find("span", {"class": "placeholder"}).get_text(strip=True)
            except AttributeError:
                pronoun = ""
            filtered_element = el.get_text(strip=True).replace(pronoun, "").strip()
            if filtered_element:  # 只添加非空结果
                filtered_elements.append(filtered_element)

        if not filtered_elements:
            raise APIError(f"在Linguee中未找到 '{original_text}' 的有效翻译")

        # 返回第一个翻译结果
        return filtered_elements[0]

    def translate_word(self, word: str, return_all: bool = False, **kwargs) -> Union[str, List[str]]:
        """
        使用Linguee翻译单词
        
        Args:
            word: 要翻译的单词
            return_all: 是否返回所有同义词翻译
            **kwargs: 额外参数
            
        Returns:
            翻译结果，单个字符串或字符串列表
        """
        if self._same_source_target() or not word.strip():
            return word

        if len(word) > 50:
            raise APIError("Linguee翻译支持的最大单词长度为50字符")

        # 构建URL
        url = f"{self.BASE_ENDPOINT}{self.config.source_lang}-{self.config.target_lang}/search/?source={self.config.source_lang}&query={word}"
        url = requote_uri(url)
        
        response = self._session.get(url, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("Linguee API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            raise APIError(f"Linguee API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        element_query = {"class": "dictLink featured"}
        elements = soup.find_all("a", element_query)
        response.close()

        if not elements:
            raise APIError(f"在Linguee中未找到 '{word}' 的翻译")

        filtered_elements = []
        for el in elements:
            try:
                pronoun = el.find("span", {"class": "placeholder"}).get_text(strip=True)
            except AttributeError:
                pronoun = ""
            filtered_element = el.get_text(strip=True).replace(pronoun, "").strip()
            if filtered_element:  # 只添加非空结果
                filtered_elements.append(filtered_element)

        if not filtered_elements:
            raise APIError(f"在Linguee中未找到 '{word}' 的有效翻译")

        return filtered_elements if return_all else filtered_elements[0]

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Linguee翻译特殊API方法的引用规范
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
            }
        }