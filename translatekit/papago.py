"""
Papago翻译服务实现
"""

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
    
    DEFAULT_API_KEY = {
        "client_id": "",
        "secret_key": ""
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "client_id",
            "name": "Client ID",
            "description": "应用注册时分配的Client ID",
            "required": True,
            "type": "string"
        },
        {
            "id": "secret_key",
            "name": "Secret Key",
            "description": "应用注册时分配的Secret Key",
            "required": True,
            "type": "string"
        }
    ]
    
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
        super().__init__(config, **kwargs)

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
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

        response = self.session.post(self.BASE_ENDPOINT, headers=headers, data=payload, proxies=self.proxies, timeout=self.config.timeout)

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

