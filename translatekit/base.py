from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
import logging

class BaseTranslator(ABC):
    """Base class for all translators / 所有翻译器的基类"""
    
    def __init__(self, api_key: Optional[dict] = None, **kwargs):
        """
        Initialize translator with API key and configuration
        使用API密钥和配置初始化翻译器
        
        Args:
            api_key: API key for translation service / 翻译服务的API密钥
            **kwargs: Additional configuration parameters / 额外的配置参数
        """
        self.api_key = api_key
        self._config = {
            'timeout': 30,
            'retry_attempts': 3,
            'rate_limit_delay': 1.0,
            'batch_size': 10,
            **kwargs
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()

    @abstractmethod
    def _translate(self, text: str, src: str, dest: str) -> str:
        """
        Translate text from source language to destination language
        将文本从源语言翻译到目标语言
        
        Args:
            text: Text to translate / 要翻译的文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            
        Returns:
            Translated text / 翻译后的文本
        """
        pass

    @abstractmethod
    def _translate_batch(self, texts: List[str], src: str, dest: str) -> List[str]:
        """
        Translate multiple texts in batch
        批量翻译多个文本
        
        Args:
            texts: List of texts to translate / 要翻译的文本列表
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            
        Returns:
            List of translated texts / 翻译后的文本列表
        """
        pass
    @abstractmethod
    def translate(self, text: str, src: str, dest: str) -> str:
        """
        Translate text from source language to destination language
        将文本从源语言翻译到目标语言
        
        Args:
            text: Text to translate / 要翻译的文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            
        Returns:
            Translated text / 翻译后的文本
        """
        pass

    @abstractmethod
    def translate_batch(self, texts: List[str], src: str, dest: str) -> List[str]:
        """
        Translate multiple texts in batch
        批量翻译多个文本
        
        Args:
            texts: List of texts to translate / 要翻译的文本列表
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            
        Returns:
            List of translated texts / 翻译后的文本列表
        """
        pass

    def config(self) -> Dict[str, Any]:
        """
        Get current configuration
        获取当前配置
        
        Returns:
            Dictionary containing current configuration / 包含当前配置的字典
        """
        return self._config.copy()

    def update_config(self, **kwargs) -> None:
        """
        Update configuration parameters
        更新配置参数
        
        Args:
            **kwargs: Configuration parameters to update / 要更新的配置参数
        """
        self._config.update(kwargs)
        self._validate_config()

    def set_api_key(self, api_key: str) -> None:
        """
        Set or update API key
        设置或更新API密钥
        
        Args:
            api_key: New API key / 新的API密钥
        """
        self.api_key = api_key
        self.logger.info("API key updated / API密钥已更新")

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes
        获取支持的语言代码列表
        
        Returns:
            List of supported language codes / 支持的语言代码列表
        """
        return ['en', 'zh', 'es', 'fr', 'de', 'ja', 'ko', 'ru']

    def validate_language(self, lang: str) -> bool:
        """
        Validate if language code is supported
        验证语言代码是否受支持
        
        Args:
            lang: Language code to validate / 要验证的语言代码
            
        Returns:
            True if language is supported / 如果语言受支持则返回True
        """
        return lang in self.get_supported_languages()

    def _validate_config(self) -> None:
        """
        Validate configuration parameters
        验证配置参数
        """
        if self._config.get('timeout') <= 0:
            raise ValueError("Timeout must be positive / 超时时间必须为正数")
        if self._config.get('retry_attempts') < 0:
            raise ValueError("Retry attempts cannot be negative / 重试次数不能为负数")
        if self._config.get('rate_limit_delay') < 0:
            raise ValueError("Rate limit delay cannot be negative / 速率限制延迟不能为负数")

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before translation
        翻译前预处理文本
        
        Args:
            text: Input text / 输入文本
            
        Returns:
            Preprocessed text / 预处理后的文本
        """
        return text.strip()

    def _postprocess_text(self, text: str) -> str:
        """
        Postprocess text after translation
        翻译后处理文本
        
        Args:
            text: Translated text / 翻译后的文本
            
        Returns:
            Postprocessed text / 后处理后的文本
        """
        return text.strip()

    def _check_api_key(self) -> None:
        """
        Check if API key is set
        检查API密钥是否已设置
        """
        if not self.api_key:
            raise ValueError("API key is required but not set / API密钥是必需的但未设置")

    @abstractmethod
    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get API usage information (quota, remaining requests, etc.)
        获取API使用信息（配额、剩余请求数等）
        
        Returns:
            Dictionary with usage information / 包含使用信息的字典
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(api_key={'***' if self.api_key else None})"