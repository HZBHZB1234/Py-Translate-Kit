# Py-Translate-Kit 🌐

> 一个现代化、轻量级的Python翻译工具包，简化多平台翻译服务集成。

[![PyPI version](https://badge.fury.io/py/translatekit.svg)](https://badge.fury.io/py/translatekit)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/translatekit.svg)](https://pypi.org/project/translatekit/)

## ✨ 特性

- 🚀 **简单易用** - 直观的API设计，快速上手
- 🔌 **多平台支持** - 整合主流翻译服务（Google、DeepL、百度等）
- 🔄 **智能重试** - 网络不稳定时自动重试
- 💾 **缓存系统** - 提高重复翻译性能
- 📊 **性能统计** - 监控翻译性能和使用情况
- 🧩 **模块化设计** - 易于扩展和维护
- 🛡️ **类型安全** - 完整的类型注解支持

## 📦 安装

### 使用pip安装（推荐）

```bash
pip install translatekit
```

### 从源码安装

```bash
git clone https://github.com/HZBHZB1234/Py-Translate-Kit.git
cd Py-Translate-Kit
pip install -e .
```

## 🚀 快速开始

### 基础使用

```python
import translatekit as tkit

# 创建翻译器配置
config = tkit.TranslationConfig(
    api_key={"appkey": "your_app_key"},
    debug_mode=True,
    enable_cache=True,
    cache_size=1000
)

# 创建翻译器实例
translator = tkit.BaiduTranslator(
    config=config,
    source_lang="zh",
    target_lang="en"
)

# 使用翻译功能
text = "你好，世界！"
result = translator.translate(text)
print(result)  # 输出: Hello, World!
```

查看 [example.py](example.py) 获取更详细的使用示例。

## 🌍 支持的翻译服务

| 服务 | 类名 | 特点 |
|------|------|------|
| Google Translate | `GoogleTranslator` | 免费，高质量 |
| DeepL | `DeeplTranslator` | 高质量翻译 |
| 百度翻译 | `BaiduTranslator` | 中文支持优秀，支持文档翻译 |
| 微软翻译 | `MicrosoftTranslator` | 多语言支持，支持转写功能 |
| 腾讯翻译 | `TencentTranslator` | 中国服务，支持多种语言 |
| Yandex | `YandexTranslator` | 俄语支持好，支持语言检测 |
| LibreTranslate | `LibreTranslator` | 开源本地服务，支持语言检测 |
| MyMemory | `MymemoryTranslator` | 免费服务 |
| Papago | `PapagoTranslator` | 韩国Naver提供，支持多语种 |
| PONS | `PonsTranslator` | 词典翻译，支持多语言 |
| Linguee | `LingueeTranslator` | 词典和翻译记忆，支持多语言 |
| QCRI | `QcriTranslator` | 卡塔尔计算研究所提供，支持领域翻译 |
| 有道翻译 | `YoudaoTranslator` | 支持文档、图片、网页翻译等多种功能 |
| 腾讯混元 | `TencentHunyuanTranslator` | 腾讯混元大模型翻译 |
| 以及其他更多服务 | ... | 持续扩展中 |

## ⚙️ 配置选项

Py-Translate-Kit 提供了丰富的配置选项，详情请参阅 [TRANSLATION_CONFIG.md](TRANSLATION_CONFIG.md)。

## 🧩 工具箱

Py-Translate-Kit 提供了一些工具箱函数，帮助开发者处理翻译相关的任务。详情请参阅 [kit.md](kit.md)。

## 🛠️ 高级功能

### 缓存系统
可选的缓存机制，显著提高重复翻译的性能。

### 智能重试
在网络不稳定时自动重试，确保翻译请求的成功率。

### 性能统计
监控翻译性能和使用情况，帮助优化翻译流程。

### 批量与分块翻译
- **批量翻译**：高效处理多个文本
- **分块翻译**：处理长文本的自动分块功能

## 🏗️ 项目结构

```
translatekit/
├── __init__.py              # 导出主要类和函数
├── base.py                  # 所有翻译器的抽象基类
├── kit.py                   # 工具箱函数
├── google.py                # Google Translate 实现
├── baidu.py                 # 百度翻译实现
├── deepl.py                 # DeepL API 实现
├── microsoft.py             # Microsoft Translator 实现
├── tencent.py               # 腾讯翻译实现
├── yandex.py                # Yandex.Translate 实现
├── libre.py                 # LibreTranslate 实现
├── mymemory.py              # MyMemory 实现
├── papago.py                # Papago 实现
├── pons.py                  # PONS 实现
├── linguee.py               # Linguee 实现
├── qcri.py                  # QCRI 实现
├── ...                      # 其他翻译服务
```

## 🤝 贡献 & 碎碎念

本项目开始开发的原因是deeptranslate库的功能过于简单，且大量api已经失效。  
因此，为了更好地服务于Python开发者，我们开发了Py-Translate-Kit，提供了更加丰富的翻译服务，并加入了缓存、重试、性能统计等功能。  
欢迎大家提出宝贵意见，共同打造一个更加优秀的翻译工具包。 

鉴于当前开发者无力获取所有该仓库支持的翻译服务的apikey，如果出现了问题，请提交issue。  

~~github copilot说话咋这么肉麻~~

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 🐛 报告问题

如果遇到任何问题，请在 [GitHub Issues](https://github.com/yourusername/Py-Translate-Kit/issues) 中提交问题。
