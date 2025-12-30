# 从旧版逻辑到新版逻辑的适配指南

## 概述

本指南详细介绍了如何将旧版翻译服务实现迁移到新版基类逻辑。主要变化包括：
- 更改了API调用函数的命名约定
- 修改了初始化配置的逻辑
- 添加了DEFAULT_API_KEY常量
- 其他相关优化

## 主要变更内容

### 1. 翻译函数命名约定变更

#### 旧版
```python
def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
    # 实现API调用逻辑
    pass
```

#### 新版
```python
def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
    # 实现API调用逻辑，返回原始API响应
    pass

```
同时，注意如果原有的API调用含有多个方式，则需要分别改为多个`_translate_xxx`方法。详情参考[_select_translate_method函数](file:///e:/desktop/limbus%20transfer/Py-Translate-Kit/translatekit/base.py#L300-L325)。
### 2. 初始化配置逻辑变更

#### 旧版
```python
def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
    config = config or self.DEFAULT_CONFIG
    self.api_key = config.api_key.get('your_service_api_key', kwargs.get('api_key', ''))
    
    # 验证API密钥
    if not self.api_key:
        raise ConfigurationError("服务需要API密钥")
    
    # 更新配置中的API密钥
    config.api_key['your_service_api_key'] = self.api_key

    super().__init__(config, **kwargs)
    self.validate_config()
```

#### 新版
```python
def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
    # 注意：现在应该先调用super().__init__，然后设置特定属性
    super().__init__(config, **kwargs)
    
    # 在初始化后获取配置值
    self.api_key = self.config.api_key.get('your_service_api_key', '')
    
    # 验证配置
    self.validate_config()
```

### 3. 添加DEFAULT_API_KEY常量

#### 旧版
```python
class YourServiceTranslator(TranslatorBase):
    SERVICE_NAME = "your_service_translator"
    SUPPORTED_LANGUAGES = {...}
    # 没有DEFAULT_API_KEY
```

#### 新版
```python
class YourServiceTranslator(TranslatorBase):
    SERVICE_NAME = "your_service_translator"
    SUPPORTED_LANGUAGES = {...}
    
    DEFAULT_API_KEY = {
        "your_service_api_key": "",  # 服务特定的API密钥字段
        # 如有其他认证信息，也在此处定义
    }
    
    METADATA = Metadata(
        console_url="https://your-service-console-url.com",
        description="Your Service翻译服务实现...",
        documentation_url="https://your-service-documentation.com",
        short_description="Your Service翻译服务",
        usage_documentation="..."
    )
```

### 4. 添加DESCRIBE_API_KEY常量
使用DESCRIBE_API_KEY常量，可以提供更详细的API密钥描述，例如：
```python
    # DEFAULT_API_KEY常量定义
    DEFAULT_API_KEY = {
        "api_key": "",
        "folder_id": "",
        "speller": False,
        "format_HTML": False
    }
    
    # 相应的DESCRIBE_API_KEY常量定义
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "Yandex Cloud API密钥",
            "type": "string",
            "required": True,
            "description": "Yandex Cloud API密钥"
        },
        {
            "id": "folder_id",
            "name": "Yandex Cloud目录ID",
            "type": "string",
            "required": True,
            "description": "Yandex Cloud目录ID"
        },
        {
            "id": "speller",
            "name": "拼写检查",
            "type": "boolean",
            "required": False,
            "description": "是否启用拼写检查，默认为False"
        },
        {
            "id": "format_HTML",
            "name": "HTML格式",
            "type": "boolean",
            "required": False,
            "description": "是否将输入文本作为HTML格式，默认为False"
        }
    ]
```
### 5. 更新API
访问METADATA常量中的链接，确认是否需要更新API。


## 示例：适配DeeplTranslator

以下是将DeeplTranslator从旧逻辑适配到新逻辑的完整示例：

```python
# 旧版的方法
class DeepLTranslator(TranslatorBase):
    """DeepL翻译服务实现类"""
    
    # 省略无需修改的部分...
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化DeepL翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key, use_free_api等
        """
        config = config or self.DEFAULT_CONFIG
        self.api_key = config.api_key.get('deepl_api_key', kwargs.get('api_key', ''))
        self.use_free_api = kwargs.get('use_free_api', True)
        self.proxies = kwargs.get('proxies', None)
        self.glossary_id = kwargs.get('glossary_id', None)
        self.preserve_formatting = kwargs.get('preserve_formatting', False)
        self.tag_handling = kwargs.get('tag_handling', 'xml')
        self.context = kwargs.get('context', None)
        self.split_sentences = kwargs.get('split_sentences', '1')
        self.prevent_implicit_spaces = kwargs.get('prevent_implicit_spaces', False)
        self.formality = kwargs.get('formality', None)

        # 从环境变量或配置中获取API密钥
        if not self.use_free_api and not self.api_key:
            raise ConfigurationError("DeepL翻译需要API密钥")

        # 更新配置中的API密钥
        config.api_key['deepl_api_key'] = self.api_key

        super().__init__(config, **kwargs)
        self.validate_config()

        # 根据是否使用免费API设置正确的端点
        if not self.use_free_api:
            self.BASE_ENDPOINT = "https://api.deepl.com/v2/"

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.api_key:
            raise ConfigurationError("DeepL API密钥未配置")

# 新版的方法
class DeepLTranslator(TranslatorBase):
    """DeepL翻译服务实现类"""
    
    # 省略无需修改的部分...
    DEFAULT_API_KEY = {
        "api_key": "",
        "use_free_api": True,
        "proxies": None,
        "glossary_id": None,
        "preserve_formatting": False,
        "tag_handling": "xml",
        "context": None,
        "split_sentences": "1",
        "prevent_implicit_spaces": False,
        "formality": None
    }
    
    # 省略DESCRIBE_API_KEY部分...

    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化DeepL翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持api_key, use_free_api等
        """
        super().__init__(config, **kwargs)
        self.api_key = config.api_key.get('api_key','')
        self.use_free_api = config.api_key.get('use_free_api', True)
        self.proxies = config.api_key.get('proxies', None)
        self.glossary_id = config.api_key.get('glossary_id', None)
        self.preserve_formatting = config.api_key.get('preserve_formatting', False)
        self.tag_handling = config.api_key.get('tag_handling', 'xml')
        self.context = config.api_key.get('context', None)
        self.split_sentences = config.api_key.get('split_sentences', '1')
        self.prevent_implicit_spaces = config.api_key.get('prevent_implicit_spaces', False)
        self.formality = config.api_key.get('formality', None)


        self.validate_config()

        # 根据是否使用免费API设置正确的端点
        if not self.use_free_api:
            self.BASE_ENDPOINT = "https://api.deepl.com/v2/"

    def validate_config(self):
        """验证配置"""
        super().validate_config()
        if not self.api_key:
            raise ConfigurationError("DeepL API密钥未配置")
```

## 验证适配结果

完成适配后，请验证：

1. 所有必要的常量都已定义（特别是`DEFAULT_API_KEY`）
2. 初始化方法遵循新的模式
3. API调用逻辑已更名为`_translate_*`
4. 配置验证方法引用正确的配置字段
5. 适配的API参数已添加到`DESCRIBE_API_KEY`中
6. API文档链接正确且已是最新

## 注意事项

1. **API参数管理**：确保在[DEFAULT_API_KEY](file:///e:/desktop/limbus%20transfer/Py-Translate-Kit/translatekit/base.py#L64-L64)中声明所有需要的API参数字段
2. **初始化顺序**：在大多数情况下，应该先调用`super().__init__`，然后再设置特定属性
3. **配置验证**：确保验证方法检查的是正确配置的字段