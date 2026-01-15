"""
空翻译器实现，对于所有输入文本都返回原文，用于调试目的
"""

from typing import Dict, Any, Optional
from .base import TranslatorBase, TranslationConfig, Metadata


class NullTranslator(TranslatorBase):
    """空翻译器实现类，对于所有输入文本都返回原文，用于调试目的"""
    
    # 服务元信息
    SERVICE_NAME = "null_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测',
        'en': '英语'
    }
    
    METADATA = Metadata(
        console_url="",
        description="空翻译器，对于所有输入文本都返回原文，用于调试目的",
        documentation_url="",
        short_description="空翻译器（调试用）",
        usage_documentation="不发送任何网络请求，直接返回原文，用于调试翻译流程"
    )
    
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """
        默认翻译方法，直接返回原文
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            原始文本，不做任何翻译
        """
        return text

    def _parse_api_response(self, response: Any, **kwargs) -> str:
        """
        解析API响应，对于NullTranslator，响应就是原始文本
        
        Args:
            response: API响应（在这里就是原始文本）
            **kwargs: 额外参数
            
        Returns:
            解析后的翻译文本
        """
        return response

    def _validate_languages(self, source_lang: str, target_lang: str):
        """验证语言对，NullTranslator不做验证，允许所有语言对"""
        pass