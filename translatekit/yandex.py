"""
Yandex翻译服务实现
"""

import os
import requests
from typing import Dict, Any, Optional, List
from base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class YandexTranslator(TranslatorBase):
    """Yandex翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "yandex_translator"
    SUPPORTED_LANGUAGES = {}  # 将在初始化时从API获取
    
    # Yandex翻译API端点
    API_VERSION = "1.5"
    BASE_ENDPOINT = "https://translate.yandex.net/api/{version}/tr.json/{endpoint}"
    
    METADATA = Metadata(
        console_url="https://translate.yandex.com/apikeys",
        description="Yandex翻译服务实现，提供高质量的机器翻译",
        documentation_url="https://yandex.com/dev/translate/",
        short_description="Yandex翻译服务",
        usage_documentation="需要API密钥，支持多种语言，翻译质量高"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Yandex翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key等
        """
        config = config or self.DEFAULT_CONFIG
        self.api_key = config.api_key.get('yandex_api_key', kwargs.get('api_key', os.getenv('YANDEX_API_KEY', '')))
        self.proxies = kwargs.get('proxies', None)

        # 从环境变量或配置中获取API密钥
        if not self.api_key:
            raise ConfigurationError("Yandex翻译需要API密钥")

        # 更新配置中的API密钥
        config.api_key['yandex_api_key'] = self.api_key

        super().__init__(config, **kwargs)

        # 获取支持的语言列表
        self._supported_languages = self._get_supported_languages_from_api()
        # 更新类属性以反映实际支持的语言
        self.SUPPORTED_LANGUAGES = self._supported_languages

        # 设置API端点
        self.api_endpoints = {
            "langs": "getLangs",
            "detect": "detect",
            "translate": "translate",
        }

    def _get_supported_languages_from_api(self) -> Dict[str, str]:
        """从Yandex API获取支持的语言列表"""
        try:
            url = self.BASE_ENDPOINT.format(version=self.API_VERSION, endpoint="getLangs")
            params = {"key": self.api_key}
            response = requests.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            directions = data.get("dirs", [])
            # 从方向列表中提取语言代码
            languages = set()
            for direction in directions:
                if "-" in direction:
                    source, target = direction.split("-", 1)
                    languages.add(source)
                    languages.add(target)
            
            # 为每个语言代码创建语言名称映射（简化版，实际中可能需要更完整的映射）
            language_map = {}
            for lang_code in languages:
                # 使用语言代码作为键和值
                language_map[lang_code] = lang_code

            return language_map
        except Exception as e:
            self.logger.warning(f"无法获取Yandex支持的语言列表，使用默认列表: {e}")
            # 返回一个默认的常见语言列表
            return {
                "en": "en", "ru": "ru", "de": "de", "fr": "fr", "es": "es",
                "it": "it", "pl": "pl", "tr": "tr", "zh": "zh", "ja": "ja",
                "ko": "ko", "ar": "ar", "pt": "pt", "nl": "nl", "uk": "uk",
                "he": "he", "ro": "ro", "sv": "sv", "hu": "hu", "cs": "cs",
                "fi": "fi", "da": "da", "no": "no", "sk": "sk", "bg": "bg",
                "hr": "hr", "el": "el", "lt": "lt", "lv": "lv", "et": "et",
                "auto": "auto"
            }

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.api_key:
            raise ConfigurationError("Yandex API密钥未配置")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Yandex翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        params = {
            "text": text,
            "format": "plain",
            "lang": target_lang if source_lang == "auto" else f"{source_lang}-{target_lang}",
            "key": self.api_key,
        }

        url = self.BASE_ENDPOINT.format(version=self.API_VERSION, endpoint="translate")
        response = requests.post(url, data=params, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("Yandex API请求频率超限，请稍后重试")

        response.raise_for_status()
        result = response.json()

        if result.get("code") == 429:
            raise APIError("Yandex API请求频率超限，请稍后重试")
        elif result.get("code") != 200:
            raise APIError(f"Yandex API错误: {result.get('code', 'Unknown error')} - {result.get('message', 'Unknown error')}")
        elif not result.get("text"):
            raise APIError("Yandex API响应中未找到翻译结果")

        return result

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if not response.get("text"):
            raise APIError("Yandex API响应中未找到翻译结果")
        return response["text"][0] if isinstance(response["text"], list) else response["text"]

    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            检测到的语言代码
        """
        params = {
            "text": text,
            "format": "plain",
            "key": self.api_key,
        }

        url = self.BASE_ENDPOINT.format(version=self.API_VERSION, endpoint="detect")
        response = requests.post(url, data=params, proxies=self.proxies, timeout=self.config.timeout)
        response.raise_for_status()
        result = response.json()

        language = result.get("lang")
        status_code = result.get("code", 0)

        if status_code != 200:
            raise APIError(f"Yandex语言检测错误: {status_code}")
        elif not language:
            raise APIError("Yandex语言检测未能识别语言")

        return language

    def get_supported_directions(self) -> List[str]:
        """获取支持的翻译方向"""
        try:
            url = self.BASE_ENDPOINT.format(version=self.API_VERSION, endpoint="getLangs")
            params = {"key": self.api_key}
            response = requests.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("dirs", [])
        except Exception as e:
            self.logger.error(f"获取Yandex支持的翻译方向失败: {e}")
            return []

    def get_language_support(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self._supported_languages.copy()

    def validate_language(self, lang_code: str, lang_type: str = 'target') -> bool:
        """验证语言代码 - 支持语言代码和语言名称两种格式"""
        supported = self.get_language_support()
        
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
        获取Yandex翻译特殊API方法的引用规范
        """
        return {
            "detect_language": {
                "description": "检测输入文本的语言",
                "parameters": {
                    "text": "要检测的文本"
                },
                "return_type": "str 检测到的语言代码",
                "example": "translator.detect_language('Hello world')"
            },
            "get_supported_directions": {
                "description": "获取Yandex支持的翻译方向列表",
                "parameters": {},
                "return_type": "List[str] 支持的翻译方向列表，格式为'source-target'",
                "example": "translator.get_supported_directions()"
            },
            "get_language_support": {
                "description": "获取支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_language_support()"
            }
        }