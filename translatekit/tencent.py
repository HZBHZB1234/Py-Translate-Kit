"""
Tencent翻译服务实现
"""

import base64
import hashlib
import hmac
import time
import os
import requests
from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class TencentTranslator(TranslatorBase):
    """Tencent翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "tencent_translator"
    SUPPORTED_LANGUAGES = {
        "arabic": "ar", "chinese (simplified)": "zh", "chinese (traditional)": "zh-TW",
        "english": "en", "french": "fr", "german": "de", "hindi": "hi",
        "indonesian": "id", "japanese": "ja", "korean": "ko", "malay": "ms",
        "portuguese": "pt", "russian": "ru", "spanish": "es", "thai": "th",
        "turkish": "tr", "vietnamese": "vi", "auto": "auto"
    }
    
    # Tencent翻译API端点
    BASE_ENDPOINT = "https://tmt.tencentcloudapi.com"
    
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
            **kwargs: 额外配置参数，支持secret_id, secret_key等
        """
        config = config or self.DEFAULT_CONFIG
        self.secret_id = config.api_key.get('tencent_secret_id', kwargs.get('secret_id', os.getenv('TENCENT_SECRET_ID', '')))
        self.secret_key = config.api_key.get('tencent_secret_key', kwargs.get('secret_key', os.getenv('TENCENT_SECRET_KEY', '')))
        self.proxies = kwargs.get('proxies', None)

        # 验证必需的认证信息
        if not self.secret_id:
            raise ConfigurationError("Tencent翻译需要Secret ID，获取地址: https://console.cloud.tencent.com/capi")
        if not self.secret_key:
            raise ConfigurationError("Tencent翻译需要Secret Key")

        # 更新配置中的认证信息
        config.api_key['tencent_secret_id'] = self.secret_id
        config.api_key['tencent_secret_key'] = self.secret_key

        super().__init__(config, **kwargs)

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.secret_id:
            raise ConfigurationError("Tencent Secret ID未配置")
        if not self.secret_key:
            raise ConfigurationError("Tencent Secret Key未配置")

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

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
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
            "Nonce": 11886,  # 随机正整数，实际应用中应该生成随机数
            "ProjectId": 0,   # 默认项目ID
            "Region": kwargs.get("region", "ap-beijing"),  # 区域，默认北京
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
        response = requests.get(self.BASE_ENDPOINT, params=params, proxies=self.proxies, timeout=self.config.timeout)

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

    def translate_with_region(self, text: str, source_lang: str = None, target_lang: str = None, region: str = "ap-beijing") -> str:
        """
        使用指定区域进行翻译
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            region: 腾讯云服务区域
            
        Returns:
            翻译结果
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang

        self._validate_languages(source_lang, target_lang)

        # 构建请求参数
        params = {
            "Action": "TextTranslate",
            "Nonce": 11886,
            "ProjectId": 0,
            "Region": region,
            "SecretId": self.secret_id,
            "Source": source_lang,
            "SourceText": text,
            "Target": target_lang,
            "Timestamp": int(time.time()),
            "Version": "2018-03-21",
        }

        # 创建签名
        params["Signature"] = self._create_signature(params)

        # 发送请求
        response = requests.get(self.BASE_ENDPOINT, params=params, proxies=self.proxies, timeout=self.config.timeout)

        if response.status_code != 200:
            raise APIError(f"Tencent API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        result = response.json()

        if "Response" in result and "Error" in result["Response"]:
            error_info = result["Response"]["Error"]
            raise APIError(f"Tencent API错误: {error_info.get('Code', 'Unknown')} - {error_info.get('Message', 'Unknown error')}")

        target_text = result["Response"].get("TargetText", "")
        if not target_text:
            raise APIError("Tencent API响应中未找到翻译结果")

        return target_text

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Tencent翻译特殊API方法的引用规范
        """
        return {
            "translate_with_region": {
                "description": "使用指定区域进行翻译，可以选择不同的腾讯云服务区域以优化性能",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（可选，默认使用配置）",
                    "target_lang": "目标语言（可选，默认使用配置）",
                    "region": "腾讯云服务区域，默认为'ap-beijing'"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_region('Hello world', 'en', 'zh', 'ap-shanghai')"
            },
            "get_supported_languages": {
                "description": "获取Tencent支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_supported_languages()"
            }
        }