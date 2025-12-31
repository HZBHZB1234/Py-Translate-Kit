"""
translator/base.py

翻译器基类，提供统一的翻译接口和可扩展的架构。
重构版本：简化翻译逻辑，添加方法选择参数
"""

import abc
import logging
import time
import threading
import requests
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, Callable, Any, Tuple
from functools import wraps
from dataclasses import dataclass
from enum import Enum


class TranslationError(Exception):
    """翻译相关异常基类"""
    pass


class ConfigurationError(TranslationError):
    """配置错误"""
    pass


class APIError(TranslationError):
    """API调用错误"""
    pass


class SplitStrategy(Enum):
    """文本分割策略"""
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph" 
    FIXED_LENGTH = "fixed_length"
    SEMANTIC = "semantic"


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    ADAPTIVE = "adaptive"


@dataclass
class TranslationConfig:
    """翻译配置数据类"""
    
    # API配置
    api_key: Dict[str, str] = None
    
    # 翻译参数
    source_lang: str = "auto"
    target_lang: str = "en"
    
    # 翻译方法选择
    method: str = "default"
    
    # 文本处理
    text_max_length: int = 2000
    split_strategy: SplitStrategy = SplitStrategy.SENTENCE
    enable_preprocessing: bool = True
    enable_postprocessing: bool = True
    
    # 重试与容错
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    timeout: float = 30.0
    
    # 并发设置
    max_workers: int = 5
    batch_size: int = 10
    
    # 高级功能
    enable_cache: bool = False
    cache_size: Optional[int] = None
    enable_metrics: bool = False
    debug_mode: bool = False

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = {}


@dataclass
class Metadata:
    """翻译器元数据信息"""
    console_url: str = ""
    description: str = ""
    documentation_url: str = ""
    short_description: str = ""
    usage_documentation: str = ""
    custom_override_content: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_override_content is None:
            self.custom_override_content = {}


