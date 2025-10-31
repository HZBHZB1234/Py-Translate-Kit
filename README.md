# Py-Translate-Kit
一个python库，简单而快捷的使用翻译服务，允许用户导入自定义脚本
** 还在开发，别到时候看见issue里有人问为什么搜不到**

## 简介

Py-Translate-Kit是一个轻量级的Python翻译工具包，旨在简化翻译服务的集成过程。
它内置了大量可用翻译服务，并允许用户通过自定义脚本来扩展翻译能力。

## 特性

- 简单易用的翻译接口
- 支持主流翻译服务
- 允许用户导入自定义翻译脚本
- 易于扩展的设计

## 安装

### 从PyPI安装（推荐）

```bash
pip install translatekit
```

### 从源码安装

我一会儿再来写这个

## 使用方法

### 作为命令行工具使用

```bash
py-translate --help
```

### 在Python代码中使用

```python
# 基础使用示例
import translatekit
translator = translatekit.TranslatorCore()
# 使用翻译功能
```

查看 [example.py](example.py) 获取更详细的使用示例。

## 目录结构

```
py_translate_kit/
├── __init__.py          # 包初始化文件
├── core.py              # 核心功能
└── main.py              # 主入口点
```

## 许可证

本项目采用 [LICENSE](LICENSE) 许可证。