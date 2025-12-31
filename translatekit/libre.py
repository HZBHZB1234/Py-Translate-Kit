"""
Libre翻译服务实现
"""

import warnings
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
    
    DEFAULT_API_KEY = {
        "api_key": "",
        "use_free_api": True,
        "custom_url": None
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "Libre翻译API密钥",
            "type": "string",
            "required": False,
            "description": "Libre翻译API密钥"
        },
        {
            "id": "use_free_api",
            "name": "使用免费API",
            "type": "boolean",
            "required": False,
            "description": "是否使用免费API"
        },
        {
            "id": "custom_url",
            "name": "自定义URL",
            "type": "string",
            "required": False,
            "description": "Libre翻译API的URL"
        }
    ]
    
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
        super().__init__(config, **kwargs)
        try:
            self.SUPPORTED_LANGUAGES = self.get_supported_languages()
        except Exception as e:
            warnings.warn(f"获取支持的语言列表失败，使用默认列表: {e}", RuntimeWarning)
    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.use_free_api and not self.api_key:
            raise ConfigurationError("Libre翻译实例需要API密钥")

    def _update_inner_config(self):
        super()._update_inner_config()
        
        # 如果提供了自定义URL，更新BASE_ENDPOINT
        if self.custom_url:
            self.BASE_ENDPOINT = self.custom_url


    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
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
        response = self.session.post(url, params=params, proxies=self.proxies, timeout=self.config.timeout)

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

            response = self.session.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
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

        response = self.session.post(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
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

            response = self.session.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
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