"""
DeepL翻译服务实现
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata


class DeepLTranslator(TranslatorBase):
    """DeepL翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "deepl_translator"
    SUPPORTED_LANGUAGES = {
        "bg": "bulgarian", "cs": "czech", "da": "danish", "de": "german", "el": "greek",
        "en": "english", "es": "spanish", "et": "estonian", "fi": "finnish",
        "fr": "french", "hu": "hungarian", "id": "indonesian", "it": "italian",
        "ja": "japanese", "ko": "korean", "lt": "lithuanian", "lv": "latvian",
        "no": "norwegian", "nl": "dutch", "pl": "polish", "pt": "portuguese",
        "ro": "romanian", "ru": "russian", "sk": "slovak", "sl": "slovenian",
        "sv": "swedish", "tr": "turkish", "uk": "ukrainian", "zh": "chinese",
        "auto": "auto"
    }
    
    # DeepL API端点
    BASE_ENDPOINT = "https://api-free.deepl.com/v2/"
    TRANSLATE_ENDPOINT = "translate"
    
    METADATA = Metadata(
        console_url="https://www.deepl.com/pro",
        description="DeepL翻译服务实现，提供高质量的神经网络翻译",
        documentation_url="https://www.deepl.com/docs-api",
        short_description="DeepL翻译服务",
        usage_documentation="需要API密钥，支持多种语言，翻译质量高"
    )
    
    # 默认API配置
    DEFAULT_API_KEY = {
        "api_key": "",
        "use_free_api": True,
        "glossary_id": None,
        "preserve_formatting": False,
        "tag_handling": "xml",
        "context": None,
        "split_sentences": "1",
        "prevent_implicit_spaces": False,
        "formality": None
    }
    
    # API参数描述
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "DeepL API密钥",
            "type": "string",
            "required": True,
            "description": "DeepL翻译服务的API密钥，可从DeepL控制台获取"
        },
        {
            "id": "use_free_api",
            "name": "使用免费API",
            "type": "boolean",
            "required": False,
            "description": "免费版（True）限每月50万字，端点为api-free.deepl.com；付费版（False）无限制，端点为api.deepl.com"
        },
        {
            "id": "glossary_id",
            "name": "术语表ID",
            "type": "string",
            "required": False,
            "description": "用于翻译的术语表ID，需提前在DeepL控制台创建"
        },
        {
            "id": "preserve_formatting",
            "name": "保留格式",
            "type": "boolean",
            "required": False,
            "description": "是否保留原文格式，默认为False"
        },
        {
            "id": "tag_handling",
            "name": "标签处理",
            "type": "string",
            "required": False,
            "description": "指定的标签处理方式，可选xml/html/none，默认为'xml'"
        },
        {
            "id": "context",
            "name": "上下文",
            "type": "string",
            "required": False,
            "description": "提供额外的上下文信息以改善翻译，最大500字符"
        },
        {
            "id": "split_sentences",
            "name": "句子分割",
            "type": "string",
            "required": False,
            "description": "控制句子分割的方式，可选0（不分割）/ 1（正常分割）/ nonewlines（不按换行分割），默认'1'"
        },
        {
            "id": "prevent_implicit_spaces",
            "name": "防止隐式空格",
            "type": "boolean",
            "required": False,
            "description": "是否防止在标签周围添加隐式空格，默认为False"
        },
        {
            "id": "formality",
            "name": "正式程度",
            "type": "string",
            "required": False,
            "description": "可选'default'/'more'/'less'，仅支持德语、法语等部分语言，英语不生效"
        }
    ]
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化DeepL翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key, use_free_api等
        """
        super().__init__(config,** kwargs)
        
        # 根据是否使用免费API设置正确的端点
        if not self.use_free_api:
            self.BASE_ENDPOINT = "https://api.deepl.com/v2/"


    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用DeepL翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数，如glossary_id, preserve_formatting等
        """
        # 构建请求头
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # 构建请求数据
        data = {
            'text': text,
            'target_lang': target_lang.upper()
        }

        # 添加可选参数
        if source_lang != 'auto':
            data['source_lang'] = source_lang.upper()
        if self.glossary_id:
            data['glossary_id'] = self.glossary_id
        if self.preserve_formatting:
            data['preserve_formatting'] = '1'
        if self.tag_handling:
            data['tag_handling'] = self.tag_handling
        if self.context:
            data['context'] = self.context
        if self.split_sentences:
            data['split_sentences'] = self.split_sentences
        if self.prevent_implicit_spaces:
            data['prevent_implicit_spaces'] = '1'
        if self.formality:
            data['formality'] = self.formality

        # 发送请求
        response = self.session.post(
            f"{self.BASE_ENDPOINT}{self.TRANSLATE_ENDPOINT}",
            headers=headers,
            data=data,
            timeout=self.config.timeout
        )

        # 检查响应状态
        if response.status_code == 403:
            raise APIError("DeepL API访问被拒绝，请检查API密钥是否正确")
        elif response.status_code == 429:
            raise APIError("DeepL API请求频率超限，请稍后重试")
        elif response.status_code == 400:
            raise APIError(f"DeepL API请求错误: {response.text}")
        elif response.status_code == 404:
            raise APIError(f"DeepL API端点未找到: {response.text}")
        elif response.status_code >= 400:
            raise APIError(f"DeepL API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if 'translations' not in response or not response['translations']:
            raise APIError("DeepL API响应中未找到翻译结果")
            
        # 获取第一个翻译结果
        translation = response['translations'][0]
        return translation['text']

    def get_usage(self) -> Dict[str, Any]:
        """获取API使用情况"""
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = self.session.post(
            f"{self.BASE_ENDPOINT}usage",
            headers=headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_glossaries(self) -> List[Dict[str, Any]]:
        """获取用户定义的术语表列表"""
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = self.session.get(
            f"{self.BASE_ENDPOINT}glossaries",
            headers=headers,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json().get('glossaries', [])

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取DeepL翻译特殊API方法的引用规范
        """
        return {
            "get_usage": {
                "description": "获取API使用情况统计信息",
                "parameters": {},
                "return_type": "Dict[str, Any] 使用情况信息字典",
                "example": "translator.get_usage()"
            },
            "get_glossaries": {
                "description": "获取用户定义的术语表列表",
                "parameters": {},
                "return_type": "List[Dict[str, Any]] 术语表信息列表",
                "example": "translator.get_glossaries()"
            }
        }
