"""
translator/base.py

翻译器基类，提供统一的翻译接口和可扩展的架构。
"""

import abc
import logging
import time
import threading
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


class TranslatorBase(abc.ABC):
    """
    翻译器基类，提供统一的翻译接口和可扩展架构
    """
    
    # 类属性：服务元信息（子类应覆盖）
    SERVICE_NAME = "base_translator"
    SUPPORTED_LANGUAGES = {}
    DEFAULT_CONFIG = TranslationConfig()
    
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
        
        if kwargs:
            self._update_config_from_kwargs(kwargs)
        
        self.validate_config()
        self.logger.info(f"{self.SERVICE_NAME} 初始化完成")

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
    
    def get_custom_override_content(self) -> Dict[str, Any]:
        """获取自定义覆盖内容"""
        return self.METADATA.custom_override_content.copy() if self.METADATA.custom_override_content else {}
    
    # ==================== 核心翻译接口 ====================
    
    def translate(self, text: Union[str, List, Dict], 
                  source_lang: Optional[str] = None,
                  target_lang: Optional[str] = None,
                  **kwargs) -> Union[str, List, Dict]:
        """
        智能翻译主接口，自动选择最佳处理策略
        
        Args:
            text: 输入文本，支持字符串、列表、字典
            source_lang: 源语言，默认使用配置
            target_lang: 目标语言，默认使用配置
            **kwargs: 额外参数
            
        Returns:
            翻译结果，保持输入格式
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        self._validate_languages(source_lang, target_lang)
        
        # 根据输入类型选择处理方式
        if isinstance(text, str):
            return self._translate_single(text, source_lang, target_lang, **kwargs)
        elif isinstance(text, list):
            return self._translate_batch(text, source_lang, target_lang, **kwargs)
        elif isinstance(text, dict):
            return self._translate_dict(text, source_lang, target_lang, **kwargs)
        else:
            raise ValueError(f"不支持的文本类型: {type(text)}")

    def translate_batch(self, texts: List[str],
                        source_lang: Optional[str] = None,
                        target_lang: Optional[str] = None,
                        **kwargs) -> List[str]:
        """批量翻译接口"""
        return self.translate(texts, source_lang, target_lang, **kwargs)

    def translate_with_strategy(self, text: str,
                                strategy: str = 'auto',
                                source_lang: Optional[str] = None,
                                target_lang: Optional[str] = None,
                                **kwargs) -> str:
        """
        指定策略的翻译接口（高级功能）
        
        Args:
            text: 输入文本
            strategy: 翻译策略 ('raw', 'chunk', 'parallel', 'auto')
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
            
        Returns:
            翻译结果
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang
        
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if self._cache and cache_key in self._cache:
            self.logger.debug("缓存命中")
            return self._cache[cache_key]
        
        if strategy == 'raw':
            result = self._translate_single_raw(text, source_lang, target_lang, **kwargs)
        elif strategy == 'chunk':
            result = self._translate_chunked(text, source_lang, target_lang, **kwargs)
        elif strategy == 'parallel':
            result = self._translate_parallel([text], source_lang, target_lang, **kwargs)[0]
        else:  # auto
            result = self._translate_single(text, source_lang, target_lang, **kwargs)
        
        # 更新缓存
        if self._cache is not None:
            self._update_cache(cache_key, result)
            
        return result

    # ==================== 文本处理管道 ====================
    
    def get_text_processing_pipeline(self) -> List[Callable]:
        """获取文本处理管道，子类可覆盖以重新定义流程"""
        return [
            self._preprocess_text,
            self._split_long_text,
            self._apply_translation,
            self._merge_translated_texts,
            self._postprocess_text
        ]

    def execute_pipeline(self, text: str, **kwargs) -> str:
        """执行文本处理管道"""
        pipeline = self.get_text_processing_pipeline()
        result = text
        
        for processor in pipeline:
            result = processor(result, **kwargs)
            self.logger.debug(f"处理器 {processor.__name__} 完成")
            
        return result

    def _preprocess_text(self, text: str, **kwargs) -> str:
        """文本预处理"""
        if not self.config.enable_preprocessing:
            return text
            
        processed = text.strip()
        processed = self._custom_preprocess(processed, **kwargs)
        
        return processed

    def _split_long_text(self, text: str, **kwargs) -> Union[str, List[str]]:
        """长文本分割"""
        if len(text) <= self.config.text_max_length:
            return text
            
        self.logger.info(f"文本过长 ({len(text)} 字符)，进行分割")
        
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

    def _apply_translation(self, text: Union[str, List[str]], 
                          source_lang: str, 
                          target_lang: str,
                          **kwargs) -> Union[str, List[str]]:
        """应用翻译"""
        if isinstance(text, str):
            return self._translate_single_raw(text, source_lang, target_lang, **kwargs)
        else:
            return self._translate_parallel(text, source_lang, target_lang, **kwargs)

    def _merge_translated_texts(self, fragments: List[str], **kwargs) -> str:
        """合并翻译后的文本片段"""
        if len(fragments) == 1:
            return fragments[0]
            
        # 简单的空格合并，子类可以覆盖实现更智能的合并
        return ' '.join(fragments)

    def _postprocess_text(self, text: str, **kwargs) -> str:
        """后处理"""
        if not self.config.enable_postprocessing:
            return text
            
        processed = text.strip()
        processed = self._custom_postprocess(processed, **kwargs)
        
        return processed

    # ==================== 必须由子类实现的方法 ====================
    
    @abc.abstractmethod
    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用具体翻译API - 必须由子类实现
        
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

    # ==================== 翻译策略实现 ====================
    
    def _translate_single(self, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """单文本翻译（自动策略选择）"""
        # 检查缓存
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if self._cache and cache_key in self._cache:
            self.logger.debug("缓存命中")
            return self._cache[cache_key]
        
        # 根据文本长度选择策略
        if len(text) > self.config.text_max_length:
            strategy = 'chunk'
        else:
            strategy = 'raw'
            
        result = self.translate_with_strategy(text, strategy, source_lang, target_lang, **kwargs)
        
        # 更新缓存
        if self._cache is not None:
            self._update_cache(cache_key, result)
            
        return result

    def _translate_single_raw(self, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """原始API翻译（无分割）"""
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if self._cache and cache_key in self._cache:
            self.logger.debug("缓存命中")
            return self._cache[cache_key]
        
        self.logger.debug(f"直接翻译: {text[:50]}...")
        
        # 应用速率限制
        self._apply_rate_limiting()
        
        # 重试机制
        response = self._retry_on_failure(
            self._call_translate_api,
            text, source_lang, target_lang, **kwargs
        )
        
        # 解析响应
        result = self._parse_api_response(response, **kwargs)
        
        # 更新使用量统计
        self._update_usage_metrics(text, result)
        
        # 更新缓存
        if self._cache is not None:
            self._update_cache(cache_key, result)
            
        return result

    def _translate_chunked(self, text: str, source_lang: str, target_lang: str, **kwargs) -> str:
        """分块翻译"""
        cache_key = self._get_cache_key(text, source_lang, target_lang)
        if self._cache and cache_key in self._cache:
            self.logger.debug("缓存命中")
            return self._cache[cache_key]
            
        self.logger.info("使用分块翻译策略")
        
        # 分割文本
        chunks = self._split_long_text(text, **kwargs)
        if isinstance(chunks, str):
            chunks = [chunks]
            
        self.logger.debug(f"分割为 {len(chunks)} 个片段")
        
        # 翻译各个片段
        translated_chunks = self._translate_parallel(chunks, source_lang, target_lang, **kwargs)
        
        # 合并结果
        result = self._merge_translated_texts(translated_chunks, **kwargs)
        
        # 更新缓存
        if self._cache is not None:
            self._update_cache(cache_key, result)
            
        return result

    def _translate_parallel(self, texts: List[str], source_lang: str, target_lang: str, **kwargs) -> List[str]:
        """并行翻译"""
        if len(texts) == 1:
            return [self._translate_single_raw(texts[0], source_lang, target_lang, **kwargs)]
            
        self.logger.info(f"并行翻译 {len(texts)} 个文本")
        
        # 检查缓存
        cached_results = []
        remaining_texts = []
        remaining_indices = []
        
        if self._cache is not None:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text, source_lang, target_lang)
                if cache_key in self._cache:
                    self.logger.debug(f"缓存命中: {text[:50]}...")
                    cached_results.append((i, self._cache[cache_key]))
                else:
                    remaining_texts.append(text)
                    remaining_indices.append(i)
        else:
            remaining_texts = texts
            remaining_indices = list(range(len(texts)))
            
        # 如果所有文本都在缓存中，则直接返回结果
        if not remaining_texts:
            results = [None] * len(texts)
            for index, result in cached_results:
                results[index] = result
            return results
            
        # 分批处理未缓存的文本
        batch_size = kwargs.get('batch_size', self.config.batch_size)
        batches = [remaining_texts[i:i + batch_size] for i in range(0, len(remaining_texts), batch_size)]
        
        results = []
        for batch in batches:
            batch_results = self._process_batch_parallel(batch, source_lang, target_lang, **kwargs)
            results.extend(batch_results)
            
        # 将结果保存到缓存中
        if self._cache is not None:
            for i, result in enumerate(results):
                cache_key = self._get_cache_key(remaining_texts[i], source_lang, target_lang)
                self._update_cache(cache_key, result)
                
        # 合并缓存的结果和新翻译的结果
        final_results = [None] * len(texts)
        
        # 填充缓存的结果
        for index, result in cached_results:
            final_results[index] = result
            
        # 填充新翻译的结果
        for i, result in enumerate(results):
            final_index = remaining_indices[i]
            final_results[final_index] = result
            
        return final_results

    def _translate_batch(self, texts: List[str], source_lang: str, target_lang: str, **kwargs) -> List[str]:
        """批量翻译（列表输入）"""
        # 检查缓存
        cached_results = []
        remaining_texts = []
        remaining_indices = []
        
        if self._cache is not None:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text, source_lang, target_lang)
                if cache_key in self._cache:
                    self.logger.debug(f"缓存命中: {text[:50]}...")
                    cached_results.append((i, self._cache[cache_key]))
                else:
                    remaining_texts.append(text)
                    remaining_indices.append(i)
        else:
            remaining_texts = texts
            remaining_indices = list(range(len(texts)))
            
        # 如果所有文本都在缓存中，则直接返回结果
        if not remaining_texts:
            results = [None] * len(texts)
            for index, result in cached_results:
                results[index] = result
            return results
            
        # 翻译未缓存的文本
        translated_texts = self._translate_parallel(remaining_texts, source_lang, target_lang, **kwargs)
        
        # 合并缓存的结果和新翻译的结果
        final_results = [None] * len(texts)
        
        # 填充缓存的结果
        for index, result in cached_results:
            final_results[index] = result
            
        # 填充新翻译的结果
        for i, result in enumerate(translated_texts):
            final_index = remaining_indices[i]
            final_results[final_index] = result
            
        return final_results

    def _translate_dict(self, text_dict: Dict, source_lang: str, target_lang: str, **kwargs) -> Dict:
        """字典翻译（保持结构）"""
        # 构建缓存键列表
        keys = list(text_dict.keys())
        texts = list(text_dict.values())
        cache_keys = [self._get_cache_key(text, source_lang, target_lang) for text in texts]
        
        # 检查缓存
        cached_results = {}
        remaining_items = {}
        
        if self._cache is not None:
            for key, text, cache_key in zip(keys, texts, cache_keys):
                if cache_key in self._cache:
                    self.logger.debug(f"缓存命中: {text[:50]}...")
                    cached_results[key] = self._cache[cache_key]
                else:
                    remaining_items[key] = text
        else:
            remaining_items = text_dict.copy()
            
        # 如果所有文本都在缓存中，则直接返回结果
        if not remaining_items:
            return cached_results
            
        # 提取未缓存的文本值
        remaining_keys, remaining_texts = zip(*remaining_items.items()) if remaining_items else ([], [])
        remaining_keys = list(remaining_keys)
        remaining_texts = list(remaining_texts)
        
        # 批量翻译未缓存的文本
        translated_texts = self._translate_batch(remaining_texts, source_lang, target_lang, **kwargs)
        
        # 保存新翻译结果到缓存
        if self._cache is not None:
            for i, text in enumerate(remaining_texts):
                cache_key = self._get_cache_key(text, source_lang, target_lang)
                self._update_cache(cache_key, translated_texts[i])
        
        # 组合最终结果
        final_result = {}
        final_result.update(cached_results)
        
        # 添加新翻译的结果
        for i, key in enumerate(remaining_keys):
            final_result[key] = translated_texts[i]
            
        return final_result

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
        self.logger.warning("语义分割未实现，回退到固定长度分割")
        return self._split_by_fixed_length(text, **kwargs)

    # ==================== 并发处理 ====================
    
    def _process_batch_parallel(self, texts: List[str], source_lang: str, target_lang: str, **kwargs) -> List[str]:
        """并行处理批次"""
        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
            
        futures = []
        for text in texts:
            future = self._executor.submit(
                self._translate_single_raw, text, source_lang, target_lang, **kwargs
            )
            futures.append(future)
            
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self.logger.error(f"并行翻译失败: {e}")
                results.append("")  # 错误时返回空字符串
                
        return results

    def get_executor(self, executor_type: str = 'thread', **kwargs):
        """获取执行器"""
        if executor_type == 'thread':
            return ThreadPoolExecutor(max_workers=kwargs.get('max_workers', self.config.max_workers))
        else:
            raise ValueError(f"不支持的执行器类型: {executor_type}")

    # ==================== 错误处理与重试 ====================
    
    def _retry_on_failure(self, func: Callable, *args, **kwargs) -> Any:
        """
        重试装饰器实现
        
        Args:
            func: 要重试的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        max_retries = kwargs.pop('max_retries', self.config.max_retries)
        retry_strategy = kwargs.pop('retry_strategy', self.config.retry_strategy)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                
                if attempt == max_retries:
                    break
                    
                # 计算延迟
                delay = self._calculate_retry_delay(attempt, retry_strategy)
                self.logger.info(f"等待 {delay:.2f} 秒后重试")
                time.sleep(delay)
                
                # 错误处理
                self._handle_retry_error(e, attempt, **kwargs)
        
        # 所有重试都失败
        raise self._wrap_exception(last_exception, *args, **kwargs)

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
            else:
                self.logger.warning(f"忽略未知配置项: {key}")

    def update_config(self, **kwargs):
        """更新配置"""
        self._update_config_from_kwargs(kwargs)
        self.validate_config()

    def validate_config(self):
        """验证配置"""
        if not self.config.api_key:
            raise ConfigurationError("API密钥未配置")
            
        if not self.config.target_lang:
            raise ConfigurationError("目标语言未配置")

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

    # ==================== 钩子方法（子类可覆盖） ====================
    
    def _custom_preprocess(self, text: str, **kwargs) -> str:
        """自定义预处理（子类可覆盖）"""
        return text

    def _custom_postprocess(self, text: str, **kwargs) -> str:
        """自定义后处理（子类可覆盖）"""
        return text

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
            
        logger.setLevel(
            logging.DEBUG if self.config.debug_mode else logging.INFO
        )
        
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
    
    def enable_debug_mode(self, level: str = 'basic'):
        """启用调试模式"""
        self.config.debug_mode = True
        self.logger.setLevel(logging.DEBUG)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self._metrics.copy() if self._metrics else {}
    
    # ==================== JSON补丁翻译 ====================

    def get_json_patch(self, json1: Union[Dict,List], json2: Union[Dict,List]) -> List[Dict]:
        """比较两个JSON对象生成补丁"""
        try:
            import jsonpatch
        except ImportError:
            raise ImportError("请安装jsonpatch库以使用此功能")
        return jsonpatch.make_patch(json1, json2).patch
    
    def apply_json_patch(self, json: Union[Dict,List], patch: List[Dict]) -> Union[Dict,List]:
        """应用JSON补丁"""
        try:
            import jsonpatch
        except ImportError:
            raise ImportError("请安装jsonpatch库以使用此功能")
        return jsonpatch.apply_patch(json, patch)
    
    def translate_jsonpatch(self, json_patch: List[Dict], source_lang: str, target_lang: str) -> List[Dict]:
        """
        翻译 JSON Patch 中的操作值
        
        此方法会筛选出 'add' 和 'replace' 操作，将其 'value' 字段进行翻译，
        并将翻译后的值重新组合成新的 JSON Patch。
        """
        # 提取需要翻译的值（仅针对 'add' 和 'replace' 操作）
        values_to_translate = [operation['value'] for operation in json_patch 
                            if operation['op'] in ['add', 'replace']]
        
        # 执行翻译操作
        translated_values = self.translate(values_to_translate, source_lang, target_lang)
        
        # 将翻译后的值重新整合进原始 patch 结构中
        translated_patch = []
        translation_index = 0
        for operation in json_patch:
            if operation['op'] in ['add', 'replace']:
                # 创建一个新操作，使用翻译后的值替换原值
                updated_operation = {**operation, 'value': translated_values[translation_index]}
                translated_patch.append(updated_operation)
                translation_index += 1
            else:
                # 对于其他操作类型，直接复制原始操作
                translated_patch.append(operation)
                
        return translated_patch