import translatekit as tkit

# 获取目标翻译器配置逻辑
default_api_key = tkit.BaiduTranslator.DEFAULT_API_KEY
describe_api_key = tkit.BaiduTranslator.DESCRIBE_API_KEY
for index, describe in enumerate(describe_api_key):
    print(f'''
          参数{index+1}
          参数ID：{describe["id"]}
          参数名称：{describe["name"]}
          参数是否必填：{describe["required"]}
          参数类型：{describe["type"]}
          参数描述：{describe["description"]}，
          ''')

# 可以通过打印TranslationConfig类来获取默认配置
print(tkit.TranslationConfig)

# 可以使用TranslationConfig类来配置翻译器参数
config = tkit.TranslationConfig(
    api_setting={"appkey": "your_app_key"},
    debug_mode=True,
    enable_cache=True,
    cache_size=1000
)

# 创建翻译器实例
translator = tkit.BaiduTranslator(
    config=config,
    # 也可以通过kwargs的方式传入并修改参数
    # 先判断并修改config中的参数，没有的话再修改config.api_setting中的参数
    source_lang="zh",
    target_lang="en",
    appid = "your_app_id"
)

text = "你好，世界！"

# 调用翻译器进行翻译
result = translator.translate(text)

print(result)

texts = ["你好，世界！", "晚安"]

# 调用翻译器进行批量翻译，翻译器会自动判断类型
results = translator.translate(texts)

print(results)

# 调用翻译器进行领域翻译
# 你可以在调用translate方法时传入参数method=以改变翻译方法
# 一般而言，也会提供一个单独的方法来调用其他翻译方法，如translate_with_domain

result_domain = translator.translate(text, method="domain", domain="news")
result_domain_ = translator.translate_with_domain(text, "news", "en")
print(result_domain)
print(result_domain_)

# 你可以在调用translate方法时传入参数来临时改变翻译配置
result = translator.translate(text, source_lang="zh", target_lang="en", text_max_length=5000)
print(result)

# 也可以使用update_config方法来更新翻译配置（永久）
translator.update_config(source_lang="zh", target_lang="en", text_max_length=5000)
result = translator.translate(text)
print(result)

# 通过get_supported_languages方法可以获取支持的语言列表
meta = translator.get_supported_languages()
print(meta)

# 通过get_special_api_reference方法可以获取翻译器的特殊函数参考
meta = translator.get_special_api_reference()
print(meta)

# 通过get_metadata方法可以获取翻译器的元数据
meta = translator.get_metadata()
print(meta)

# 也可以通过一系列方法来获取翻译器的单独元数据等
meta_console_url = translator.get_console_url()
print(meta_console_url)
meta_description = translator.get_description()
print(meta_description)
meta_documentation_url = translator.get_documentation_url()
print(meta_documentation_url)
meta_short_description = translator.get_short_description()
print(meta_short_description)
# 注：大部分翻译器还未实现get_usage_documentation方法
meta_usage_documentation = translator.get_usage_documentation()
print(meta_usage_documentation)
# 注：大部分翻译器还未实现get_custom_content方法
meta_custom_content = translator.get_custom_content()
print(meta_custom_content)

# 使用get_performance_metrics方法获取当次开销
usage = translator.get_performance_metrics()
print(usage)

# 使用clear_cache方法清除缓存
translator.clear_cache()

# 你可以通过add_preprocess和add_postprocess方法来添加预处理和后处理函数
# 预处理函数会在调用translate方法之前被调用
# 后处理函数会在调用translate方法之后被调用
# 预处理函数和后处理函数的调用顺序是按照添加的顺序
# 你可以通过clear_preprocess和clear_postprocess方法来清除所有预处理和后处理函数

translator.add_preprocess(lambda x: x.upper())
translator.add_postprocess(lambda x: x.lower())
result = translator.translate(text)
print(result)

translator.clear_preprocess()
translator.clear_postprocess()
result = translator.translate(text)
print(result)

# 这是默认config的配置逻辑，我将使用他来介绍各个参数功能

"""
class TranslationConfig:
    # API配置
    # 本文开头已经介绍了API配置的过程，这里不再赘述
    api_setting: Dict[str, str] = None
    
    # 目标语言和源语言
    source_lang: str = "auto"
    target_lang: str = "en"
    
    # 翻译方法选择
    method: str = "default"
    
    # 文本处理
    # 文本最大长度
    text_max_length: int = 2000
    # 文本分割策略
    split_strategy: SplitStrategy = SplitStrategy.SENTENCE
    # 启用文本预处理(需要自定义)
    enable_preprocessing: bool = True
    # 启用文本后处理(需要自定义)
    enable_postprocessing: bool = True
    
    # 重试与容错
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    timeout: float = 30.0
    
    # 并发设置
    # 并发请求数
    max_workers: int = 5
    # 批量请求数
    batch_size: int = 10
    
    # 启用缓存
    enable_cache: bool = False
    # 缓存大小上限
    cache_size: Optional[int] = None
    
    # 启用性能记录
    enable_metrics: bool = False
    # 调试模式(设置logget等级为DEBUG)
    debug_mode: bool = False
"""

# llm_general翻译器的传参比较特殊

config = tkit.TranslationConfig(
    api_setting={"api_key": "your_api_key",
                 "base_url": "https://api.openai.com/v1",
                 "user_prompt_base": "第一句话:{0}，第二句话:{1}，第三句话:{2}"},
    debug_mode=True,
    enable_cache=True,
    cache_size=1000
)

translator = tkit.LLMGeneralTranslator(
    config=config
)

translator.translate(["你好，世界！", "晚安", "再见"])