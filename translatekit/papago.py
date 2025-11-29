"""
Papago翻译服务实现
"""

import json
import requests
from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class PapagoTranslator(TranslatorBase):
    """Papago翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "papago_translator"
    SUPPORTED_LANGUAGES = {
        "ko": "Korean", "en": "English", "ja": "Japanese", "zh-CN": "Chinese",
        "zh-TW": "Chinese traditional", "es": "Spanish", "fr": "French",
        "vi": "Vietnamese", "th": "Thai", "id": "Indonesia", "auto": "auto"
    }
    
    # Papago翻译API端点
    BASE_ENDPOINT = "https://openapi.naver.com/v1/papago/n2mt"
    
    METADATA = Metadata(
        console_url="https://developers.naver.com/products/papago/",
        description="Papago翻译服务实现，韩国Naver公司提供的翻译服务",
        documentation_url="https://developers.naver.com/docs/nmt/reference/",
        short_description="Papago翻译服务（Naver）",
        usage_documentation="需要Client ID和Secret Key，支持韩语、英语、日语、中文等多种语言"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Papago翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持client_id, secret_key等
        """
        config = config or self.DEFAULT_CONFIG
        self.client_id = config.api_key.get('papago_client_id', kwargs.get('client_id', ''))
        self.secret_key = config.api_key.get('papago_secret_key', kwargs.get('secret_key', ''))
        self.proxies = kwargs.get('proxies', None)

        # 验证必需的认证信息
        if not self.client_id or not self.secret_key:
            raise ConfigurationError("Papago翻译需要Client ID和Secret Key")

        # 更新配置中的认证信息
        config.api_key['papago_client_id'] = self.client_id
        config.api_key['papago_secret_key'] = self.secret_key

        super().__init__(config, **kwargs)

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.client_id or not self.secret_key:
            raise ConfigurationError("Papago Client ID和Secret Key未配置")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Papago翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        payload = {
            "source": source_lang,
            "target": target_lang,
            "text": text,
        }

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.secret_key,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        response = requests.post(self.BASE_ENDPOINT, headers=headers, data=payload, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code >= 400:
            raise APIError(f"Papago API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if "message" not in response:
            raise APIError("Papago API响应格式错误，缺少message字段")

        msg = response.get("message")
        result = msg.get("result", None)
        if not result:
            raise APIError("Papago API响应中未找到result字段")

        translated_text = result.get("translatedText", "")
        if not translated_text:
            raise APIError("Papago API响应中未找到翻译结果")

        return translated_text

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
        获取Papago翻译特殊API方法的引用规范
        """
        return {
            "get_supported_languages": {
                "description": "获取Papago支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_supported_languages()"
            }
        }