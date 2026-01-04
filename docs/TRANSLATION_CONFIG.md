# 翻译配置参数详解

本文档详细介绍了 Py-Translate-Kit 中 [TranslationConfig](file:///e:/desktop/limbus%20transfer/Py-Translate-Kit/translatekit/kit.py#L287-L317) 类的所有配置参数，帮助用户更好地理解和使用该翻译工具包。

## 配置参数分类

### 1. API配置

- **api_setting**: `Dict[str, str] = None`
  - 用于存储API密钥的字典，不同翻译服务需要不同的密钥格式
  - 默认为None，若未提供则初始化为空字典
  - 使用示例：`{"appkey": "your_app_key", "secret": "your_secret"}`

### 2. 翻译参数

- **source_lang**: `str = "auto"`
  - 源语言代码，指定待翻译文本的语言
  - 默认为"auto"，表示自动检测语言
  - 支持的语言代码因翻译服务而异

- **target_lang**: `str = "en"`
  - 目标语言代码，指定翻译后的语言
  - 默认为"en"（英语）

- **method**: `str = "default"`
  - 翻译方法选择，用于指定使用哪种翻译策略
  - 默认为"default"方法

### 3. 文本处理

- **text_max_length**: `int = 2000`
  - 单次翻译文本的最大长度
  - 默认值为2000字符，超过此长度的文本将被分块处理

- **split_strategy**: `SplitStrategy = SplitStrategy.SENTENCE`
  - 文本分割策略，可选值包括：
    - [SplitStrategy.SENTENCE](translatekit/base.py#L615-L620): 按句子分割
    - [SplitStrategy.PARAGRAPH](translatekit/base.py#L621-L625): 按段落分割
    - [SplitStrategy.FIXED_LENGTH](translatekit/base.py#L626-L650): 按固定长度分割
    - [SplitStrategy.SEMANTIC](translatekit/base.py#L651-L655): 语义分割(待实现)

- **enable_preprocessing**: `bool = True`
  - 是否启用预处理功能
  - 默认启用，预处理需要手动添加相关函数
  - 预处理函数列表默认为空

- **enable_postprocessing**: `bool = True`
  - 是否启用后处理功能
  - 默认启用，后处理需要手动添加相关函数
  - 后处理函数列表默认为空

### 4. 重试与容错

- **max_retries**: `int = 3`
  - 最大重试次数，当翻译请求失败时的重试次数
  - 默认为3次

- **retry_strategy**: `RetryStrategy = RetryStrategy.EXPONENTIAL`
  - 重试策略，可选值包括：
    - [RetryStrategy.EXPONENTIAL](translatekit/base.py#L687-L696): 指数退避策略
    - [RetryStrategy.LINEAR](translatekit/base.py#L687-L696): 线性退避策略
    - [RetryStrategy.ADAPTIVE](translatekit/base.py#L687-L696): 自适应策略

- **timeout**: `float = 30.0`
  - 请求超时时间（秒）
  - 默认为30.0秒

### 5. 并发设置

- **max_workers**: `int = 5`
  - 最大工作线程数，用于并发处理翻译任务
  - 默认为5个线程

- **batch_size**: `int = 10`
  - 批处理大小，批量翻译时每批处理的文本数量
  - 默认为10条

### 6. 高级功能

- **enable_cache**: `bool = False`
  - 是否启用缓存功能
  - 默认关闭，开启后可缓存翻译结果，自动匹配相同文本，可以减少重复翻译

- **cache_size**: `Optional[int] = None`
  - 缓存大小限制
  - 默认为None，表示无限制

- **enable_metrics**: `bool = False`
  - 是否启用性能指标收集
  - 默认关闭，开启后可以追踪翻译使用量

- **debug_mode**: `bool = False`
  - 是否启用调试模式
  - 默认关闭，开启后会将logger.level设置为DEBUG，输出更多日志信息

## 使用示例

```python
import translatekit as tkit

# 创建带自定义配置的翻译器
config = tkit.TranslationConfig(
    api_setting={"appkey": "your_app_key"},
    debug_mode=True,
    enable_cache=True,
    cache_size=1000,
    source_lang="zh",
    target_lang="en",
    text_max_length=5000,
    max_retries=5,
    timeout=60.0
)

# 创建翻译器实例
translator = tkit.BaiduTranslator(config=config)

# 使用翻译器
result = translator.translate("你好，世界！")
print(result)
```
