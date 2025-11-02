from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any, Callable
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import re

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
        _preprocess_text() -> str                      # 子类单个文本预处理
        _postprocess_text() -> str                     # 子类单个文本后处理
        _preprocess_batch() -> List[Union[str,dict,List]]    # 子类批量文本预处理
        _postprocess_batch() -> List[Union[str,dict,List]]   # 子类批量文本后处理
        _validate_config() -> None                     # 配置验证
        get_usage_info() -> Dict[str, Any]             # 获取使用信息
        get_supported_languages() -> List[str]         # 获取支持的语言
        validate_language() -> bool                    # 验证语言代码
        
        # 新增的高级处理方法
        _handle_single_text() -> str                   # 单个文本高级处理
        _handle_batch_texts() -> List[Union[str,dict,List]] # 批量文本高级处理
        _split_long_text() -> List[str]                # 长文本分割
        _merge_split_results() -> str                  # 分割结果合并
        
    Optional class attributes that subclasses can override:
    以下类属性是可选的，子类可以覆盖：
        API_CONFIG_TEMPLATE    # API配置模板
        _function_config       # 函数配置参数
        _user_config           # 用户配置参数
        Describe               # 服务描述
        
    Public methods for external use:
    供外部使用的公共方法：
        translate() -> str                        # 单个文本翻译
        translate_batch() -> List[Union[str,dict,List]]      # 批量文本翻译
        get_api_config_template() -> List[Dict[str, Any]]    # 获取API配置模板
        get_service_description()                 # 获取服务描述
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
        'max_text_length': 5000,           # 最大文本长度
        'split_strategy': 'sentence',      # 分割策略：sentence/paragraph/fixed
        'split_separators': ['.', '。', '!', '！', '?', '？', '\n\n'],  # 分割分隔符
        'chunk_size': 500,                 # 固定分割时的块大小
        'overlap_size': 50,                # 分割重叠大小
        'max_workers': 3,                  # 线程池最大工作线程数
        'max_retries': 3,                  # 最大重试次数
        'retry_delay': 1,                  # 重试延迟（秒）
        'request_timeout': 30,             # 请求超时时间
        'rate_limit_per_second': 5,        # 每秒请求限制
    }
    
    # User configuration, similar to apikey, include other user configurations, can be overridden by subclasses
    # 用户配置，类似于apikey，包含其他的用户配置，子类可以覆盖
    _user_config = {}
    
    # Describe translator, not called in class
    # 描述内容，不在类中调用
    Describe = "Base Translator"
    
    # 线程池和重试池相关属性
    _thread_pool = None
    _request_queue = Queue()
    _rate_limiter = None

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
        
        # 初始化线程池
        self._init_thread_pool()
        
        # 初始化速率限制器
        self._init_rate_limiter()
        
        self._validate_config()

    def _init_thread_pool(self):
        """初始化线程池"""
        max_workers = self._function_config.get('max_workers', 3)
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)

    def _init_rate_limiter(self):
        """初始化速率限制器"""
        self._last_request_time = 0
        self._request_lock = threading.Lock()

    def _apply_rate_limit(self):
        """应用速率限制"""
        rate_limit = self._function_config.get('rate_limit_per_second', 5)
        if rate_limit <= 0:
            return
            
        min_interval = 1.0 / rate_limit
        
        with self._request_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
                
            self._last_request_time = time.time()

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
        
        # 使用高级处理机制处理单个文本
        def translation_work():
            # 预处理文本：先进行基类内建预处理，再进行子类预处理
            base_processed_text = self._builtin_preprocess_text(text, **config)
            processed_text = self._preprocess_text(base_processed_text, **config)
            
            # 执行翻译
            result = self._translate(processed_text, src, dest, **config)
            
            # 后处理文本：先进行子类后处理，再进行基类内建后处理
            subclass_processed_result = self._postprocess_text(result, **config)
            final_result = self._builtin_postprocess_text(subclass_processed_result, **config)
            
            return final_result
        
        # 调用高级处理方法
        return self._handle_single_text(translation_work, text, src, dest, **config)

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
        
        # 使用高级处理机制处理批量文本
        def batch_translation_work():
            # 批量预处理：先进行基类内建批量预处理，再进行子类批量预处理
            base_processed_texts = self._builtin_preprocess_batch(texts, **config)
            processed_texts = self._preprocess_batch(base_processed_texts, **config)
            
            # 执行批量翻译
            results = self._translate_batch(processed_texts, src, dest, **config)
            
            # 批量后处理：先进行子类批量后处理，再进行基类内建批量后处理
            subclass_processed_results = self._postprocess_batch(results, **config)
            final_results = self._builtin_postprocess_batch(subclass_processed_results, **config)
            
            return final_results
        
        # 调用高级批量处理方法
        return self._handle_batch_texts(batch_translation_work, texts, src, dest, **config)

    def _handle_single_text(self, translation_func: Callable, text: str, src: str, dest: str, **kwargs) -> str:
        """
        Advanced handling for single text translation with retry, rate limiting, and text splitting
        单个文本翻译的高级处理，包括重试、速率限制和文本分割
        
        Args:
            translation_func: Translation function to execute / 要执行的翻译函数
            text: Text to translate / 要翻译的文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Translated text / 翻译后的文本
        """
        max_retries = kwargs.get('max_retries', 3)
        max_text_length = kwargs.get('max_text_length', 5000)
        
        # 检查文本长度，决定是否需要分割
        if len(text) > max_text_length:
            self.logger.info(f"Text too long ({len(text)} chars), splitting into chunks")
            return self._handle_long_text(translation_func, text, src, dest, **kwargs)
        
        # 正常长度的文本处理（带重试机制）
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # 应用速率限制
                self._apply_rate_limit()
                
                # 执行翻译
                return translation_func()
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Translation attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries:
                    retry_delay = kwargs.get('retry_delay', 1)
                    time.sleep(retry_delay * (attempt + 1))  # 递增延迟
                else:
                    self.logger.error(f"All {max_retries} retry attempts failed")
                    raise last_exception
        
        # 理论上不会执行到这里
        raise last_exception

    def _handle_batch_texts(self, translation_func: Callable, texts: List[Union[str,dict,List]], 
                           src: str, dest: str, **kwargs) -> List[Union[str,dict,List]]:
        """
        Advanced handling for batch translation with parallel processing and error handling
        批量翻译的高级处理，包括并行处理和错误处理
        
        Args:
            translation_func: Batch translation function to execute / 要执行的批量翻译函数
            texts: List of texts to translate / 要翻译的文本列表
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of translated texts / 翻译后的文本列表
        """
        max_workers = kwargs.get('max_workers', 3)
        use_parallel = kwargs.get('use_parallel', True) and len(texts) > 1
        
        if not use_parallel or max_workers <= 1:
            # 串行处理
            return translation_func()
        
        # 并行处理
        self._init_thread_pool()
        
        # 将批量任务拆分为单个任务并行执行
        def single_translation_wrapper(index, single_text):
            def work():
                # 应用速率限制
                self._apply_rate_limit()
                return self.translate(single_text, src, dest, **kwargs)
            return index, work
        
        # 准备任务
        tasks = []
        for i, text_item in enumerate(texts):
            if isinstance(text_item, dict):
                text_to_translate = text_item.get('text', '')
            elif isinstance(text_item, list):
                text_to_translate = ' '.join(str(x) for x in text_item)
            else:
                text_to_translate = str(text_item)
                
            tasks.append(single_translation_wrapper(i, text_to_translate))
        
        # 提交任务到线程池
        futures = []
        for task in tasks:
            index, work_func = task
            future = self._thread_pool.submit(work_func)
            futures.append((index, future))
        
        # 收集结果
        results = [None] * len(texts)
        successful_count = 0
        
        for index, future in futures:
            try:
                result = future.result(timeout=kwargs.get('request_timeout', 30))
                results[index] = result
                successful_count += 1
            except Exception as e:
                self.logger.error(f"Failed to translate text at index {index}: {str(e)}")
                # 保留原始文本或设置错误标记
                if isinstance(texts[index], dict):
                    results[index] = {**texts[index], 'translation_error': str(e)}
                else:
                    results[index] = f"Translation Error: {str(e)}"
        
        self.logger.info(f"Batch translation completed: {successful_count}/{len(texts)} successful")
        return results

    def _handle_long_text(self, translation_func: Callable, text: str, src: str, dest: str, **kwargs) -> str:
        """
        Handle long text by splitting, translating chunks, and merging results
        处理长文本：分割、翻译分块、合并结果
        
        Args:
            translation_func: Translation function for chunks / 用于分块翻译的函数
            text: Long text to translate / 要翻译的长文本
            src: Source language code / 源语言代码
            dest: Destination language code / 目标语言代码
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Merged translated text / 合并后的翻译文本
        """
        # 分割文本
        chunks = self._split_long_text(text, **kwargs)
        self.logger.info(f"Split long text into {len(chunks)} chunks")
        
        # 翻译各个分块
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            self.logger.debug(f"Translating chunk {i+1}/{len(chunks)}")
            
            def chunk_translation():
                return self._handle_single_text(
                    lambda: self._translate(chunk, src, dest, **kwargs),
                    chunk, src, dest, **kwargs
                )
            
            try:
                translated_chunk = chunk_translation()
                translated_chunks.append(translated_chunk)
            except Exception as e:
                self.logger.error(f"Failed to translate chunk {i+1}: {str(e)}")
                # 对于失败的分块，保留原文或添加错误标记
                translated_chunks.append(f"[Translation Error: {str(e)}]")
        
        # 合并翻译结果
        merged_result = self._merge_split_results(translated_chunks, **kwargs)
        return merged_result

    def _split_long_text(self, text: str, **kwargs) -> List[str]:
        """
        Split long text into manageable chunks based on strategy
        根据策略将长文本分割为可管理的分块
        
        Args:
            text: Text to split / 要分割的文本
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            List of text chunks / 文本分块列表
        """
        strategy = kwargs.get('split_strategy', 'sentence')
        chunk_size = kwargs.get('chunk_size', 500)
        overlap_size = kwargs.get('overlap_size', 50)
        separators = kwargs.get('split_separators', ['.', '。', '!', '！', '?', '？', '\n\n'])
        
        if strategy == 'fixed':
            # 固定长度分割
            return self._split_by_fixed_length(text, chunk_size, overlap_size)
        elif strategy == 'sentence':
            # 按句子分割
            return self._split_by_sentences(text, separators, chunk_size)
        elif strategy == 'paragraph':
            # 按段落分割
            return self._split_by_paragraphs(text, chunk_size)
        else:
            # 默认使用句子分割
            return self._split_by_sentences(text, separators, chunk_size)

    def _split_by_fixed_length(self, text: str, chunk_size: int, overlap_size: int) -> List[str]:
        """按固定长度分割文本"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # 如果不在文本末尾，尝试在句子边界处分割
            if end < text_length:
                # 查找合适的分割点
                for separator in ['.', '。', '!', '！', '?', '？', ' ', '\n']:
                    last_sep_pos = text.rfind(separator, start, end)
                    if last_sep_pos != -1 and last_sep_pos > start + chunk_size // 2:
                        end = last_sep_pos + len(separator)
                        break
            
            chunks.append(text[start:end])
            start = end - overlap_size  # 应用重叠
            
            if start >= text_length:
                break
        
        return chunks

    def _split_by_sentences(self, text: str, separators: List[str], max_chunk_size: int) -> List[str]:
        """按句子分割文本"""
        if not separators:
            separators = ['.', '。', '!', '！', '?', '？']
        
        # 构建正则表达式模式来匹配句子分隔符
        pattern = '|'.join(re.escape(sep) for sep in separators)
        sentences = re.split(f'({pattern})', text)
        
        # 重新组合句子，考虑最大块大小
        chunks = []
        current_chunk = ""
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # 如果当前块加上新句子不会超过限制，或者当前块为空
            if len(current_chunk) + len(sentence) <= max_chunk_size or not current_chunk:
                current_chunk += sentence
                i += 1
            else:
                # 当前块已满，开始新块
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                i += 1
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def _split_by_paragraphs(self, text: str, max_chunk_size: int) -> List[str]:
        """按段落分割文本"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果当前块加上新段落不会超过限制，或者当前块为空
            if len(current_chunk) + len(paragraph) <= max_chunk_size or not current_chunk:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += paragraph
            else:
                # 当前块已满，开始新块
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def _merge_split_results(self, translated_chunks: List[str], **kwargs) -> str:
        """
        Merge translated chunks back into a coherent text
        将翻译后的分块合并为连贯的文本
        
        Args:
            translated_chunks: List of translated chunks / 翻译后的分块列表
            **kwargs: Configuration parameters / 配置参数
            
        Returns:
            Merged text / 合并后的文本
        """
        # 简单的合并策略：用空格连接
        # 子类可以覆盖此方法实现更复杂的合并逻辑
        return ' '.join(translated_chunks)

    def get_api_config_template(self) -> List[Dict[str, Any]]:
        """
        Get API configuration template (read-only)
        获取API配置模板（只读）
        
        Returns:
            List of API configuration items / API配置项列表
        """
        return self.API_CONFIG_TEMPLATE.copy()

    def get_service_description(self):
        """
        Get service description (read-only)
        获取服务描述（只读）
        
        Returns:
            Whatever you want to add / 你想添加的任何东西
        """
        return self.Describe

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
        
        # 如果线程池配置发生变化，重新初始化
        if 'max_workers' in kwargs:
            if self._thread_pool:
                self._thread_pool.shutdown(wait=True)
                self._thread_pool = None
            self._init_thread_pool()
            
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
        if self._function_config.get('timeout', 30) <= 0:
            raise ValueError("Timeout must be positive / 超时时间必须为正数")
        if self._function_config.get('retry_attempts', 3) < 0:
            raise ValueError("Retry attempts cannot be negative / 重试次数不能为负数")
        if self._function_config.get('rate_limit_delay', 0) < 0:
            raise ValueError("Rate limit delay cannot be negative / 速率限制延迟不能为负数")
        if self._function_config.get('max_text_length', 5000) <= 0:
            raise ValueError("Max text length must be positive / 最大文本长度必须为正数")
        if self._function_config.get('max_workers', 3) <= 0:
            raise ValueError("Max workers must be positive / 最大工作线程数必须为正数")

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
            List of postprocess

ed texts / 后处理后的文本列表
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

    def __del__(self):
        """清理资源"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(api_config_keys={list(self.api_config.keys())})"