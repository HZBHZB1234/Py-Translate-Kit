"""
百度翻译服务实现，支持通用翻译、LLM翻译、文档翻译、领域翻译和语种识别
"""

import json
import random
import time
import hashlib
import base64
import hmac
import requests
from typing import Dict, Any, List, Optional, Union
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class BaiduTranslator(TranslatorBase):
    """百度翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "baidu_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测','zh': '中文','en': '英语','yue': '粤语',
        'wyw': '文言文','jp': '日语','kor': '韩语','fra': '法语',
        'spa': '西班牙语','th': '泰语','ara': '阿拉伯语','ru': '俄语',
        'pt': '葡萄牙语','de': '德语','it': '意大利语','el': '希腊语',
        'nl': '荷兰语','pl': '波兰语','bul': '保加利亚语',
        'est': '爱沙尼亚语','dan': '丹麦语','fin': '芬兰语','cs': '捷克语',
        'rom': '罗马尼亚语','slo': '斯洛文尼亚语','swe': '瑞典语',
        'hu': '匈牙利语','cht': '繁体中文','vie': '越南语'
    }
    
    # 百度API端点
    BASE_ENDPOINT = "https://fanyi-api.baidu.com"
    GENERAL_TRANSLATE_PATH = "/api/trans/vip/translate"
    LLM_TRANSLATE_PATH = "/api/trans/vip/llm/translate"
    LANG_DETECT_PATH = "/api/trans/vip/language"
    DOMAIN_TRANSLATE_PATH = "/api/trans/vip/fieldtranslate"
    DOC_CREATE_JOB_PATH = "/transapi/doctrans/createjob/trans"
    DOC_QUERY_PATH = "/transapi/doctrans/query/trans"
    DOC_QUOTE_PATH = "/transapi/doctrans/createjob/quote"
    DOC_QUERY_QUOTE_PATH = "/transapi/doctrans/query/quote"
    
    # 领域翻译支持的领域
    SUPPORTED_DOMAINS = {
        "common": "通用",
        "tech": "科技",
        "medical": "医疗",
        "legal": "法律",
        "financial": "金融"
    }
    
    DEFAULT_API_KEY = {
        "appid": "",
        "appkey": ""
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "appid",
            "name": "百度翻译appid",
            "type": "string",
            "required": True,
            "description": "百度翻译appid"
        },
        {
            "id": "appkey",
            "name": "百度翻译appkey",
            "type": "string",
            "required": True,
            "description": "百度翻译appkey"
        }
    ]
    
    metadata = Metadata(
        console_url="https://fanyi-api.baidu.com/api/trans/product/desktop",
        description="百度翻译服务实现",
        documentation_url="https://fanyi-api.baidu.com/doc/11",
        short_description="百度翻译服务",
        usage_documentation=""
    )
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化百度翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持appid, appkey等
        """
        super().__init__(config, **kwargs)
        
        # 线程本地存储，用于速率限制
        self.MIN_REQUEST_INTERVAL = 0.5  # 百度API建议的最小请求间隔
        
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用百度翻译API（通用翻译）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
            
        # 通用翻译
        url = f"{self.BASE_ENDPOINT}{self.GENERAL_TRANSLATE_PATH}"
        
        # 生成签名
        salt = random.randint(32768, 65536)
        sign = self._generate_general_sign(text, salt)
        
        # 构建请求参数
        params = {
            'appid': self.config.api_key.get('appid', ''),
            'q': text,
            'from': source_lang,
            'to': target_lang,
            'salt': salt,
            'sign': sign
        }
        
        # 发送请求
        response = self._session.get(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def _translate_llm(self, text: str, source_lang: str, target_lang: str,** kwargs) -> Any:
        """调用百度LLM翻译API"""
        url = f"{self.BASE_ENDPOINT}{self.LLM_TRANSLATE_PATH}"
        
        # 生成签名
        salt = random.randint(32768, 65536)
        sign = self._generate_general_sign(text, salt)
        
        # 构建请求参数
        params = {
            'appid': self.config.api_key.get('appid', ''),
            'q': text,
            'from': source_lang,
            'to': target_lang,
            'salt': salt,
            'sign': sign,
            'format': kwargs.get('format', 'text')  # 支持text或html
        }
        
        # 发送请求
        response = self._session.get(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def _translate_domain(self, text: str, source_lang: str, target_lang: str, domain: str, **kwargs) -> Any:
        """调用百度领域翻译API"""
        if domain not in self.SUPPORTED_DOMAINS:
            raise ValueError(f"不支持的翻译领域: {domain}，支持的领域有: {list(self.SUPPORTED_DOMAINS.keys())}")
            
        url = f"{self.BASE_ENDPOINT}{self.DOMAIN_TRANSLATE_PATH}"
        
        # 生成签名
        salt = random.randint(32768, 65536)
        sign = self._generate_general_sign(text, salt)
        
        # 构建请求参数
        params = {
            'appid': self.config.api_key.get('appid', ''),
            'q': text,
            'from': source_lang,
            'to': target_lang,
            'domain': domain,
            'salt': salt,
            'sign': sign
        }
        
        # 发送请求
        response = self._session.get(url, params=params, timeout=self.config.timeout)
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
        
        # 生成签名
        salt = random.randint(32768, 65536)
        sign = self._generate_general_sign(text, salt)
        
        # 构建请求参数
        params = {
            'appid': self.config.api_key.get('appid', ''),
            'q': text,
            'salt': salt,
            'sign': sign
        }
        
        # 发送请求
        response = self._session.get(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'error_code' in result:
            raise APIError(f"语种识别失败: {result.get('error_msg', '未知错误')} (错误码: {result.get('error_code')})")
            
        return result
    
    def create_llm_doc_translation_job(self, file_path: str, file_name: str, 
                                     from_lang: str, to_lang: str, 
                                     file_format: str, output_format: str = "") -> Dict[str, Any]:
        """
        创建LLM文档翻译任务
        
        Args:
            file_path: 本地文件路径
            file_name: 文件名
            from_lang: 源语言
            to_lang: 目标语言
            file_format: 文件格式
            output_format: 输出格式，可选
            
        Returns:
            包含任务ID的响应字典
        """
        url = f"{self.BASE_ENDPOINT}{self.DOC_CREATE_JOB_PATH}"
        
        # 读取文件并进行base64编码
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
            
        # 构建请求数据
        input_data = {
            'from': from_lang,
            'to': to_lang,
            'input': {
                'content': content,
                'format': file_format,
                'filename': file_name
            }
        }
        
        if output_format:
            input_data['output'] = {'format': output_format}
            
        # 生成签名和时间戳
        timestamp = int(time.time())
        sign = self._generate_doc_sign(timestamp, input_data)
        headers = self._create_doc_headers(timestamp, sign)
        
        # 发送请求
        response = self._session.post(
            url, 
            headers=headers, 
            json=input_data,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'error_code' in result:
            raise APIError(f"创建文档翻译任务失败: {result.get('error_msg', '未知错误')} (错误码: {result.get('error_code')})")
            
        return result
    
    def query_doc_translation(self, request_id: str) -> Dict[str, Any]:
        """
        查询文档翻译结果
        
        Args:
            request_id: 翻译任务ID
            
        Returns:
            包含翻译状态和结果的字典
        """
        url = f"{self.BASE_ENDPOINT}{self.DOC_QUERY_PATH}"
        
        input_data = {'requestId': request_id}
        
        # 生成签名和时间戳
        timestamp = int(time.time())
        sign = self._generate_doc_sign(timestamp, input_data)
        headers = self._create_doc_headers(timestamp, sign)
        
        # 发送请求
        response = self._session.post(
            url, 
            headers=headers, 
            json=input_data,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'error_code' in result:
            raise APIError(f"查询文档翻译结果失败: {result.get('error_msg', '未知错误')} (错误码: {result.get('error_code')})")
            
        return result
    
    def create_doc_quote(self, file_path: str, file_name: str, from_lang: str, to_lang: str, file_format: str) -> Dict[str, Any]:
        """创建文档翻译报价"""
        url = f"{self.BASE_ENDPOINT}{self.DOC_QUOTE_PATH}"
        
        # 读取文件并进行base64编码
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
            
        # 构建请求数据
        input_data = {
            'from': from_lang,
            'to': to_lang,
            'input': {
                'content': content,
                'format': file_format,
                'filename': file_name
            }
        }
        
        # 生成签名和时间戳
        timestamp = int(time.time())
        sign = self._generate_doc_sign(timestamp, input_data)
        headers = self._create_doc_headers(timestamp, sign)
        
        # 发送请求
        response = self._session.post(
            url, 
            headers=headers, 
            json=input_data,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'error_code' in result:
            raise APIError(f"创建文档报价失败: {result.get('error_msg', '未知错误')} (错误码: {result.get('error_code')})")
            
        return result
    
    def query_doc_quote(self, file_id: str) -> Dict[str, Any]:
        """查询文档翻译报价结果"""
        url = f"{self.BASE_ENDPOINT}{self.DOC_QUERY_QUOTE_PATH}"
        
        input_data = {'fileId': file_id}
        
        # 生成签名和时间戳
        timestamp = int(time.time())
        sign = self._generate_doc_sign(timestamp, input_data)
        headers = self._create_doc_headers(timestamp, sign)
        
        # 发送请求
        response = self._session.post(
            url, 
            headers=headers, 
            json=input_data,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        if 'error_code' in result:
            raise APIError(f"查询文档报价失败: {result.get('error_msg', '未知错误')} (错误码: {result.get('error_code')})")
            
        return result
    
    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if 'error_code' in response:
            raise APIError(f"翻译失败: {response.get('error_msg', '未知错误')} (错误码: {response.get('error_code')})")
            
        # 处理通用翻译和领域翻译的响应
        if 'trans_result' in response:
            return ''.join([item['dst'] for item in response['trans_result']])
            
        # 处理LLM翻译的响应
        if 'result' in response:
            return response['result']
            
        raise APIError(f"无法解析翻译响应: {response}")
    
    def _generate_general_sign(self, text: str, salt: int) -> str:
        """生成通用翻译API的签名"""
        appid = self.config.api_key.get('appid', '')
        sign_str = f"{appid}{text}{salt}{self.appkey}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def _generate_doc_sign(self, timestamp: int, input_data: Dict[str, Any]) -> str:
        """生成文档翻译API的签名"""
        appid = self.config.api_key.get('appid', '')
        query_str = json.dumps(input_data)
        sign_str = f"{appid}{timestamp}{query_str}"
        sign = base64.b64encode(
            hmac.new(
                self.appkey.encode('utf-8'), 
                sign_str.encode('utf-8'), 
                digestmod=hashlib.sha256
            ).digest()
        )
        return sign.decode('utf-8')
    
    def _create_doc_headers(self, timestamp: int, sign: str) -> Dict[str, str]:
        """创建文档翻译API的请求头"""
        return {
            'Content-Type': 'application/json',
            'X-Appid': self.config.api_key.get('appid', ''),
            'X-Sign': sign,
            'X-Timestamp': str(timestamp),
        }
    
    def translate_with_domain(self, text: str, domain: str, 
                             source_lang: Optional[str] = None, 
                             target_lang: Optional[str] = None,** kwargs) -> str:
        """
        领域翻译接口
        
        Args:
            text: 要翻译的文本
            domain: 翻译领域
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        return self.translate(text, source_lang, target_lang, domain=domain,** kwargs)
    
    def translate_with_llm(self, text: str, 
                          source_lang: Optional[str] = None, 
                          target_lang: Optional[str] = None,
                          format: str = 'text', **kwargs) -> str:
        """
        LLM翻译接口
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            format: 文本格式，text或html
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        return self.translate(text, source_lang, target_lang, use_llm=True, format=format,** kwargs)
    
    
    def get_supported_domains(self) -> Dict[str, str]:
        """获取支持的翻译领域"""
        return self.SUPPORTED_DOMAINS.copy()
    
    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取百度翻译特殊API方法的引用规范
        
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
            },
            "create_llm_doc_translation_job": {
                "description": "创建LLM文档翻译任务",
                "parameters": {
                    "file_path": "本地文件路径",
                    "file_name": "文件名",
                    "from_lang": "源语言",
                    "to_lang": "目标语言",
                    "file_format": "文件格式",
                    "output_format": "输出格式，可选"
                },
                "return_type": "Dict[str, Any] 包含任务ID的响应字典",
                "example": "translator.create_llm_doc_translation_job('./doc.txt', 'doc.txt', 'zh', 'en', 'txt')"
            },
            "query_doc_translation": {
                "description": "查询文档翻译结果",
                "parameters": {
                    "request_id": "翻译任务ID"
                },
                "return_type": "Dict[str, Any] 包含翻译状态和结果的字典",
                "example": "translator.query_doc_translation('request_id_123')"
            },
            "create_doc_quote": {
                "description": "创建文档翻译报价",
                "parameters": {
                    "file_path": "本地文件路径",
                    "file_name": "文件名",
                    "from_lang": "源语言",
                    "to_lang": "目标语言",
                    "file_format": "文件格式"
                },
                "return_type": "Dict[str, Any] 包含报价信息的响应字典",
                "example": "translator.create_doc_quote('./doc.txt', 'doc.txt', 'zh', 'en', 'txt')"
            },
            "query_doc_quote": {
                "description": "查询文档翻译报价结果",
                "parameters": {
                    "file_id": "文件ID"
                },
                "return_type": "Dict[str, Any] 包含报价查询结果的字典",
                "example": "translator.query_doc_quote('file_id_123')"
            },
            "translate_with_domain": {
                "description": "领域翻译接口，针对特定领域进行优化翻译",
                "parameters": {
                    "text": "要翻译的文本",
                    "domain": "翻译领域",
                    "source_lang": "源语言（可选）",
                    "target_lang": "目标语言（可选）"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_domain('专业术语', 'tech', 'zh', 'en')"
            },
            "translate_with_llm": {
                "description": "LLM翻译接口，使用大语言模型进行翻译",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（可选）",
                    "target_lang": "目标语言（可选）",
                    "format": "文本格式，text或html"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_llm('<p>HTML文本</p>', 'zh', 'en', 'html')"
            },
            "get_supported_domains": {
                "description": "获取支持的翻译领域列表",
                "parameters": {},
                "return_type": "Dict[str, str] 支持的领域字典",
                "example": "translator.get_supported_domains()"
            }
        }
