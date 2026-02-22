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

relateForm = {
    "百度翻译服务": BaiduTranslator,
    "Google翻译服务": GoogleTranslator,
    "DeepL翻译服务": DeepLTranslator,
    "Microsoft翻译服务": MicrosoftTranslator,
    "Yandex Cloud翻译服务": YandexTranslator,
    "Libre翻译服务": LibreTranslator,
    "MyMemory翻译服务": MyMemoryTranslator,
    "Papago翻译服务": PapagoTranslator,
    "Linguee翻译服务": LingueeTranslator,
    "腾讯翻译服务": TencentTranslator,
    "有道翻译服务": YoudaoTranslator,
    "思知对话翻译服务": SizhiTranslator,
    "空翻译器(使用原文)": NullTranslator,
    "LLM通用翻译服务": LLMGeneralTranslator
}


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

__version__ = "0.2.8"
__author__ = "HZBHZB1234"
