"""
Qcri翻译服务实现
"""

import warnings
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
    
    DEFAULT_API_KEY = {
        "api_key": "",
        "domain": ""
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "API Key",
            "description": "Qcri翻译API密钥",
            "required": True,
            "type": "string"
        },
        {
            "id": "domain",
            "name": "Domain",
            "description": "翻译领域建议调api获取",
            "required": False,
            "type": "string"
        }
    ]

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
        self.api_endpoints = {
            "get_languages": "getLanguagePairs",
            "get_domains": "getDomains",
            "translate": "translate",
        }

        super().__init__(config, **kwargs)
        
        try:
            self.SUPPORTED_LANGUAGES = self.get_supported_languages()
        except Exception as e:
            warnings.warn(f"获取支持的语言列表失败，使用默认列表: {e}", RuntimeWarning)

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

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Qcri翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
        """
        domain = self.config.api_key.get('domain', 'general')  # 默认为通用领域

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