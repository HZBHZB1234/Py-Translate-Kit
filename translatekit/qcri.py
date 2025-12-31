"""
Qcri翻译服务实现
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class QcriTranslator(TranslatorBase):
    """Qcri翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "qcri_translator"
    SUPPORTED_LANGUAGES = {
        "ar": "Arabic","en": "English","es": "Spanish","auto": "auto"
    }
    
    # Qcri翻译API端点
    BASE_ENDPOINT = "https://mt.qcri.org/api/v1/"
    
    METADATA = Metadata(
        console_url="https://mt.qcri.org/",
        description="Qcri翻译服务实现，由卡塔尔计算研究所提供的翻译服务",
        documentation_url="https://mt.qcri.org/api/doc/",
        short_description="Qcri翻译服务（卡塔尔计算研究所）",
        usage_documentation="需要API密钥，支持阿拉伯语、英语、西班牙语等语言对"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Qcri翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key等
        """
        config = config or self.DEFAULT_CONFIG
        self.api_key = config.api_key.get('qcri_api_key', kwargs.get('api_key', ''))
        self.proxies = kwargs.get('proxies', None)

        # 验证API密钥
        if not self.api_key:
            raise ConfigurationError("Qcri翻译需要API密钥，可免费获取：https://mt.qcri.org/api/v1/ref")

        # 更新配置中的API密钥
        config.api_key['qcri_api_key'] = self.api_key

        # API端点
        self.api_endpoints = {
            "get_languages": "getLanguagePairs",
            "get_domains": "getDomains",
            "translate": "translate",
        }

        super().__init__(config, **kwargs)

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.api_key:
            raise ConfigurationError("Qcri API密钥未配置")

    def _get(self, endpoint: str, params: Optional[dict] = None, return_text: bool = True) -> str:
        """执行GET请求"""
        if not params:
            params = {"key": self.api_key}
        try:
            url = self.BASE_ENDPOINT + self.api_endpoints[endpoint]
            res = self.session.get(url, params=params, proxies=self.proxies, timeout=self.config.timeout)
            return res.text if return_text else res
        except Exception as e:
            raise APIError(f"Qcri API请求错误: {e}")

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Qcri翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数，包括domain
        """
        domain = kwargs.get('domain', 'general')  # 默认为通用领域

        params = {
            "key": self.api_key,
            "langpair": f"{source_lang}-{target_lang}",
            "domain": domain,
            "text": text,
        }

        try:
            response = self._get("translate", params=params, return_text=False)
        except ConnectionError:
            raise APIError("Qcri API连接错误")

        if response.status_code != 200:
            raise APIError(f"Qcri API错误: {response.status_code}")

        response.raise_for_status()
        result = response.json()
        return result

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        translation = response.get("translatedText")
        if not translation:
            raise APIError("Qcri API响应中未找到翻译结果")
        return translation

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        try:
            # 从API获取支持的语言对
            response = self._get("get_languages", return_text=False)
            if response.status_code != 200:
                raise APIError(f"获取支持语言列表错误: {response.status_code}")

            data = response.json()
            # 从语言对中提取单独的语言代码
            languages = set()
            for pair in data:
                if 'sourceLanguage' in pair:
                    languages.add(pair['sourceLanguage'])
                if 'targetLanguage' in pair:
                    languages.add(pair['targetLanguage'])

            # 创建语言名称到代码的映射（简化版，实际应用中可能需要更完整的映射）
            language_map = {}
            for lang_code in languages:
                language_map[lang_code] = lang_code

            return language_map
        except Exception as e:
            self.logger.warning(f"无法获取Qcri支持的语言列表，使用默认列表: {e}")
            return self.SUPPORTED_LANGUAGES.copy()

    def get_domains(self) -> List[str]:
        """
        获取支持的翻译领域
        
        Returns:
            支持的领域列表
        """
        try:
            response = self._get("get_domains", return_text=False)
            if response.status_code != 200:
                raise APIError(f"获取支持领域列表错误: {response.status_code}")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise APIError(f"获取领域列表错误: {e}")

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
        获取Qcri翻译特殊API方法的引用规范
        """
        return {
            "get_supported_languages": {
                "description": "获取Qcri支持的语言列表",
                "parameters": {},
                "return_type": "Dict[str, str] 语言代码映射字典",
                "example": "translator.get_supported_languages()"
            },
            "get_domains": {
                "description": "获取Qcri支持的翻译领域列表",
                "parameters": {},
                "return_type": "List[str] 支持的领域列表",
                "example": "translator.get_domains()"
            },
            "translate_with_domain": {
                "description": "使用指定领域进行翻译",
                "parameters": {
                    "text": "要翻译的文本",
                    "domain": "翻译领域，如'general', 'it', 'media', 'scientific'等"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate('Hello', domain='general')"
            }
        }