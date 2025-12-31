"""
Tencent翻译服务实现
"""

import base64
import hashlib
import hmac
import time
import random
import requests
from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class TencentTranslator(TranslatorBase):
    """Tencent翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "tencent_translator"
    SUPPORTED_LANGUAGES = {
        "ar": "arabic", "zh": "chinese (simplified)", "zh-TW": "chinese (traditional)",
        "en": "english", "fr": "french", "de": "german", "hi": "hindi",
        "id": "indonesian", "ja": "japanese", "ko": "korean", "ms": "malay",
        "pt": "portuguese", "ru": "russian", "es": "spanish", "th": "thai",
        "tr": "turkish", "vi": "vietnamese","auto": "auto"
    }
    
    # Tencent翻译API端点
    BASE_ENDPOINT = "https://tmt.tencentcloudapi.com"
    
    DEFAULT_API_KEY = {
        "ecret_id": "",
        "secret_key": "",
        "project_id": 0,
        "region": "ap-beijing"
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "secret_id",
            "name": "Secret ID",
            "description": "腾讯云API密钥Secret ID",
            "required": True,
            "type": "string"
        },
        {
            "id": "secret_key",
            "name": "Secret Key",
            "description": "腾讯云API密钥Secret Key",
            "required": True,
            "type": "string"
        },
        {
            "id": "project_id",
            "name": "项目ID",
            "description": "腾讯云翻译项目ID",
            "required": False,
            "type": "number"
        },
        {
            "id": "region",
            "name": "地区",
            "description": "腾讯云翻译区域",
            "required": False,
            "type": "string"
        }
    ]
    
    METADATA = Metadata(
        console_url="https://cloud.tencent.com/product/tmt",
        description="Tencent翻译服务实现，腾讯云提供的翻译服务",
        documentation_url="https://cloud.tencent.com/document/product/551/15619",
        short_description="Tencent翻译服务（腾讯云）",
        usage_documentation="需要Secret ID和Secret Key，支持多种语言，提供高质量翻译服务"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Tencent翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)

    def _create_signature(self, params: dict) -> str:
        """创建请求签名"""
        # 按字母顺序排序参数
        query_str = "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
        # 构建签名原文
        s = "GET" + self.BASE_ENDPOINT.replace("https://", "") + "/?" + query_str
        # 使用HMAC-SHA1进行加密
        hmac_str = hmac.new(
            self.secret_key.encode("utf8"),
            s.encode("utf8"),
            hashlib.sha1,
        ).digest()
        # 对签名进行Base64编码
        return base64.b64encode(hmac_str).decode("utf8")

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Tencent翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 构建请求参数
        params = {
            "Action": "TextTranslate",
            "Nonce": random.randint(1, 65536),
            "ProjectId": self.project_id,
            "Region": self.region,
            "SecretId": self.secret_id,
            "Source": source_lang,
            "SourceText": text,
            "Target": target_lang,
            "Timestamp": int(time.time()),  # 当前时间戳
            "Version": "2018-03-21",  # API版本
        }

        # 创建签名
        params["Signature"] = self._create_signature(params)

        # 发送请求
        response = self.session.get(self.BASE_ENDPOINT, params=params, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code != 200:
            raise APIError(f"Tencent API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        result = response.json()

        if not result:
            raise APIError("Tencent API响应为空")

        # 检查是否有错误信息
        if "Response" in result and "Error" in result["Response"]:
            error_info = result["Response"]["Error"]
            raise APIError(f"Tencent API错误: {error_info.get('Code', 'Unknown')} - {error_info.get('Message', 'Unknown error')}")

        return result

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if "Response" not in response:
            raise APIError("Tencent API响应格式错误，缺少Response字段")

        target_text = response["Response"].get("TargetText", "")
        if not target_text:
            raise APIError("Tencent API响应中未找到翻译结果")

        return target_text
