"""腾讯混元大模型翻译服务实现类"""
import time
import random
import hashlib
import hmac
import json
from typing import Dict, Any, List, Optional
import requests
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class TencentHunyuanTranslator(TranslatorBase):
    """腾讯混元大模型翻译服务实现类"""
    
    metadata = Metadata(
        console_url="https://console.cloud.tencent.com/hunyuan",    
        description="腾讯混元大模型翻译服务实现",
        documentation_url="https://cloud.tencent.com/document/product/1729/113395",
        short_description="腾讯混元翻译服务",
        usage_documentation=""
    )
    SERVICE_NAME = "tencent_hunyuan_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测',
        'zh': '中文',
        'en': '英语',
        'ja': '日语',
        'ko': '韩语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语',
        'ru': '俄语',
        'pt': '葡萄牙语',
        'it': '意大利语',
        'ar': '阿拉伯语',
        'tr': '土耳其语',
        'vi': '越南语',
        'id': '印尼语',
        'th': '泰语',
        'ms': '马来语',
        'hi': '印地语'
    }
    
    # 腾讯混元API端点
    BASE_ENDPOINT = "https://api.tencentcloudapi.com"
    TRANSLATE_PATH = "/v2/hunyuan/translate"
    LANG_DETECT_PATH = "/v2/hunyuan/detect-language"
    
    metadata = Metadata(
        console_url="https://console.cloud.tencent.com/hunyuan",
        description="腾讯混元大模型翻译服务实现",
        documentation_url="https://cloud.tencent.com/document/product/1729/113395",
        short_description="腾讯混元翻译服务",
        usage_documentation=""
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化腾讯混元翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持secret_id, secret_key等
        """
        config = config or self.DEFAULT_CONFIG
        self.secret_id = config.api_key.get('secret_id', '')
        self.secret_key = config.api_key.get('secret_key', '')
        
        super().__init__(config,** kwargs)
        
        if not self.secret_id:
            raise ConfigurationError("腾讯混元翻译需要配置secret_id")
        if not self.secret_key:
            raise ConfigurationError("腾讯混元翻译需要配置secret_key")
        
        # 线程本地存储，用于速率限制
        self.MIN_REQUEST_INTERVAL = 0.3  # 建议的最小请求间隔
        
    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.secret_id:
            raise ConfigurationError("secret_id未配置，腾讯混元翻译需要secret_id和secret_key")
        if not self.secret_key:
            raise ConfigurationError("secret_key未配置，腾讯混元翻译需要secret_id和secret_key")
    
    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用腾讯混元翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        url = f"{self.BASE_ENDPOINT}{self.TRANSLATE_PATH}"
        
        # 处理自动检测语言的情况
        if source_lang == 'auto':
            detect_result = self.detect_language(text)
            source_lang = detect_result.get('Lang', 'zh')
        
        # 构建请求参数
        params = {
            "Action": "TranslateText",
            "Version": "2023-09-01",
            "Region": kwargs.get('region', 'ap-guangzhou'),
            "SourceText": text,
            "SourceLang": source_lang,
            "TargetLang": target_lang
        }
        
        # 生成签名并添加到请求头
        timestamp = int(time.time())
        nonce = random.randint(10000, 99999)
        signature = self._generate_signature(params, timestamp, nonce)
        
        headers = {
            "Host": "api.tencentcloudapi.com",
            "Content-Type": "application/json",
            "X-TC-Action": "TranslateText",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Nonce": str(nonce),
            "X-TC-Region": params["Region"],
            "Authorization": signature
        }
        
        # 发送请求
        response = requests.post(
            url,
            headers=headers,
            json=params,
            proxies=self.proxies,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        语种识别
        
        Args:
            text: 要识别的文本
            
        Returns:
            包含识别结果的字典
        """
        url = f"{self.BASE_ENDPOINT}{self.LANG_DETECT_PATH}"
        
        params = {
            "Action": "DetectLanguage",
            "Version": "2023-09-01",
            "Region": "ap-guangzhou",
            "Text": text
        }
        
        timestamp = int(time.time())
        nonce = random.randint(10000, 99999)
        signature = self._generate_signature(params, timestamp, nonce)
        
        headers = {
            "Host": "api.tencentcloudapi.com",
            "Content-Type": "application/json",
            "X-TC-Action": "DetectLanguage",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Nonce": str(nonce),
            "X-TC-Region": params["Region"],
            "Authorization": signature
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=params,
            proxies=self.proxies,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'Error' in result:
            raise APIError(f"语种识别失败: {result['Error'].get('Message', '未知错误')} "
                          f"(错误码: {result['Error'].get('Code')})")
            
        return result.get('Response', {})
    
    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if 'Error' in response:
            raise APIError(f"翻译失败: {response['Error'].get('Message', '未知错误')} "
                          f"(错误码: {response['Error'].get('Code')})")
        
        response_data = response.get('Response', {})
        if 'TargetText' in response_data:
            return response_data['TargetText']
            
        raise APIError(f"无法解析翻译响应: {response}")
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: int, nonce: int) -> str:
        """
        生成腾讯云API签名
        
        参考文档: https://cloud.tencent.com/document/api/213/30654
        """
        # 1. 拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        
        # 2. 生成 canonical headers 和 signed headers
        canonical_headers = (
            f"content-type:application/json\n"
            f"host:api.tencentcloudapi.com\n"
        )
        signed_headers = "content-type;host"
        
        # 3. 生成请求体哈希
        payload = json.dumps(params)
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # 4. 拼接规范请求串
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )
        
        # 5. 生成签名串
        algorithm = "TC3-HMAC-SHA256"
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        service = "hunyuan"
        region = params.get('Region', 'ap-guangzhou')
        
        credential_scope = f"{date}/{region}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )
        
        # 6. 计算签名
        secret_date = hmac.new(
            f"TC3{self.secret_key}".encode('utf-8'),
            date.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        secret_service = hmac.new(
            secret_date,
            service.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        secret_signing = hmac.new(
            secret_service,
            "tc3_request".encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature = hmac.new(
            secret_signing,
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # 7. 生成Authorization
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        return authorization
    
    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取腾讯混元翻译特殊API方法的引用规范
        
        Returns:
            包含特殊API方法信息的字典
        """
        return {
            "detect_language": {
                "description": "语种识别，自动识别输入文本的语言",
                "parameters": {
                    "text": "要识别的文本"
                },
                "return_type": "Dict[str, Any] 包含识别结果的字典",
                "example": "translator.detect_language('你好世界')"
            }
        }