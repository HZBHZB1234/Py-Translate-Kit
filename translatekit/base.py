from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
import logging

class BaseTranslator(ABC):
    """
    Base class for all translators
    所有翻译器的基类
    
    Abstract methods that subclasses must implement:
    以下是抽象方法，子类必须实现：
        _translate() -> str
        _translate_batch() -> List[Union[str,dict,List]]
    These two methods are the actual translation methods
    这两个方法为翻译实际方法
    
    Optional methods that subclasses can override (with default implementations in base class):
    以下方法是可选的，子类可以覆盖（基类中已有默认实现）：
        _builtin_preprocess_text() -> str              # 基类内建单个文本预处理
        _builtin_postprocess_text() -> str             # 基类内建单个文本后处理
        _builtin_preprocess_batch() -> List[Union[str,dict,List]]    # 基类内建批量文本预处理
        _builtin_postprocess_batch() -> List[Union[str,dict,List]]   # 基类内建批量文本后处理
        _preprocess_text() -> str                      # 子类单个文本预处理
        _postprocess_text() -> str                     # 子类单个文本后处理
        _preprocess_batch() -> List[Union[str,dict,List]]    # 子类批量文本预处理
        _postprocess_batch() -> List[Union[str,dict,List]]   # 子类批量文本后处理
        _validate_config() -> None                     # 配置验证
        get_usage_info() -> Dict[str, Any]             # 获取使用信息
        get_supported_languages() -> List[str]         # 获取支持的语言
        validate_language() -> bool                    # 验证语言代码
        
    Optional class attributes that subclasses can override:
    以下类属性是可选的，子类可以覆盖：
        API_CONFIG_TEMPLATE    # API配置模板
        _function_config       # 函数配置参数
        _user_config           # 用户配置参数
        
    Public methods for external use:
    供外部使用的公共方法：
        translate() -> str                        # 单个文本翻译
        translate_batch() -> List[Union[str,dict,List]]      # 批量文本翻译
        get_api_config_template() -> List[Dict[str, Any]]    # 获取API配置模板
        get_function_config() -> Dict[str, Any]   # 获取函数配置
        update_function_config() -> None          # 更新函数配置
        get_user_config() -> Dict[str, Any]       # 获取用户配置
        update_user_config() -> None              # 更新用户配置
        update_api_config() -> None               # 更新API配置
        get_supported_languages() -> List[str]    # 获取支持的语言
        validate_language() -> bool               # 验证语言代码
    """
    
    # API configuration template, be used as reference, can be overridden by subclasses
    # API配置模板，将会作为参考，子类可以覆盖
    API_CONFIG_TEMPLATE = [
        {
            "id": "apikey",
            "describe": "API密钥",
            "addition": {"type": "pwd"}
        }
    ]

    # Function configuration, used for built-in text preprocessing methods, can be overridden by subclasses
    # 函数配置，用于使用内置的预处理文本方式，子类可以覆盖
    _function_config = {
            'timeout': 30,
            'retry_attempts': 3,
            'rate_limit_delay': 1.0,
            'batch_size': 10
        }
    
    # User configuration, similar to apikey, include other user configurations, can be overridden by subclasses
    # 用户配置，类似于apikey，包含其他的用户配置，子类可以覆盖
    _user_config = {}
    
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
            **self._function_config,
            **kwargs
        }
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
    def _translate_batch(self, texts: List[Union[str,dict,List]] , src: str, dest: str, **kwargs) -> List[Union[str,dict,List]]:
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
        
        # 预处理文本：先进行基类内建预处理，再进行子类预处理
        base_processed_text = self._builtin_preprocess_text(text, **config)
        processed_text = self._preprocess_text(base_processed_text, **config)
        
        # 执行翻译
        result = self._translate(processed_text, src, dest, **config)
        
        # 后处理文本：先进行子类后处理，再进行基类内建后处理
        subclass_processed_result = self._postprocess_text(result, **config)
        final_result = self._builtin_postprocess_text(subclass_processed_result, **config)
        
        return final_result

    def translate_batch(self, texts: List[Union[str,dict,List]], src: str, dest: str, **kwargs) -> List[Union[str,dict,List]]:
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
        
        # 批量预处理：先进行基类内建批量预处理，再进行子类批量预处理
        base_processed_texts = self._builtin_preprocess_batch(texts, **config)
        processed_texts = self._preprocess_batch(base_processed_texts, **config)
        
        # 执行批量翻译
        results = self._translate_batch(processed_texts, src, dest, **config)
        
        # 批量后处理：先进行子类批量后处理，再进行基类内建批量后处理
        subclass_processed_results = self._postprocess_batch(results, **config)
        final_results = self._builtin_postprocess_batch(subclass_processed_results, **config)
        
        return final_results

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

    def _builtin_preprocess_text(self, text: str, **kwargs) -> str:
        """
        Base class built-in text preprocessing before translation
        翻译前基类内建文本预处理
        
        Args:
            text: Input text / 输入文本
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Preprocessed text / 预处理后的文本
        """
        # 基类内建预处理逻辑
        # 例如：去除多余空格、标准化换行符等
        if isinstance(text, str):
            text = text.strip()
        return text

    def _builtin_postprocess_text(self, text: str, **kwargs) -> str:
        """
        Base class built-in text postprocessing after translation
        翻译后基类内建文本后处理
        
        Args:
            text: Translated text / 翻译后的文本
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Postprocessed text / 后处理后的文本
        """
        # 基类内建后处理逻辑
        # 例如：确保输出为字符串、处理特殊字符等
        if not isinstance(text, str):
            text = str(text)
        return text

    def _builtin_preprocess_batch(self, texts: List[Union[str,dict,List]], **kwargs) -> List[Union[str,dict,List]]:
        """
        Base class built-in batch preprocessing before translation
        翻译前基类内建批量预处理
        
        Args:
            texts: List of texts to preprocess / 要预处理的文本列表
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of preprocessed texts / 预处理后的文本列表
        """
        # 默认实现：对每个文本单独调用_builtin_preprocess_text
        return [self._builtin_preprocess_text(text, **kwargs) for text in texts]

    def _builtin_postprocess_batch(self, texts: List[Union[str,dict,List]], **kwargs) -> List[Union[str,dict,List]]:
        """
        Base class built-in batch postprocessing after translation
        翻译后基类内建批量后处理
        
        Args:
            texts: List of translated texts to postprocess / 要后处理的翻译后文本列表
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of postprocessed texts / 后处理后的文本列表
        """
        # 默认实现：对每个文本单独调用_builtin_postprocess_text
        return [self._builtin_postprocess_text(text, **kwargs) for text in texts]

    def _preprocess_text(self, text: str, **kwargs) -> str:
        """
        Subclass text preprocessing before translation (can be overridden by subclasses)
        翻译前子类文本预处理（子类可以覆盖）
        
        Args:
            text: Input text / 输入文本
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Preprocessed text / 预处理后的文本
        """
        # 子类可以覆盖此方法实现特定的预处理逻辑
        return text

    def _postprocess_text(self, text: str, **kwargs) -> str:
        """
        Subclass text postprocessing after translation (can be overridden by subclasses)
        翻译后子类文本后处理（子类可以覆盖）
        
        Args:
            text: Translated text / 翻译后的文本
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Postprocessed text / 后处理后的文本
        """
        # 子类可以覆盖此方法实现特定的后处理逻辑
        return text

    def _preprocess_batch(self, texts: List[Union[str,dict,List]], **kwargs) -> List[Union[str,dict,List]]:
        """
        Subclass batch preprocessing before translation (can be overridden by subclasses)
        翻译前子类批量预处理（子类可以覆盖）
        
        Args:
            texts: List of texts to preprocess / 要预处理的文本列表
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of preprocessed texts / 预处理后的文本列表
        """
        # 默认实现：对每个文本单独调用_preprocess_text
        return [self._preprocess_text(text, **kwargs) for text in texts]

    def _postprocess_batch(self, texts: List[Union[str,dict,List]], **kwargs) -> List[Union[str,dict,List]]:
        """
        Subclass batch postprocessing after translation (can be overridden by subclasses)
        翻译后子类批量后处理（子类可以覆盖）
        
        Args:
            texts: List of translated texts to postprocess / 要后处理的翻译后文本列表
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of postprocessed texts / 后处理后的文本列表
        """
        # 默认实现：对每个文本单独调用_postprocess_text
        return [self._postprocess_text(text, **kwargs) for text in texts]

    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get API usage information (quota, remaining requests, etc.)
        获取API使用信息（配额、剩余请求数等）
        
        Returns:
            Dictionary with usage information / 包含使用信息的字典
        """
        return {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(api_config_keys={list(self.api_config.keys())})"