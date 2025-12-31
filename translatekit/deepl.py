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
            "description": "是否使用免费版API，默认为True，免费版使用api-free.deepl.com端点"
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
            "description": "指定的标签处理方式，默认为'xml'"
        },
        {
            "id": "context",
            "name": "上下文",
            "type": "string",
            "required": False,
            "description": "提供额外的上下文信息以改善翻译"
        },
        {
            "id": "split_sentences",
            "name": "句子分割",
            "type": "string",
            "required": False,
            "description": "控制句子分割的方式，默认为'1'"
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
            "description": "翻译的正式程度，可选值为'default'、'more'、'less'"
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
        
        # 从配置中获取API参数
        self.api_key = self.config.api_key.get('api_key', '')
        self.use_free_api = self.config.api_key.get('use_free_api', True)
        self.glossary_id = self.config.api_key.get('glossary_id', None)
        self.preserve_formatting = self.config.api_key.get('preserve_formatting', False)
        self.tag_handling = self.config.api_key.get('tag_handling', 'xml')
        self.context = self.config.api_key.get('context', None)
        self.split_sentences = self.config.api_key.get('split_sentences', '1')
        self.prevent_implicit_spaces = self.config.api_key.get('prevent_implicit_spaces', False)
        self.formality = self.config.api_key.get('formality', None)

        self.validate_config()

        # 根据是否使用免费API设置正确的端点
        if not self.use_free_api:
            self.BASE_ENDPOINT = "https://api.deepl.com/v2/"

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.api_key:
            raise ConfigurationError("DeepL API密钥未配置")

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

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()

    def validate_language(self, lang_code: str, lang_type: str = 'target') -> bool:
        """验证语言代码 - 支持语言代码和语言名称两种格式"""
        supported = self.get_supported_languages()
        
        # 如果是'auto'且为源语言，返回True
        if lang_code == 'auto' and lang_type == 'source':
            return True
            
        # 检查是否是语言代码（如'en'）
        for name, code in supported.items():
            if code == lang_code:
                return True
                
        # 检查是否是语言名称（如'english'）
        return lang_code in supported

    def _validate_languages(self, source_lang: str, target_lang: str):
        """验证语言对"""
        if not self.validate_language(source_lang, 'source'):
            raise ValueError(f"不支持的源语言: {source_lang}")
            
        if not self.validate_language(target_lang, 'target'):
            raise ValueError(f"不支持的目标语言: {target_lang}")

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
            },
            "get_supported_languages": {
                "description": "获取DeepL支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_supported_languages()"
            }
        }

    def set_glossary(self, glossary_id: str):
        """设置要使用的术语表ID"""
        self.glossary_id = glossary_id

    def set_formality(self, formality: str):
        """
        设置翻译的正式程度
        Args:
            formality: 'default', 'more', 'less'
        """
        if formality in ['default', 'more', 'less']:
            self.formality = formality
        else:
            raise ValueError("正式程度必须是 'default', 'more', 或 'less' 中的一个")