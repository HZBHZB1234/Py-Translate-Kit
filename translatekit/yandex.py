"""
Yandex翻译服务实现
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class YandexTranslator(TranslatorBase):
    """Yandex翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "yandex_translator"
    SUPPORTED_LANGUAGES = {}  # 将在初始化时从API获取
    
    DEFAULT_API_KEY = {
        "api_key": "",
        "folder_id": "",
        "speller": False,
        "format_HTML": False
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "Yandex Cloud API密钥",
            "type": "string",
            "required": True,
            "description": "Yandex Cloud API密钥"
        },
        {
            "id": "folder_id",
            "name": "Yandex Cloud目录ID",
            "type": "string",
            "required": True,
            "description": "Yandex Cloud目录ID"
        },
        {
            "id": "speller",
            "name": "拼写检查",
            "type": "boolean",
            "required": False,
            "description": "是否启用拼写检查，默认为False"
        },
        {
            "id": "format_HTML",
            "name": "HTML格式",
            "type": "boolean",
            "required": False,
            "description": "是否将输入文本作为HTML格式，默认为False"
        }
    ]
    
    # Yandex Cloud 翻译API端点
    BASE_ENDPOINT = "https://translate.api.cloud.yandex.net/translate/v2/{endpoint}"
    
    METADATA = Metadata(
        console_url="https://console.yandex.cloud/",
        description="Yandex Cloud翻译服务实现，提供高质量的机器翻译",
        documentation_url="https://yandex.cloud/ru/docs/translate/",
        short_description="Yandex Cloud翻译服务",
        usage_documentation="需要API密钥，支持多种语言，翻译质量高"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Yandex翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)
        
        # 获取支持的语言列表
        self._supported_languages = self._get_supported_languages_from_api()
        self.SUPPORTED_LANGUAGES = self._supported_languages

    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_supported_languages_from_api(self) -> Dict[str, str]:
        """从Yandex Cloud API获取支持的语言列表"""
        try:
            url = self.BASE_ENDPOINT.format(endpoint="languages")
            params = {"folderId": self.folder_id} if self.folder_id else {}
            
            response = self.session.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 构建语言映射字典
            language_map = {}
            for lang in data.get("languages", []):
                code = lang.get("code")
                name = lang.get("name", code)
                language_map[code] = name
                
            # 添加自动检测支持
            language_map["auto"] = "Auto-detect"
            
            return language_map
        except Exception as e:
            self.logger.warning(f"无法获取Yandex Cloud支持的语言列表，使用默认列表: {e}")
            # 返回一个默认的常见语言列表
            return {
                "auto": "Auto-detect", "en": "English", "ru": "Russian", 
                "de": "German", "fr": "French", "es": "Spanish",
                "it": "Italian", "pl": "Polish", "tr": "Turkish", 
                "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
                "ar": "Arabic", "pt": "Portuguese", "nl": "Dutch",
                "uk": "Ukrainian", "he": "Hebrew", "ro": "Romanian",
                "sv": "Swedish", "hu": "Hungarian", "cs": "Czech"
            }

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Yandex Cloud翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        url = self.BASE_ENDPOINT.format(endpoint="translate")
        
        # 构建请求体
        body = {
            "folderId": self.folder_id,
            "targetLanguageCode": target_lang,
            "texts": [text],
            "speller": self.speller,
            "format": "HTML" if self.format_HTML else "PLAIN_TEXT"
        }
        
        # 如果源语言不是自动检测，添加源语言参数
        if source_lang != "auto":
            body["sourceLanguageCode"] = source_lang
            
        response = self.session.post(
            url,
            headers=self._get_headers(),
            json=body,
            timeout=self.config.timeout
        )

        # 处理HTTP错误状态码
        if response.status_code == 429:
            raise APIError("Yandex Cloud API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"HTTP错误: {response.status_code}")
            except:
                error_msg = f"HTTP错误: {response.status_code}"
            raise APIError(f"Yandex Cloud API错误: {error_msg}")

        result = response.json()
        
        if not result.get("translations"):
            raise APIError("Yandex Cloud API响应中未找到翻译结果")

        return result

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        translations = response.get("translations", [])
        if not translations:
            raise APIError("Yandex Cloud API响应中未找到翻译结果")
            
        return translations[0].get("text", "")

    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            检测到的语言代码
        """
        url = self.BASE_ENDPOINT.format(endpoint="detect")
        
        body = {
            "text": text,
            "format": "PLAIN_TEXT"
        }
        
        if self.folder_id:
            body["folderId"] = self.folder_id

        response = self.session.post(
            url,
            headers=self._get_headers(),
            json=body,
            proxies=self.proxies,
            timeout=self.config.timeout
        )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"HTTP错误: {response.status_code}")
            except:
                error_msg = f"HTTP错误: {response.status_code}"
            raise APIError(f"Yandex Cloud语言检测错误: {error_msg}")

        result = response.json()
        language = result.get("languageCode")
        
        if not language:
            raise APIError("Yandex Cloud语言检测未能识别语言")

        return language

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Yandex Cloud翻译特殊API方法的引用规范
        """
        return {
            "detect_language": {
                "description": "检测输入文本的语言",
                "parameters": {
                    "text": "要检测的文本"
                },
                "return_type": "str 检测到的语言代码",
                "example": "translator.detect_language('Hello world')"
            }
        }