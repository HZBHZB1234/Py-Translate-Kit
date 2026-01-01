"""
腾讯混元大模型翻译服务实现，基于腾讯云API
"""

import time
import hashlib
import hmac
import json
import urllib.parse
import warnings
import requests
from typing import Dict, Any, List, Optional, Union
from .base import (TranslatorBase, TranslationConfig,
                   APIError, ConfigurationError,
                   Metadata, ConfigWarning, TranslationWarning,)


class TencentHunyuanTranslator(TranslatorBase):
    """腾讯混元大模型翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "tencent_hunyuan_translator"
    SUPPORTED_LANGUAGES = {
        "zh": "简体中文","yue": "粤语","en": "英语","fr": "法语",
        "pt": "葡萄牙语","es": "西班牙语","ja": "日语","tr": "土耳其语",
        "ru": "俄语","ar": "阿拉伯语","ko": "韩语","th": "泰语",
        "it": "意大利语","de": "德语","vi": "越南语","ms": "马来语",
        "id": "印尼语"
    }
    
    # 支持的模型
    SUPPORTED_MODELS = {
        "hunyuan-translation": "混元翻译标准版",
        "hunyuan-translation-lite": "混元翻译轻量版"
    }
    
    # 腾讯云API配置
    API_DOMAIN = "hunyuan.tencentcloudapi.com"
    API_PATH = "/"
    ACTION = "ChatTranslations"
    VERSION = "2023-09-01"
    SIGN_METHOD = "HmacSHA256"
    SIGN_ALGORITHM = "TC3-HMAC-SHA256"
    SERVICE = "hunyuan"
    
    DEFAULT_API_KEY = {
        "secret_id": "",
        "secret_key": "",
        "model": "hunyuan-translation",
        "region": "ap-guangzhou",
        "field": None,
        "reference": None
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "secret_id",
            "name": "腾讯云SecretId",
            "type": "string",
            "required": True,
            "description": "腾讯云API密钥SecretId"
        },
        {
            "id": "secret_key",
            "name": "腾讯云SecretKey",
            "type": "string",
            "required": True,
            "description": "腾讯云API密钥SecretKey"
        },
        {
            "id": "model",
            "name": "翻译模型",
            "type": "string",
            "required": False,
            "description": "翻译模型，可选: hunyuan-translation, hunyuan-translation-lite",
            "default": "hunyuan-translation"
        },
        {
            "id": "region",
            "name": "腾讯云区域",
            "type": "string",
            "required": False,
            "description": "腾讯云区域，例如: ap-guangzhou, ap-shanghai, ap-beijing",
        },
        {
            "id": "field",
            "name": "翻译领域",
            "type": "string",
            "required": False,
            "description": "翻译领域，例如: 游戏剧情",
        },
        {
            "id": "reference",
            "name": "翻译示例",
            "type": "list",
            "required": False,
            "description": "翻译示例，可以放专业术语，例如: [{\"source\": \"HP\", \"target\": \"生命值\"}]，示例数量理应不超过10条",
        }
    ]
    
    metadata = Metadata(
        console_url="https://console.cloud.tencent.com/hunyuan",
        description="腾讯混元大模型翻译服务，支持高质量文本翻译",
        documentation_url="https://cloud.tencent.com/document/product/1729/113395",
        short_description="腾讯混元大模型翻译",
        usage_documentation=""
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化腾讯混元翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持secret_id, secret_key, model等
        """
        super().__init__(config, **kwargs)
        
        self.MIN_REQUEST_INTERVAL = 0.5
        
        # 初始化额外配置
        self.stream = False  # 默认非流式
        self.default_field = None
        
    def validate_config(self):
        super().validate_config()
        if self.model not in self.SUPPORTED_MODELS:
            warnings.warn(f"不支持的翻译模型: {self.model}\n支持的模型列表: {list(self.SUPPORTED_MODELS.keys())}", ConfigWarning)
    
    def validate_language(self, lang_code, lang_type = 'target'):
        supported = self.get_supported_languages()
        
        return lang_code in supported
    
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用腾讯混元翻译API（默认翻译）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            API响应数据
        """
        # 构建请求数据
        payload = self._build_request_payload(text, source_lang, target_lang, **kwargs)
        
        # 生成签名和请求头
        headers = self._generate_tc3_signature(payload)
        
        # 发送请求
        url = f"https://{self.API_DOMAIN}{self.API_PATH}"
        
        try:
            response = self._session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP请求异常: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"，状态码: {e.response.status_code}，响应: {e.response.text[:500]}"
            raise APIError(error_msg)
    
    def _translate_stream(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用腾讯混元翻译API（流式翻译）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            API响应数据
        """
        # 验证语言
        # 构建请求数据，启用流式
        payload = self._build_request_payload(text, source_lang, target_lang, **kwargs)
        payload["Stream"] = True
        
        # 生成签名和请求头
        headers = self._generate_tc3_signature(payload)
        
        # 发送流式请求
        url = f"https://{self.API_DOMAIN}{self.API_PATH}"
        
        try:
            response = self._session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
                stream=True
            )
            response.raise_for_status()
            
            # 解析流式响应
            return self._parse_stream_response(response)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP请求异常: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"，状态码: {e.response.status_code}"
            raise APIError(error_msg)
        finally:
            if 'response' in locals():
                response.close()
    
    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """
        解析腾讯混元API响应
        
        Args:
            response: API响应数据
            **kwargs: 额外参数
            
        Returns:
            翻译结果文本
        """
        # 检查错误
        if "Error" in response:
            error = response["Error"]
            raise APIError(f"API调用失败: 错误码={error.get('Code')}，错误信息={error.get('Message')}")
        
        if "Response" not in response:
            raise APIError(f"响应缺少核心字段Response: {response}")
        
        response_data = response["Response"]
        
        # 检查是否有Choices字段
        if not response_data.get("Choices") or len(response_data["Choices"]) == 0:
            raise APIError(f"响应缺少Choices字段: {response_data}")
        
        # 提取翻译文本
        translated_text = response_data["Choices"][0]["Message"].get("Content", "")
        
        if not translated_text:
            raise APIError(f"译文为空: {response_data}")
        
        return translated_text
    
    def _generate_tc3_signature(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        生成腾讯云TC3-HMAC-SHA256签名
        
        Args:
            payload: 请求体数据
            
        Returns:
            包含签名的请求头
        """
        secret_id = self.config.api_key.get('secret_id', '')
        secret_key = self.config.api_key.get('secret_key', '')
        
        if not secret_id or not secret_key:
            raise ConfigurationError("腾讯云SecretId和SecretKey未配置")
        
        # 1. 生成基础参数
        timestamp = int(time.time())
        nonce = int(time.time() * 1000)
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        # 2. 拼接规范请求串
        http_method = "POST"
        canonical_uri = self.API_PATH
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json\nhost:{self.API_DOMAIN}\n"
        signed_headers = "content-type;host"
        hashed_request_payload = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        canonical_request = (
            f"{http_method}\n{canonical_uri}\n{canonical_querystring}\n"
            f"{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        )
        
        # 3. 生成签名摘要
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        credential_scope = f"{date}/{self.SERVICE}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (
            f"{self.SIGN_ALGORITHM}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        )
        
        # 4. 生成签名密钥
        secret_date = hmac.new(
            f"TC3{secret_key}".encode("utf-8"),
            date.encode("utf-8"),
            hashlib.sha256
        ).digest()
        secret_service = hmac.new(secret_date, self.SERVICE.encode("utf-8"), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
        
        # 5. 计算最终签名
        signature = hmac.new(
            secret_signing,
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # 6. 构建Authorization头
        authorization = (
            f"{self.SIGN_ALGORITHM} "
            f"Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        # 7. 完整请求头
        headers = {
            "Content-Type": "application/json",
            "Host": self.API_DOMAIN,
            "X-TC-Action": self.ACTION,
            "X-TC-Version": self.VERSION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Nonce": str(nonce),
            "X-TC-SignatureMethod": self.SIGN_METHOD,
            "Authorization": authorization
        }
        
        if self.REGION:
            headers["X-TC-Region"] = self.REGION
            
        return headers
    
    def _build_request_payload(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        构建API请求体
        
        Args:
            text: 待翻译文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            请求体数据
        """
        payload = {
            "Model": self.model,
            "Stream": kwargs.get('stream', self.stream),
            "Source": source_lang,
            "Target": target_lang,
            "Text": text
        }
        
        # 可选参数
        if self.field:
            payload["Field"] = self.field
            
        if self.reference:
            payload["Reference"] = self.reference
                
        return payload
    
    def _parse_stream_response(self, response) -> Dict[str, Any]:
        """
        解析流式响应
        
        Args:
            response: 流式响应对象
            
        Returns:
            解析后的响应数据
        """
        translated_text = []
        usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        request_id = response.headers.get("X-TC-RequestId", "")
        error_msg = ""
        
        # 解析SSE流
        for line in response.iter_lines(chunk_size=1024, decode_unicode=False):
            if not line:
                continue
                
            line_str = line.decode("utf-8").strip()
            if not line_str.startswith("data:"):
                continue
                
            data_str = line_str[5:].strip()
            if data_str == "[DONE]":
                break
            if not data_str:
                continue
                
            try:
                stream_data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
                
            # 处理错误
            if "ErrorMsg" in stream_data and stream_data["ErrorMsg"]:
                error_msg = stream_data["ErrorMsg"]
                continue
                
            # 提取增量内容
            if "Choices" in stream_data and len(stream_data["Choices"]) > 0:
                delta_content = stream_data["Choices"][0].get("Delta", {}).get("Content", "")
                if delta_content:
                    translated_text.append(delta_content)
                    
            # 提取Token使用信息
            if "Usage" in stream_data:
                usage_info = {
                    "prompt_tokens": stream_data["Usage"].get("PromptTokens", 0),
                    "completion_tokens": stream_data["Usage"].get("CompletionTokens", 0),
                    "total_tokens": stream_data["Usage"].get("TotalTokens", 0)
                }
                
        # 检查错误
        if error_msg:
            raise APIError(f"流式翻译异常: {error_msg} (请求ID: {request_id})")
            
        if not translated_text:
            raise APIError(f"流式译文为空 (请求ID: {request_id})")
            
        # 构建标准响应格式
        return {
            "Response": {
                "Choices": [{
                    "Message": {
                        "Content": "".join(translated_text)
                    }
                }],
                "Usage": usage_info,
                "RequestId": request_id
            }
        }
    
    def translate_with_stream(self, text: str,
                            source_lang: Optional[str] = None,
                            target_lang: Optional[str] = None,
                            **kwargs) -> str:
        """
        流式翻译接口
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        return self.translate(text, source_lang, target_lang, method="stream", **kwargs)
    
    def translate_with_references(self, text: str,
                                 references: List[Dict[str, str]],
                                 source_lang: Optional[str] = None,
                                 target_lang: Optional[str] = None,
                                 **kwargs) -> str:
        """
        参考示例翻译接口
        
        Args:
            text: 要翻译的文本
            references: 参考示例列表
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        return self.translate(text, source_lang, target_lang, references=references, **kwargs)
    
    def get_supported_models(self) -> Dict[str, str]:
        """获取支持的翻译模型"""
        return self.SUPPORTED_MODELS.copy()
    
    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取腾讯混元翻译特殊API方法的引用规范
        
        Returns:
            包含特殊API方法信息的字典
        """
        return {
            "translate_with_stream": {
                "description": "流式翻译接口，支持实时返回翻译结果",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（不能为auto）",
                    "target_lang": "目标语言",
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_stream('Hello world', 'en', 'zh')"
            },
            "translate_with_references": {
                "description": "参考示例翻译接口，提供示例参考以提高翻译质量",
                "parameters": {
                    "text": "要翻译的文本",
                    "references": "参考示例列表，格式: [{'Source': '原文1', 'Target': '译文1'}, ...]",
                    "source_lang": "源语言（不能为auto）",
                    "target_lang": "目标语言",
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_references('文本', [{'Source': '参考原文', 'Target': '参考译文'}], 'zh', 'en')"
            },
            "get_supported_models": {
                "description": "获取支持的翻译模型列表",
                "parameters": {},
                "return_type": "Dict[str, str] 支持的模型字典",
                "example": "translator.get_supported_models()"
            }
        }