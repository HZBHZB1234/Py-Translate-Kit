"""
Libre翻译服务实现
"""

import os
import requests
from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class LibreTranslator(TranslatorBase):
    """Libre翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "libre_translator"
    SUPPORTED_LANGUAGES = {
        "en": "English", "ar": "Arabic", "zh": "Chinese", "fr": "French",
        "de": "German", "hi": "Hindi", "id": "Indonesian", "ga": "Irish",
        "it": "Italian", "ja": "Japanese", "ko": "Korean", "pl": "Polish",
        "pt": "Portuguese", "ru": "Russian", "es": "Spanish", "tr": "Turkish",
        "vi": "Vietnamese","auto": "auto"
    }
    
    # Libre翻译API端点
    BASE_ENDPOINT = "https://libretranslate.com/"
    
    METADATA = Metadata(
        console_url="https://libretranslate.com/",
        description="Libre翻译服务实现，开源的翻译API服务",
        documentation_url="https://libretranslate.com/docs/",
        short_description="Libre翻译服务（开源）",
        usage_documentation="需要API密钥（如果使用需要密钥的实例），支持多种语言，开源免费"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Libre翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key, use_free_api, custom_url等
        """
        config = config or self.DEFAULT_CONFIG
        self.api_key = config.api_key.get('libre_api_key', kwargs.get('api_key', ''))
        self.use_free_api = kwargs.get('use_free_api', True)
        self.custom_url = kwargs.get('custom_url', None)
        self.proxies = kwargs.get('proxies', None)

        # 如果使用需要API密钥的实例，则需要API密钥
        if not self.use_free_api and not self.api_key:
            raise ConfigurationError("Libre翻译实例需要API密钥")

        # 如果提供了自定义URL，更新BASE_ENDPOINT
        if self.custom_url:
            self.BASE_ENDPOINT = self.custom_url

        # 更新配置中的API密钥
        if self.api_key:
            config.api_key['libre_api_key'] = self.api_key

        super().__init__(config, **kwargs)

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        # 如果不是使用免费API且没有API密钥，则抛出错误
        if not self.use_free_api and not self.api_key:
            raise ConfigurationError("非免费Libre翻译实例需要API密钥")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Libre翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        translate_endpoint = "translate"
        params = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }

        # 如果需要API密钥，添加到参数中
        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.BASE_ENDPOINT.rstrip('/')}/{translate_endpoint}"
        response = requests.post(url, params=params, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code == 403:
            raise APIError("Libre API访问被拒绝，请检查API密钥是否正确")
        elif response.status_code >= 400:
            raise APIError(f"Libre API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if "translatedText" not in response:
            raise APIError("Libre API响应中未找到翻译结果")
        return response["translatedText"]

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        try:
            # 尝试从API获取支持的语言列表
            url = f"{self.BASE_ENDPOINT.rstrip('/')}/languages"
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key

            response = requests.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
            response.raise_for_status()
            languages_data = response.json()

            # 转换为期望的格式
            languages = {}
            for item in languages_data:
                if "name" in item and "code" in item:
                    languages[item["name"]] = item["code"]
            return languages
        except Exception as e:
            self.logger.warning(f"无法从API获取语言列表，使用默认列表: {e}")
            return self.SUPPORTED_LANGUAGES.copy()

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

    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            包含检测结果的字典
        """
        url = f"{self.BASE_ENDPOINT.rstrip('/')}/detect"
        params = {
            "q": text
        }

        if self.api_key:
            params["api_key"] = self.api_key

        response = requests.post(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()

    def get_api_usage(self) -> Dict[str, Any]:
        """
        获取API使用情况（如果服务器支持的话）
        注意：不是所有LibreTranslate实例都支持此功能
        """
        try:
            url = f"{self.BASE_ENDPOINT.rstrip('/')}/frontend/settings"
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key

            response = requests.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.warning(f"获取API设置失败（可能该实例不支持）: {e}")
            return {}

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Libre翻译特殊API方法的引用规范
        """
        return {
            "detect_language": {
                "description": "检测输入文本的语言",
                "parameters": {
                    "text": "要检测的文本"
                },
                "return_type": "Dict[str, Any] 检测结果字典，包含语言代码和置信度",
                "example": "translator.detect_language('Hello world')"
            },
            "get_api_usage": {
                "description": "获取API使用情况和设置信息（如果服务器支持）",
                "parameters": {},
                "return_type": "Dict[str, Any] API设置和使用情况信息字典",
                "example": "translator.get_api_usage()"
            },
            "get_supported_languages": {
                "description": "获取Libre支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_supported_languages()"
            }
        }