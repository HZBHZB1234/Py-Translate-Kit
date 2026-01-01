"""
translator/youdao.py

有道翻译服务实现，支持文本翻译、大模型翻译、文档翻译、图片翻译等
"""

import json
import random
import time
import hashlib
import base64
import hmac
import uuid
import requests
from typing import Dict, Any, List, Optional, Union
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class YoudaoTranslator(TranslatorBase):
    """有道翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "youdao_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测', 'zh-CHS': '中文', 'en': '英语', 'ja': '日语',
        'ko': '韩语', 'fr': '法语', 'es': '西班牙语', 'pt': '葡萄牙语',
        'it': '意大利语', 'ru': '俄语', 'de': '德语', 'ar': '阿拉伯语',
        'tr': '土耳其语', 'th': '泰语', 'vi': '越南语', 'id': '印尼语',
        'ms': '马来语', 'hi': '印地语', 'he': '希伯来语', 'pl': '波兰语',
        'nl': '荷兰语', 'ro': '罗马尼亚语', 'hu': '匈牙利语', 'cs': '捷克语',
        'sk': '斯洛伐克语', 'da': '丹麦语', 'sv': '瑞典语', 'fi': '芬兰语',
        'no': '挪威语', 'el': '希腊语', 'bg': '保加利亚语', 'uk': '乌克兰语',
        'hr': '克罗地亚语', 'sr': '塞尔维亚语', 'sl': '斯洛文尼亚语',
        'et': '爱沙尼亚语', 'lv': '拉脱维亚语', 'lt': '立陶宛语'
    }
    
    # 有道API端点
    BASE_ENDPOINT = "https://openapi.youdao.com"
    TEXT_TRANSLATE_PATH = "/api"
    LLM_TRANSLATE_PATH = "/llm_trans"
    BATCH_TRANSLATE_PATH = "/v2/api"
    DOC_UPLOAD_PATH = "/file_trans/upload"
    DOC_QUERY_PATH = "/file_trans/query"
    DOC_DOWNLOAD_PATH = "/file_trans/download"
    IMAGE_TRANSLATE_PATH = "/ocrtransapi"
    WEB_TRANSLATE_PATH = "/translate_html"
    CHINESE_SEGMENT_PATH = "/cwsapi"
    DEEPSEEK_PATH = "/ai_dialog/deepSeek"
    
    # 支持的翻译领域
    SUPPORTED_DOMAINS = {
        "general": "通用",
        "computer": "计算机",
        "medical": "医学",
        "financial": "金融经济",
        "game": "游戏"
    }
    
    # 支持的文件格式
    SUPPORTED_FILE_TYPES = {
        "docx": "Word文档",
        "pdf": "PDF文档",
        "doc": "Word文档(旧版)",
        "jpg": "JPEG图片",
        "png": "PNG图片",
        "bmp": "BMP图片",
        "ppt": "PowerPoint演示文稿(旧版)",
        "pptx": "PowerPoint演示文稿",
        "xlsx": "Excel表格"
    }
    
    # 默认API密钥和所有可选参数
    DEFAULT_API_KEY = {
        "appKey": "",
        "appSecret": "",
        # 文本翻译参数
        "strict": "false",
        "vocabId": "",
        "domain": "general",
        "rejectFallback": "false",
        "ext": "",
        "voice": "0",
        # LLM翻译参数
        "prompt": "",
        "streamType": "increment",
        "handleOption": "0",
        "polishOption": "",
        "expandOption": "",
        # 批量翻译参数
        "detectLevel": "0",
        "detectFilter": "true",
        "verifyLang": "false",
        # 图片翻译参数
        "render": "0",
        # 文档翻译参数
        "llmOptions": "0",
        "downloadFileType": "word",
        # 网页翻译参数
        "web_vocabId": "",
        # DeepSeek参数
        "deepseek_model": "deepseek-v3",
        "deepseek_stream": "false",
        "deepseek_maxTokens": "4096",
        # 通用参数
        "signType": "v3",
        "docType": "json"
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "appKey",
            "name": "有道翻译应用ID",
            "type": "string",
            "required": True,
            "description": "有道翻译应用ID，从有道智云控制台获取"
        },
        {
            "id": "appSecret",
            "name": "有道翻译应用密钥",
            "type": "string",
            "required": True,
            "description": "有道翻译应用密钥，从有道智云控制台获取"
        },
        # 文本翻译参数
        {
            "id": "strict",
            "name": "严格翻译模式",
            "type": "string",
            "required": False,
            "description": "是否严格按指定语言翻译，默认false"
        },
        {
            "id": "vocabId",
            "name": "用户术语表ID",
            "type": "string",
            "required": False,
            "description": "自定义术语表ID，用于统一术语翻译"
        },
        {
            "id": "domain",
            "name": "翻译领域",
            "type": "string",
            "required": False,
            "description": "领域化翻译：general(通用)/computer(计算机)/medical(医学)/financial(金融经济)/game(游戏)"
        },
        {
            "id": "rejectFallback",
            "name": "降级处理",
            "type": "string",
            "required": False,
            "description": "领域化翻译失败是否降级到通用翻译，默认false"
        },
        {
            "id": "ext",
            "name": "音频格式",
            "type": "string",
            "required": False,
            "description": "发音音频格式，支持mp3"
        },
        {
            "id": "voice",
            "name": "发音选择",
            "type": "string",
            "required": False,
            "description": "发音选择：0(女声)/1(男声)，默认0"
        },
        # LLM翻译参数
        {
            "id": "prompt",
            "name": "提示词",
            "type": "string",
            "required": False,
            "description": "LLM翻译提示词，≤1200字符/400单词"
        },
        {
            "id": "streamType",
            "name": "流式返回类型",
            "type": "string",
            "required": False,
            "description": "流式返回类型：increment(增量)/full(全量)/all(增量+全量)"
        },
        {
            "id": "handleOption",
            "name": "处理模式",
            "type": "string",
            "required": False,
            "description": "处理模式：0/3(通用翻译)/1/2(支持润色扩写)"
        },
        {
            "id": "polishOption",
            "name": "润色选项",
            "type": "string",
            "required": False,
            "description": "文本润色选项"
        },
        {
            "id": "expandOption",
            "name": "扩写选项",
            "type": "string",
            "required": False,
            "description": "文本扩写选项"
        },
        # 批量翻译参数
        {
            "id": "detectLevel",
            "name": "语言检测粒度",
            "type": "string",
            "required": False,
            "description": "语言检测粒度：0(合并检测)/1(分别检测)"
        },
        {
            "id": "detectFilter",
            "name": "翻译过滤",
            "type": "string",
            "required": False,
            "description": "是否过滤非必要翻译，默认true"
        },
        {
            "id": "verifyLang",
            "name": "语言核实",
            "type": "string",
            "required": False,
            "description": "是否二次核实语言方向，默认false"
        },
        # 图片翻译参数
        {
            "id": "render",
            "name": "渲染图片",
            "type": "string",
            "required": False,
            "description": "是否返回渲染图片：0(否)/1(是)，默认0"
        },
        # 文档翻译参数
        {
            "id": "llmOptions",
            "name": "大模型翻译",
            "type": "string",
            "required": False,
            "description": "是否用大模型翻译：0(否)/1(是)，仅中英互译有效"
        },
        {
            "id": "downloadFileType",
            "name": "下载文件格式",
            "type": "string",
            "required": False,
            "description": "文档下载格式：word/ppt/xlsx/pdf"
        },
        # 网页翻译参数
        {
            "id": "web_vocabId",
            "name": "网页翻译术语表ID",
            "type": "string",
            "required": False,
            "description": "网页翻译术语表ID，支持英中互译"
        },
        # DeepSeek参数
        {
            "id": "deepseek_model",
            "name": "DeepSeek模型",
            "type": "string",
            "required": False,
            "description": "DeepSeek模型名称：deepseek-v3/deepseek-r1等"
        },
        {
            "id": "deepseek_stream",
            "name": "DeepSeek流式返回",
            "type": "string",
            "required": False,
            "description": "DeepSeek是否流式返回：true/false"
        },
        {
            "id": "deepseek_maxTokens",
            "name": "DeepSeek最大token数",
            "type": "string",
            "required": False,
            "description": "DeepSeek返回最大token数，默认4096"
        },
        # 通用参数
        {
            "id": "signType",
            "name": "签名类型",
            "type": "string",
            "required": False,
            "description": "API签名类型，默认v3"
        },
        {
            "id": "docType",
            "name": "文档类型",
            "type": "string",
            "required": False,
            "description": "返回文档类型，默认json"
        }
    ]
    
    metadata = Metadata(
        console_url="https://ai.youdao.com/",
        description="有道智云翻译服务实现",
        documentation_url="https://ai.youdao.com/doc.s",
        short_description="有道翻译服务",
        usage_documentation="",
        custom_override_content={
            "max_text_length": 5000,
            "max_batch_size": 100,
            "rate_limit": 5,  # QPS
            "supported_formats": ["docx", "pdf", "doc", "jpg", "png", "bmp", "ppt", "pptx", "xlsx"],
            "special_features": ["domain_translation", "llm_translation", "document_translation", "image_translation", "webpage_translation"]
        }
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化有道翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持所有DEFAULT_API_KEY中的参数
        """
        super().__init__(config, **kwargs)
        
        # 线程本地存储，用于速率限制
        self.MIN_REQUEST_INTERVAL = 0.2  # 有道API建议的最小请求间隔
    
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用有道翻译API（文本翻译）
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            API响应
        """
        url = f"{self.BASE_ENDPOINT}{self.TEXT_TRANSLATE_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(text, salt, curtime)
        
        # 构建请求参数，优先使用kwargs中的参数，其次使用实例属性
        params = {
            'q': text,
            'from': source_lang,
            'to': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': self.signType,
            'curtime': curtime,
            'strict': self.strict,
            'vocabId': self.vocabId,
            'domain': self.domain,
            'rejectFallback': self.rejectFallback,
            'ext': self.ext,
            'voice': self.voice
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def _translate_llm(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """调用有道大模型翻译API"""
        url = f"{self.BASE_ENDPOINT}{self.LLM_TRANSLATE_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(text, salt, curtime)
        
        # 构建请求参数
        params = {
            'i': text,
            'from': source_lang,
            'to': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': self.signType,
            'curtime': curtime,
            'prompt': self.prompt,
            'streamType': self.streamType,
            'handleOption': self.handleOption,
            'polishOption': self.polishOption,
            'expandOption': self.expandOption
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        headers = {'Accept': 'text/event-stream'} if kwargs.get('stream', False) else {}
        response = self._session.post(url, data=params, headers=headers, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def _translate_batch(self, texts: List[str], source_lang: str, target_lang: str, **kwargs) -> Any:
        """调用有道批量翻译API"""
        url = f"{self.BASE_ENDPOINT}{self.BATCH_TRANSLATE_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 使用第一个文本生成签名
        sign_text = texts[0] if texts else ""
        sign = self._generate_sign(sign_text, salt, curtime)
        
        # 构建请求参数
        params = {
            'from': source_lang,
            'to': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': self.signType,
            'curtime': curtime,
            'detectLevel': self.detectLevel,
            'detectFilter': self.detectFilter,
            'verifyLang': self.verifyLang,
            'vocabId': self.vocabId,
            'ext': self.ext,
            'voice': self.voice
        }
        
        # 添加多个q参数
        for i, text in enumerate(texts):
            params[f'q[{i}]'] = text
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def translate_image(self, image_path: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        图片翻译
        
        Args:
            image_path: 图片文件路径
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果字典
        """
        url = f"{self.BASE_ENDPOINT}{self.IMAGE_TRANSLATE_PATH}"
        
        # 读取图片并进行base64编码
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(image_data, salt, curtime)
        
        # 构建请求参数
        params = {
            'type': '1',
            'from': source_lang,
            'to': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': kwargs.get('signType', self.signType),
            'curtime': curtime,
            'q': image_data,
            'docType': kwargs.get('docType', self.docType),
            'render': kwargs.get('render', self.render)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errorCode' in result and result['errorCode'] != '0':
            raise APIError(f"图片翻译失败: {result.get('errorMsg', '未知错误')} (错误码: {result.get('errorCode')})")
            
        return result
    
    def translate_webpage(self, html_content: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        网页翻译
        
        Args:
            html_content: HTML内容
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果字典
        """
        url = f"{self.BASE_ENDPOINT}{self.WEB_TRANSLATE_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(html_content, salt, curtime)
        
        # 构建请求参数
        params = {
            'q': html_content,
            'from': source_lang,
            'to': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': kwargs.get('signType', self.signType),
            'curtime': curtime,
            'vocabId': kwargs.get('vocabId', self.web_vocabId)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errorCode' in result and result['errorCode'] != '0':
            raise APIError(f"网页翻译失败: {result.get('errorMessage', '未知错误')} (错误码: {result.get('errorCode')})")
            
        return result
    
    def chinese_segment(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        中文分词
        
        Args:
            text: 中文文本
            **kwargs: 额外参数
            
        Returns:
            分词结果字典
        """
        url = f"{self.BASE_ENDPOINT}{self.CHINESE_SEGMENT_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(text, salt, curtime)
        
        # 构建请求参数
        params = {
            'appKey': self.appKey,
            'curtime': curtime,
            'q': text,
            'salt': salt,
            'sign': sign,
            'signType': kwargs.get('signType', self.signType)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errorCode' in result and result['errorCode'] != '0':
            raise APIError(f"中文分词失败: {result.get('msg', '未知错误')} (错误码: {result.get('errorCode')})")
            
        return result
    
    def upload_document_translation(self, file_path: str, file_name: str, 
                                   source_lang: str, target_lang: str, 
                                   file_format: str, **kwargs) -> Dict[str, Any]:
        """
        上传文档翻译
        
        Args:
            file_path: 本地文件路径
            file_name: 文件名
            source_lang: 源语言
            target_lang: 目标语言
            file_format: 文件格式
            **kwargs: 额外参数
            
        Returns:
            包含文档流水号的响应字典
        """
        url = f"{self.BASE_ENDPOINT}{self.DOC_UPLOAD_PATH}"
        
        # 读取文件并进行base64编码
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(content, salt, curtime)
        
        # 构建请求参数
        params = {
            'q': content,
            'fileName': file_name,
            'fileType': file_format,
            'langFrom': source_lang,
            'langTo': target_lang,
            'appKey': self.appKey,
            'salt': salt,
            'curtime': curtime,
            'sign': sign,
            'docType': kwargs.get('docType', self.docType),
            'signType': kwargs.get('signType', self.signType),
            'llmOptions': kwargs.get('llmOptions', self.llmOptions),
            'domain': kwargs.get('domain', self.domain),
            'vocabId': kwargs.get('vocabId', self.vocabId)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errorCode' in result and result['errorCode'] != '0':
            raise APIError(f"上传文档失败: {result.get('errorMsg', '未知错误')} (错误码: {result.get('errorCode')})")
            
        return result
    
    def query_document_translation(self, flownumber: str, **kwargs) -> Dict[str, Any]:
        """
        查询文档翻译进度
        
        Args:
            flownumber: 文档流水号
            **kwargs: 额外参数
            
        Returns:
            包含翻译状态的字典
        """
        url = f"{self.BASE_ENDPOINT}{self.DOC_QUERY_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(flownumber, salt, curtime)
        
        # 构建请求参数
        params = {
            'flownumber': flownumber,
            'appKey': self.appKey,
            'salt': salt,
            'curtime': curtime,
            'sign': sign,
            'docType': kwargs.get('docType', self.docType),
            'signType': kwargs.get('signType', self.signType)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errorCode' in result and result['errorCode'] != '0':
            raise APIError(f"查询文档进度失败: {result.get('errorMsg', '未知错误')} (错误码: {result.get('errorCode')})")
            
        return result
    
    def download_document_translation(self, flownumber: str, download_format: str, **kwargs) -> bytes:
        """
        下载文档翻译结果
        
        Args:
            flownumber: 文档流水号
            download_format: 下载格式
            **kwargs: 额外参数
            
        Returns:
            文档内容字节流
        """
        url = f"{self.BASE_ENDPOINT}{self.DOC_DOWNLOAD_PATH}"
        
        # 生成随机数和时间戳
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 生成签名
        sign = self._generate_sign(flownumber, salt, curtime)
        
        # 构建请求参数
        params = {
            'flownumber': flownumber,
            'appKey': self.appKey,
            'salt': salt,
            'curtime': curtime,
            'sign': sign,
            'docType': kwargs.get('docType', self.docType),
            'signType': kwargs.get('signType', self.signType),
            'downloadFileType': kwargs.get('downloadFileType', download_format)
        }
        
        # 过滤空值参数
        params = {k: v for k, v in params.items() if v and str(v).strip()}
        
        # 发送请求
        response = self._session.post(url, data=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        # 检查是否返回错误
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            result = response.json()
            if 'errorCode' in result and result['errorCode'] != '0':
                raise APIError(f"下载文档失败: {result.get('errorMsg', '未知错误')} (错误码: {result.get('errorCode')})")
        
        return response.content
    
    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        error_code = response.get('errorCode', '0')
        
        if error_code != '0':
            error_msg = response.get('errorMsg') or response.get('errorMessage') or '未知错误'
            raise APIError(f"翻译失败: {error_msg} (错误码: {error_code})")
        
        # 处理文本翻译响应
        if 'translation' in response:
            translations = response['translation']
            if isinstance(translations, list):
                return translations[0]
            return translations
        
        # 处理批量翻译响应
        if 'translateResults' in response:
            results = []
            for item in response['translateResults']:
                if 'translation' in item:
                    results.append(item['translation'])
                elif 'errorCode' in item and item['errorCode'] != '0':
                    results.append(f"[错误: {item.get('errorMsg', '未知错误')}]")
            return ' '.join(results)
        
        # 处理LLM翻译响应
        if 'data' in response and 'output' in response['data']:
            return response['data']['output']
        
        raise APIError(f"无法解析翻译响应: {response}")
    
    def _generate_sign(self, text: str, salt: str, curtime: str) -> str:
        """生成有道API签名"""
        # 计算input值
        if len(text) <= 20:
            input_str = text
        else:
            input_str = text[:10] + str(len(text)) + text[-10:]
        
        # 生成签名字符串
        sign_str = self.appKey + input_str + salt + curtime + self.appSecret
        
        # 计算SHA256哈希
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
    
    def translate_with_llm(self, text: str, 
                          source_lang: Optional[str] = None, 
                          target_lang: Optional[str] = None,
                          prompt: str = "", 
                          **kwargs) -> str:
        """
        LLM翻译接口
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        return self.translate(text, source_lang, target_lang, method='llm', prompt=prompt, **kwargs)
    
    def translate_with_domain(self, text: str, domain: str, 
                             source_lang: Optional[str] = None, 
                             target_lang: Optional[str] = None, **kwargs) -> str:
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
        if domain not in self.SUPPORTED_DOMAINS:
            raise ValueError(f"不支持的翻译领域: {domain}，支持的领域有: {list(self.SUPPORTED_DOMAINS.keys())}")
        
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        return self.translate(text, source_lang, target_lang, domain=domain, **kwargs)
    
    def translate_with_deepseek(self, text: str, 
                               source_lang: Optional[str] = None, 
                               target_lang: Optional[str] = None,
                               **kwargs) -> str:
        """
        DeepSeek模型翻译接口
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        # 构建提示词
        prompt = kwargs.get('prompt', f"请将以下{source_lang}文本翻译成{target_lang}: {text}")
        
        # 调用DeepSeek模型
        url = f"{self.BASE_ENDPOINT}{self.DEEPSEEK_PATH}"
        
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # DeepSeek使用v4签名
        sign_str = self.appKey + salt + curtime + self.appSecret
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        params = {
            'appKey': self.appKey,
            'salt': salt,
            'sign': sign,
            'signType': 'v4',
            'curtime': curtime,
            'model': kwargs.get('model', self.deepseek_model),
            'messages': [{"role": "user", "content": prompt}],
            'stream': kwargs.get('stream', self.deepseek_stream),
            'maxTokens': kwargs.get('maxTokens', self.deepseek_maxTokens)
        }
        
        response = self._session.post(url, json=params, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if 'code' in result and result['code'] != '0':
            raise APIError(f"DeepSeek翻译失败: {result.get('msg', '未知错误')} (错误码: {result.get('code')})")
        
        # 解析DeepSeek响应
        if 'data' in result and 'choices' in result['data']:
            choices = result['data']['choices']
            if choices and 'message' in choices[0]:
                return choices[0]['message']['content']
        
        raise APIError(f"无法解析DeepSeek响应: {result}")
    
    def get_supported_domains(self) -> Dict[str, str]:
        """获取支持的翻译领域"""
        return self.SUPPORTED_DOMAINS.copy()
    
    def get_supported_file_types(self) -> Dict[str, str]:
        """获取支持的文件格式"""
        return self.SUPPORTED_FILE_TYPES.copy()
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        获取所有配置参数
        
        Returns:
            包含所有参数当前值的字典
        """
        params = {}
        for key in self.DEFAULT_API_KEY.keys():
            if hasattr(self, key):
                params[key] = getattr(self, key)
        return params
    
    
    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取有道翻译特殊API方法的引用规范
        
        Returns:
            包含特殊API方法信息的字典
        """
        return {
            "translate_image": {
                "description": "图片翻译，识别图片中的文字并翻译",
                "parameters": {
                    "image_path": "图片文件路径",
                    "source_lang": "源语言",
                    "target_lang": "目标语言",
                    "render": "是否返回渲染图片(0/1)"
                },
                "return_type": "Dict[str, Any] 包含翻译结果的字典",
                "example": "translator.translate_image('./image.jpg', 'zh-CHS', 'en')"
            },
            "translate_webpage": {
                "description": "网页翻译，翻译HTML内容",
                "parameters": {
                    "html_content": "HTML内容",
                    "source_lang": "源语言",
                    "target_lang": "目标语言",
                    "vocabId": "术语表ID"
                },
                "return_type": "Dict[str, Any] 包含翻译结果的字典",
                "example": "translator.translate_webpage('<h1>标题</h1>', 'zh-CHS', 'en')"
            },
            "chinese_segment": {
                "description": "中文分词，将中文文本分割为有意义的词语单元",
                "parameters": {
                    "text": "中文文本"
                },
                "return_type": "Dict[str, Any] 包含分词结果的字典",
                "example": "translator.chinese_segment('我爱自然语言处理')"
            },
            "upload_document_translation": {
                "description": "上传文档翻译任务",
                "parameters": {
                    "file_path": "本地文件路径",
                    "file_name": "文件名",
                    "source_lang": "源语言",
                    "target_lang": "目标语言",
                    "file_format": "文件格式",
                    "llmOptions": "是否使用大模型翻译",
                    "domain": "翻译领域"
                },
                "return_type": "Dict[str, Any] 包含文档流水号的响应字典",
                "example": "translator.upload_document_translation('./doc.docx', '文档.docx', 'zh-CHS', 'en', 'docx')"
            },
            "query_document_translation": {
                "description": "查询文档翻译进度",
                "parameters": {
                    "flownumber": "文档流水号"
                },
                "return_type": "Dict[str, Any] 包含翻译状态的字典",
                "example": "translator.query_document_translation('flownumber_123')"
            },
            "download_document_translation": {
                "description": "下载文档翻译结果",
                "parameters": {
                    "flownumber": "文档流水号",
                    "download_format": "下载格式"
                },
                "return_type": "bytes 文档内容字节流",
                "example": "translator.download_document_translation('flownumber_123', 'word')"
            },
            "translate_with_llm": {
                "description": "LLM翻译接口，使用大语言模型进行翻译",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（可选）",
                    "target_lang": "目标语言（可选）",
                    "prompt": "提示词",
                    "streamType": "流式返回类型",
                    "handleOption": "处理模式"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_llm('专业术语', 'zh-CHS', 'en', '请翻译为专业的英语')"
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
                "example": "translator.translate_with_domain('专业术语', 'computer', 'zh-CHS', 'en')"
            },
            "translate_with_deepseek": {
                "description": "DeepSeek模型翻译接口",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（可选）",
                    "target_lang": "目标语言（可选）",
                    "model": "DeepSeek模型名称",
                    "stream": "是否流式返回",
                    "maxTokens": "最大token数"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate_with_deepseek('需要翻译的文本', 'zh-CHS', 'en')"
            },
            "get_supported_domains": {
                "description": "获取支持的翻译领域列表",
                "parameters": {},
                "return_type": "Dict[str, str] 支持的领域字典",
                "example": "translator.get_supported_domains()"
            },
            "get_supported_file_types": {
                "description": "获取支持的文件格式列表",
                "parameters": {},
                "return_type": "Dict[str, str] 支持的文件格式字典",
                "example": "translator.get_supported_file_types()"
            },
            "get_all_parameters": {
                "description": "获取所有配置参数的当前值",
                "parameters": {},
                "return_type": "Dict[str, Any] 参数字典",
                "example": "translator.get_all_parameters()"
            }
    }