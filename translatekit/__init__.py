"""
Py-Translate-Kit - 轻量级Python翻译工具包

此包提供了一个统一的翻译接口，支持多种翻译服务
"""

from .base import TranslatorBase, TranslationConfig, TranslationError, ConfigurationError, APIError
from .baidu import BaiduTranslator
from .google import GoogleTranslator
from .deepl import DeepLTranslator
from .microsoft import MicrosoftTranslator
from .yandex import YandexTranslator
from .libre import LibreTranslator
from .mymemory import MyMemoryTranslator
from .papago import PapagoTranslator
from .linguee import LingueeTranslator
from .pons import PonsTranslator
from .qcri import QcriTranslator
from .tencent import TencentTranslator
from .youdao import YoudaoTranslator
from.sizhi import SizhiTranslator
from .llm_general import LLMGeneralTranslator
from .null_translator import NullTranslator
from . import kit

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
    'YandexTranslator',
    'LibreTranslator',
    'MyMemoryTranslator',
    'PapagoTranslator',
    'LingueeTranslator',
    'PonsTranslator',
    'QcriTranslator',
    'TencentTranslator',
    'YoudaoTranslator',
    'SizhiTranslator',
    'LLMGeneralTranslator',
    'NullTranslator',
    'kit'
]

__version__ = "0.2.4"
__author__ = "HZBHZB1234"