def retry_on_failure(max_retries: int = 3, retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self: 'TranslatorBase', *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    self.logger.debug(f"第 {attempt + 1} 次尝试失败: {e}")
                    
                    if attempt == max_retries:
                        break
                        
                    # 计算延迟
                    delay = self._calculate_retry_delay(attempt, retry_strategy)
                    self.logger.debug(f"等待 {delay:.2f} 秒后重试")
                    time.sleep(delay)
                    
                    # 错误处理
                    self._handle_retry_error(e, attempt, **kwargs)
            
            # 所有重试都失败
            raise self._wrap_exception(last_exception, *args, **kwargs)
        return wrapper
    return decorator


def with_cache(func):
    """缓存装饰器"""
    @wraps(func)
    def wrapper(self:'TranslatorBase', text, source_lang, target_lang, **kwargs):
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if self._cache and cache_key in self._cache:
            self.logger.debug("缓存命中")
            return self._cache[cache_key]
        
        # 执行实际函数
        result = func(self, text, source_lang, target_lang, **kwargs)
        
        # 更新缓存
        if self._cache is not None:
            self._update_cache(cache_key, result)
            
        return result
    return wrapper


class TranslatorBase(abc.ABC):
    """
    翻译器基类，提供统一的翻译接口和可扩展架构
    """
    
    # 类属性：服务元信息（子类应覆盖）
    SERVICE_NAME = "base_translator"
    SUPPORTED_LANGUAGES = {}
    DEFAULT_CONFIG = TranslationConfig()
    DEFAULT_API_KEY = {}
    DESCRIBE_API_KEY = {}
    
    METADATA = Metadata(
        console_url="",
        description="Base translator class",
        documentation_url="",
        short_description="Base translator",
        usage_documentation=""
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 支持直接传入配置参数
        """
        self.config = config or self.DEFAULT_CONFIG
        
        # 初始化组件
        self.logger = self._setup_logger()
        self._thread_local = threading.local()
        self._cache = {} if self.config.enable_cache else None
        self._metrics = {} if self.config.enable_metrics else None
        self._executor = None
        self._session = requests.session()
        self._process_pre = []
        self._process_post = []
        
        if kwargs:
            self._update_config_from_kwargs(kwargs)
        
        self._update_inner_config()

        self.validate_config()
        
        self.logger.debug(f"{self.SERVICE_NAME} 初始化完成")

    def update_config(self, config: Optional[TranslationConfig] = None, **kwargs):
        """更新翻译类中的config，语法逻辑与初始化时类似
        Args:
            config: 为该次操作应用特殊配置
            kwargs: 单次特殊配置额外参数
            
        Returns:
            无返回结果，直接修改实例的config属性
        """
        if config is not None:
            self.config = config
        
        if kwargs:
            self._update_config_from_kwargs(kwargs)
        
        self._update_inner_config()

        self.validate_config()
        
    def get_metadata(self) -> Dict[str, Any]:
        """获取翻译器元数据信息"""
        return {
            "console_url": self.METADATA.console_url,
            "description": self.METADATA.description,
            "documentation_url": self.METADATA.documentation_url,
            "short_description": self.METADATA.short_description,
            "usage_documentation": self.METADATA.usage_documentation,
            "custom_override_content": self.METADATA.custom_override_content.copy() if self.METADATA.custom_override_content else {},
        }
    
    def get_console_url(self) -> str:
        """获取控制台URL"""
        return self.METADATA.console_url
    
    def get_description(self) -> str:
        """获取详细描述"""
        return self.METADATA.description
    
    def get_documentation_url(self) -> str:
        """获取文档URL"""
        return self.METADATA.documentation_url
    
    def get_short_description(self) -> str:
        """获取简要说明"""
        return self.METADATA.short_description
    
    def get_usage_documentation(self) -> str:
        """获取使用文档"""
        return self.METADATA.usage_documentation
    
    def get_custom_content(self) -> Dict[str, Any]:
        """获取自定义覆盖内容"""
        return self.METADATA.custom_override_content.copy() if self.METADATA.custom_override_content else {}
    
    # ==================== 核心翻译接口 ====================
    
    def translate(self, text: Union[str, List[str]], 
                  source_lang: Optional[str] = None,
                  target_lang: Optional[str] = None,
                  method: Optional[str] = None,
                  config: Optional[str] = None,
                  **kwargs) -> Union[str, List[str]]:
        """
        智能翻译主接口
        该接口支持多种翻译方法，并根据输入文本长度选择合适的翻译策略，自动处理并发翻译，缓存翻译结果，提供可靠的重试机制，并提供高级功能如速率限制、使用量统计等。
        只有text参数必要，其余参数仅为方便补全，逻辑上都是单次调用时的覆盖配置。
        部分特殊method可能需要额外的kwargs参数，具体请参考各子类实现文档。
        
        Args:
            text: 输入文本，支持字符串或字符串列表
            source_lang: 源语言，默认使用配置
            target_lang: 目标语言，默认使用配置
            method: 翻译方法选择，默认使用配置
            config: 为该次操作应用特殊配置
            **kwargs: 单次特殊配置额外参数
            
        Returns:
            翻译结果，保持输入格式
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        self._validate_languages(source_lang, target_lang)
        
        if config or kwargs:
            _temp_old_config = self.config
            self.update_config(config, **kwargs)          
        
        # 根据输入类型选择处理方式
        if isinstance(text, str):
            result = self._translate_single(text, source_lang, target_lang, method, **kwargs)
        elif isinstance(text, list):
            result = self._translate_batch(text, source_lang, target_lang, method, **kwargs)
        else:
            raise ValueError(f"不支持的文本类型: {type(text)}，只支持 str 和 List[str]")
        
        if config or kwargs:
            self.update_config(_temp_old_config)
        
        return result

    # ==================== 核心翻译实现 ====================
    
    def _translate_single(self, text: str, source_lang: str, target_lang: str, 
                         method: Optional[str] = None, **kwargs) -> str:
        """单文本翻译"""
        # 选择翻译方法
        method = method or self.config.method
        translate_func = self._select_translate_method(method)
        
        # 根据文本长度选择策略
        if len(text) <= self.config.text_max_length:
            return self._translate_call(self, translate_func, text, source_lang, target_lang, **kwargs)
        else:
            return self._translate_long_text(text, source_lang, target_lang, translate_func, **kwargs)

    def _translate_batch(self, texts: List[str], source_lang: str, target_lang: str,
                        method: Optional[str] = None, **kwargs) -> List[str]:
        """批量翻译"""
        if len(texts) == 1:
            return [self._translate_single(texts[0], source_lang, target_lang, method, **kwargs)]
        
        # 选择翻译方法
        method = method or self.config.method
        translate_func = self._select_translate_method(method)
        
        return self._process_batch_with_cache(
            texts, source_lang, target_lang, translate_func, **kwargs
        )

    def _select_translate_method(self, method: Optional[str] = None) -> Callable:
        """
        选择翻译方法
        
        Args:
            method: 方法名称，None表示使用默认方法
            **kwargs: 额外参数
            
        Returns:
            翻译函数
        """
        if method is None:
            return self._translate_default
        
        # 子类可以重写此方法以支持多种翻译方法
        method_name = f"_translate_{method}"
        if hasattr(self, method_name):
            return getattr(self, method_name)
        else:
            self.logger.debug(f"未知翻译方法: {method}，使用默认方法")
            return self._translate_default

    def _translate_long_text(self, text: str, source_lang: str, target_lang: str,
                            translate_func: Callable, **kwargs) -> str:
        """长文本翻译"""
        self.logger.debug(f"文本过长 ({len(text)} 字符)，进行分割翻译")
        
        # 分割文本
        chunks = self._split_long_text(text, **kwargs)
        if isinstance(chunks, str):
            chunks = [chunks]
            
        self.logger.debug(f"分割为 {len(chunks)} 个片段")
        
        # 并行翻译各个片段
        if len(chunks) > 1 and self.config.max_workers > 1:
            translated_chunks = self._translate_parallel(chunks, source_lang, target_lang, translate_func, **kwargs)
        else:
            # 串行翻译
            translated_chunks = []
            for chunk in chunks:
                translated = translate_func(chunk, source_lang, target_lang, **kwargs)
                translated_chunks.append(translated)
        
        # 合并结果
        result = self._merge_translated_texts(translated_chunks, **kwargs)
            
        return result

    @with_cache
    @retry_on_failure(max_retries=3, retry_strategy=RetryStrategy.EXPONENTIAL)
    def _translate_call(self, translate_func: Callable, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """包装翻译函数"""
        self.logger.debug(f"直接翻译: {text[:50]}...")
        
        # 预处理文本
        processed_text = self._preprocess_text(text, **kwargs)
        
        # 应用速率限制
        self._apply_rate_limiting()
        
        # 调用API
        response = translate_func(processed_text, source_lang, target_lang, **kwargs)
        
        # 解析响应
        result = self._parse_api_response(response, **kwargs)
        
        # 后处理结果
        final_result = self._postprocess_text(result, **kwargs)
        
        # 更新使用量统计
        self._update_usage_metrics(text, final_result)
        
        return final_result

    def _translate_parallel(self, texts: List[str], source_lang: str, target_lang: str,
                           translate_func: Callable, **kwargs) -> List[str]:
        """并行翻译"""
        self.logger.debug(f"并行翻译 {len(texts)} 个文本")
        return self._process_batch_parallel(texts, source_lang, target_lang, translate_func, **kwargs)

    # ==================== 批量处理逻辑 ====================
    
    def _process_batch_with_cache(self, texts: List[str], source_lang: str, target_lang: str, 
                                 translate_func: Callable, **kwargs) -> List[str]:
        """
        带缓存的批量处理
        
        Args:
            texts: 文本列表
            source_lang: 源语言
            target_lang: 目标语言
            translate_func: 翻译函数
            **kwargs: 额外参数
            
        Returns:
            翻译结果列表
        """
        # 缓存检查
        cached_results = []
        remaining_texts = []
        remaining_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            if self._cache and cache_key in self._cache:
                self.logger.debug(f"缓存命中: {text[:50]}...")
                cached_results.append((i, self._cache[cache_key]))
            else:
                remaining_texts.append(text)
                remaining_indices.append(i)
        
        # 如果所有文本都在缓存中，则直接返回结果
        if not remaining_texts:
            return self._merge_batch_results(texts, cached_results, [], [])
        
        # 处理未缓存的内容
        processed_results = self._process_batch_parallel(remaining_texts, source_lang, target_lang, translate_func, **kwargs)
        
        # 更新缓存
        if self._cache is not None:
            for i, result in enumerate(processed_results):
                cache_key = self._get_cache_key(remaining_texts[i], source_lang, target_lang)
                self._update_cache(cache_key, result)
        
        # 合并结果
        return self._merge_batch_results(texts, cached_results, processed_results, remaining_indices)

    def _merge_batch_results(self, original_texts: List[str], 
                            cached_results: List[Tuple[int, str]],
                            processed_results: List[str],
                            processed_indices: List[int]) -> List[str]:
        """
        合并批量处理结果
        """
        # 初始化结果列表
        results = [None] * len(original_texts)
        
        # 填充缓存的结果
        for index, result in cached_results:
            results[index] = result
            
        # 填充新处理的结果
        for i, result in enumerate(processed_results):
            original_index = processed_indices[i]
            results[original_index] = result
            
        return results

    # ==================== 文本处理 ====================
    
    def _split_long_text(self, text: str, **kwargs) -> Union[str, List[str]]:
        """长文本分割"""
        if len(text) <= self.config.text_max_length:
            return text
            
        self.logger.debug(f"文本过长 ({len(text)} 字符)，进行分割")
        
        strategy = kwargs.get('split_strategy', self.config.split_strategy)
        
        if strategy == SplitStrategy.SENTENCE:
            return self._split_by_sentence(text, **kwargs)
        elif strategy == SplitStrategy.PARAGRAPH:
            return self._split_by_paragraph(text, **kwargs)
        elif strategy == SplitStrategy.FIXED_LENGTH:
            return self._split_by_fixed_length(text, **kwargs)
        elif strategy == SplitStrategy.SEMANTIC:
            return self._split_by_semantic(text, **kwargs)
        else:
            return self._split_by_fixed_length(text, **kwargs)

    def _merge_translated_texts(self, fragments: List[str], **kwargs) -> str:
        """合并翻译后的文本片段"""
        if len(fragments) == 1:
            return fragments[0]
            
        # 简单的空格合并，子类可以覆盖实现更智能的合并
        return ' '.join(fragments)

    def _preprocess_text(self, text: str, **kwargs) -> str:
        """文本预处理"""
        if not self.config.enable_preprocessing:
            return text
            
        processed = text
        for pre_func in self._process_pre:
            processed = pre_func(processed, **kwargs)
        return processed

    def _postprocess_text(self, text: str, **kwargs) -> str:
        """后处理"""
        if not self.config.enable_postprocessing:
            return text
            
        processed = text
        for post_func in self._process_post:
            processed = post_func(processed, **kwargs)
        
        return processed

    # ==================== 必须由子类实现的方法 ====================
    
    @abc.abstractmethod
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用默认翻译API - 必须由子类实现
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: API特定参数
            
        Returns:
            API原始响应
        """
        pass

    @abc.abstractmethod
    def _parse_api_response(self, response: Any, **kwargs) -> str:
        """
        解析API响应 - 必须由子类实现
        
        Args:
            response: API响应对象
            **kwargs: 解析参数
            
        Returns:
            解析后的翻译文本
        """
        pass

    def _update_inner_config(self):
        """将self.config的内容更新至类中"""
        if self.DESCRIBE_API_KEY:
            for targetKeyName in self.config.api_key:
                DescribeAPI = [d for d in self.DESCRIBE_API_KEY if d['id'] == targetKeyName][0]
                setattr(self, targetKeyName, self.config.api_key.get(targetKeyName))
                self.logger.debug(f"设置{DescribeAPI['name']} 内容: {getattr(self, targetKeyName)}")

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取特殊API方法的引用规范
        
        Returns:
            包含特殊API方法信息的字典，格式为:
            {
                "method_name": {
                    "description": "方法描述",
                    "parameters": "参数说明",
                    "return_type": "返回值类型",
                    "example": "使用示例"
                }
            }
        """
        # 默认实现返回空字典，子类应覆盖此方法以提供特殊API信息
        return {}

    # ==================== 分割策略实现 ====================
    
    def _split_by_sentence(self, text: str, **kwargs) -> List[str]:
        """按句子分割"""
        import re
        sentences = re.split(r'[.!?。！？]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_paragraph(self, text: str, **kwargs) -> List[str]:
        """按段落分割"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_by_fixed_length(self, text: str, **kwargs) -> List[str]:
        """按固定长度分割"""
        max_len = kwargs.get('max_length', self.config.text_max_length)
        chunks = []
        
        for i in range(0, len(text), max_len):
            chunk = text[i:i + max_len]
            
            # 尝试在句子边界分割
            if i + max_len < len(text):
                last_period = max(
                    chunk.rfind('.'),
                    chunk.rfind('!'),
                    chunk.rfind('?'),
                    chunk.rfind('。'),
                    chunk.rfind('！'),
                    chunk.rfind('？')
                )
                if last_period > max_len * 0.5:  # 避免过小的片段
                    chunk = chunk[:last_period + 1]
                    
            chunks.append(chunk)
            
        return chunks

    def _split_by_semantic(self, text: str, **kwargs) -> List[str]:
        """语义分割（需要子类实现或使用外部库）"""
        self.logger.debug("语义分割未实现，回退到固定长度分割")
        return self._split_by_fixed_length(text, **kwargs)

    # ==================== 并发处理 ====================
    
    def _process_batch_parallel(self, texts: List[str], source_lang: str, target_lang: str,
                               translate_func: Callable, **kwargs) -> List[str]:
        """并行处理批次"""
        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
            
        # 创建futures并保持与输入文本的对应关系
        futures = []
        for text in texts:
            future = self._executor.submit(
                self._translate_call, translate_func, text, source_lang, target_lang, **kwargs
            )
            futures.append(future)
            
        # 按照提交顺序收集结果，确保顺序一致
        results = []
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self.logger.error(f"并行翻译失败: {e}")
                results.append("")  # 错误时返回空字符串
                
        return results

    # ==================== 错误处理与重试 ====================
    
    def _calculate_retry_delay(self, attempt: int, strategy: RetryStrategy) -> float:
        """计算重试延迟"""
        if strategy == RetryStrategy.EXPONENTIAL:
            return min(2 ** attempt, 60)  # 指数退避，最大60秒
        elif strategy == RetryStrategy.LINEAR:
            return min(attempt * 2, 30)   # 线性增长，最大30秒
        elif strategy == RetryStrategy.ADAPTIVE:
            return min(2 ** attempt, 45)  # 自适应延迟
        else:
            return min(2 ** attempt, 30)

    def _handle_retry_error(self, error: Exception, attempt: int, **kwargs):
        """处理重试错误"""
        error_type = type(error).__name__
        
        if "rate" in str(error).lower() or "limit" in str(error).lower():
            # 速率限制错误，延长等待时间
            time.sleep(min(2 ** (attempt + 2), 120))
        elif "timeout" in str(error).lower():
            # 超时错误，可能网络问题
            pass

    def _wrap_exception(self, error: Exception, *args, **kwargs) -> TranslationError:
        """包装异常"""
        if isinstance(error, TranslationError):
            return error
            
        error_msg = f"翻译失败: {error}"
        return APIError(error_msg)

    # ==================== 速率限制 ====================
    
    def _apply_rate_limiting(self):
        """应用速率限制"""
        if not hasattr(self._thread_local, 'last_request_time'):
            self._thread_local.last_request_time = 0
            
        current_time = time.time()
        time_since_last = current_time - self._thread_local.last_request_time
        
        min_interval = getattr(self, 'MIN_REQUEST_INTERVAL', 0.1)
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
            
        self._thread_local.last_request_time = time.time()

    # ==================== 配置管理 ====================
    
    def _update_config_from_kwargs(self, kwargs: Dict):
        """从kwargs更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            elif key in self.DEFAULT_API_KEY:
                self.config.api_key[key] = value
            else:
                self.logger.debug(f"忽略未知配置项: {key}")

    def update_config(self, **kwargs):
        """更新配置"""
        self._update_config_from_kwargs(kwargs)
        self.validate_config()

    def validate_config(self):
        """验证配置"""
        if not self.DEFAULT_API_KEY and not self.config.api_key:
            raise ConfigurationError("API密钥未配置")
            
        if not self.config.target_lang:
            raise ConfigurationError("目标语言未配置")
        
        if self.DESCRIBE_API_KEY:
            for DescribeAPI in self.DESCRIBE_API_KEY:
                if DescribeAPI.get('required', False):
                    targetKeyName = DescribeAPI.get('id')
                    if not hasattr(self, targetKeyName) or not getattr(self, targetKeyName):
                        raise ConfigurationError(f'配置项{targetKeyName}不存在或未配置')
                    
                targetKeyType = DescribeAPI.get('type')
                targetKeyContent = getattr(self, targetKeyName)
                if targetKeyType == 'string' and targetKeyContent and not isinstance(targetKeyContent, str):
                    warnings.warn(f'配置项{targetKeyName}类型错误，应为字符串类型', RuntimeWarning)
                elif targetKeyType == 'number' and targetKeyContent and not isinstance(targetKeyContent, (int, float)):
                    warnings.warn(f'配置项{targetKeyName}类型错误，应为数字类型', RuntimeWarning)
                elif targetKeyType == 'boolean' and targetKeyContent and not isinstance(targetKeyContent, bool):
                    warnings.warn(f'配置项{targetKeyName}类型错误，应为布尔类型', RuntimeWarning)

    # ==================== 缓存管理 ====================
    
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """生成缓存键"""
        return f"{source_lang}_{target_lang}_{hash(text)}"

    def _update_cache(self, key: str, value: str):
        """更新缓存"""
        if self.config.cache_size:
            if len(self._cache) >= self.config.cache_size:
                # 简单的LRU策略：移除第一个元素
                self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value

    def enable_memory_cache(self, max_size: Optional[int] = None):
        """启用内存缓存"""
        self.config.enable_cache = True
        self.config.cache_size = max_size
        self._cache = {}

    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()

    # ==================== 服务信息 ====================
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()

    def validate_language(self, lang_code: str, lang_type: str = 'target') -> bool:
        """验证语言代码"""
        supported = self.get_supported_languages()
        
        if lang_code == 'auto' and lang_type == 'source':
            return True
            
        return lang_code in supported

    def _validate_languages(self, source_lang: str, target_lang: str):
        """验证语言对"""
        if not self.validate_language(source_lang, 'source'):
            raise ValueError(f"不支持的源语言: {source_lang}")
            
        if not self.validate_language(target_lang, 'target'):
            raise ValueError(f"不支持的目标语言: {target_lang}")

    def get_usage(self) -> Dict[str, Any]:
        """获取使用情况"""
        return self._metrics or {}

    # ==================== 钩子方法 ====================
    
    def add_preprocess(self, func: Callable):
        """添加预处理函数"""
        self._process_pre.append(func)

    def add_postprocess(self, func: Callable):
        """添加后处理函数"""
        self._process_post.append(func)

    def clear_preprocess(self):
        """清除所有预处理函数"""
        self._process_pre.clear()
        
    def clear_postprocess(self):
        """清除所有后处理函数"""
        self._process_post.clear()
    
    def _update_usage_metrics(self, original_text: str, translated_text: str):
        """更新使用量统计（子类可覆盖）"""
        if not self.config.enable_metrics:
            return
            
        chars_translated = len(original_text)
        self._metrics.setdefault('chars_translated', 0)
        self._metrics['chars_translated'] += chars_translated
        self._metrics.setdefault('request_count', 0)
        self._metrics['request_count'] += 1

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"translator.{self.SERVICE_NAME}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    # ==================== 上下文管理器支持 ====================
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """清理资源"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    # ==================== 工具方法 ====================
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self._metrics.copy() if self._metrics else {}