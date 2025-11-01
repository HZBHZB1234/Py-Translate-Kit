from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
import logging

class BaseTranslator(ABC):
    """Base class for all translators / 所有翻译器的基类"""
    
    # API configuration template, can be overridden by subclasses
    # API配置模板，子类可以覆盖
    API_CONFIG_TEMPLATE = [
        {
            "id": "apikey",
            "describe": "API密钥",
            "addition": {"type": "pwd"}
        }
    ]
    
    def __init__(self, api_config: Optional[dict] = None, **kwargs):
        """
        Initialize translator with API configuration and function configuration
        使用API配置和函数配置初始化翻译器
        
        Args:
            api_config: API configuration / API配置
            **kwargs: Function configuration parameters / 函数配置参数
        """
        self.api_config = api_config or {}
        self._function_config = {
            'timeout': 30,
            'retry_attempts': 3,
            'rate_limit_delay': 1.0,
            'batch_size': 10,
            **kwargs
        }
        self._user_config = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()

    @abstractmethod
    def _translate(self, text: str, src: str, dest: str, **kwargs) -> str:
        """
        Translate text from source language to destination language
        将文本从源语言翻译到目标语言
        
        Args:
            text: Text to translate / 要翻译的文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Translated text / 翻译后的文本
        """
        pass

    @abstractmethod
    def _translate_batch(self, texts: List[str], src: str, dest: str, **kwargs) -> List[str]:
        """
        Translate multiple texts in batch
        批量翻译多个文本
        
        Args:
            texts: List of texts to translate / 要翻译的文本列表
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of translated texts / 翻译后的文本列表
        """
        pass

    def translate(self, text: str, src: str, dest: str, **kwargs) -> str:
        """
        Translate text from source language to destination language
        将文本从源语言翻译到目标语言
        
        Args:
            text: Text to translate / 要翻译的文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Additional configuration parameters / 额外的配置参数
            
        Returns:
            Translated text / 翻译后的文本
        """
        # 合并所有配置
        config = {
            **self._function_config,
            **self.api_config,
            **self._user_config,
            **kwargs
        }
        
        # 预处理文本
        processed_text = self._preprocess_text(text)
        
        # 执行翻译
        result = self._translate(processed_text, src, dest, **config)
        
        # 后处理文本
        return self._postprocess_text(result)

    def translate_batch(self, texts: List[str], src: str, dest: str, **kwargs) -> List[str]:
        """
        Translate multiple texts in batch
        批量翻译多个文本
        
        Args:
            texts: List of texts to translate / 要翻译的文本列表
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Additional configuration parameters / 额外的配置参数
            
        Returns:
            List of translated texts / 翻译后的文本列表
        """
        # 合并所有配置
        config = {
            **self._function_config,
            **self.api_config,
            **self._user_config,
            **kwargs
        }
        
        # 预处理文本
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # 执行批量翻译
        results = self._translate_batch(processed_texts, src, dest, **config)
        
        # 后处理文本
        return [self._postprocess_text(result) for result in results]

    def get_api_config_template(self) -> List[Dict[str, Any]]:
        """
        Get API configuration template (read-only)
        获取API配置模板（只读）
        
        Returns:
            List of API configuration items / API配置项列表
        """
        return self.API_CONFIG_TEMPLATE.copy()

    def get_function_config(self) -> Dict[str, Any]:
        """
        Get current function configuration
        获取当前函数配置
        
        Returns:
            Dictionary containing function configuration / 包含函数配置的字典
        """
        return self._function_config.copy()

    def update_function_config(self, **kwargs) -> None:
        """
        Update function configuration parameters
        更新函数配置参数
        
        Args:
            **kwargs: Function configuration parameters to update / 要更新的函数配置参数
        """
        self._function_config.update(kwargs)
        self._validate_config()

    def get_user_config(self) -> Dict[str, Any]:
        """
        Get current user configuration
        获取当前用户配置
        
        Returns:
            Dictionary containing user configuration / 包含用户配置的字典
        """
        return self._user_config.copy()

    def update_user_config(self, **kwargs) -> None:
        """
        Update user configuration parameters
        更新用户配置参数
        
        Args:
            **kwargs: User configuration parameters to update / 要更新的用户配置参数
        """
        self._user_config.update(kwargs)

    def update_api_config(self, **kwargs) -> None:
        """
        Update API configuration parameters
        更新API配置参数
        
        Args:
            **kwargs: API configuration parameters to update / 要更新的API配置参数
        """
        self.api_config.update(kwargs)
        self.logger.info("API configuration updated / API配置已更新")

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
        Validate function configuration parameters
        验证函数配置参数
        """
        if self._function_config.get('timeout') <= 0:
            raise ValueError("Timeout must be positive / 超时时间必须为正数")
        if self._function_config.get('retry_attempts') < 0:
            raise ValueError("Retry attempts cannot be negative / 重试次数不能为负数")
        if self._function_config.get('rate_limit_delay') < 0:
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
        return f"{self.__class__.__name__}(api_config_keys={list(self.api_config.keys())})"