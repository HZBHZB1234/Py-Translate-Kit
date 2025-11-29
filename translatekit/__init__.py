"""
Py-Translate-Kit - 轻量级Python翻译工具包

此包提供了一个统一的翻译接口，支持多种翻译服务
"""

from .base import TranslatorBase, TranslationConfig, TranslationError, ConfigurationError, APIError
from .baidu import BaiduTranslator
from .google import GoogleTranslator
from .deepl import DeepLTranslator
from .microsoft import MicrosoftTranslator

__all__ = [
    'TranslatorBase',
    'TranslationConfig',
    'TranslationError',
    'ConfigurationError',
    'APIError',
    'BaiduTranslator',
    'GoogleTranslator',
    'DeepLTranslator',
    'MicrosoftTranslator',
]

__version__ = "1.0.0"
__author__ = "HZBHZB1234"
