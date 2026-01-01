# 翻译工具Kit函数详解

## 函数compare_json(json1, json2)
该函数用于比较两个json文件的差异，并返回jsonpatch格式的差异结果。

### 参数
- json1：第一个json文件
- json2：第二个json文件

### 返回值
- 返回jsonpatch格式的差异结果

### 示例
```python
json1 = {"name": "John", "age": 30}
json2 = {"name": "John", "age": 35}

kit.compare_json(json1, json2)
# 输出：[{"op": "replace", "path": "/age", "value": 35}]
```

### 注意事项
- 该函数依赖于jsonpatch库，需要先安装：`pip install jsonpatch`。
- 本函数完全基于jsonpatch.make_patch()函数实现，并没有额外增加功能。

## 函数apply_patch(json1, patch)
该函数用于将JSON补丁应用到原始JSON对象上，返回应用补丁后的结果。

### 参数
- json1：原始JSON对象
- patch：要应用的JSON补丁

### 返回值
- 返回应用补丁后的JSON对象

### 示例
```python
json1 = {"name": "John", "age": 30}
patch = [{"op": "replace", "path": "/age", "value": 35}]

kit.apply_patch(json1, patch)
# 输出：{"name": "John", "age": 35}
```

### 注意事项
- 该函数依赖于jsonpatch库，需要先安装：`pip install jsonpatch`。
- 本函数完全基于jsonpatch.apply_patch()函数实现，并没有额外增加功能。

## 函数make_list_patch(_jsonpatch)
从JSON补丁中提取值列表，只返回操作类型为'add'或'replace'且值为字符串的项。方便使用翻译函数进行批量翻译。

### 参数
- _jsonpatch：JSON补丁列表

### 返回值
- 返回字符串值的列表

### 示例
```python
jsonpatch = [
    {"op": "add", "path": "/name", "value": "John"},
    {"op": "add", "path": "/age", "value": 30},
    {"op": "replace", "path": "/city", "value": "New York"}
]
result = kit.make_list_patch(jsonpatch)

# 输出：["John", "New York"]
```

## 函数apply_list_patch(_jsonpatch, translate_list)
将翻译后的值应用到JSON补丁中，返回更新后的补丁。

### 参数
- _jsonpatch：原始JSON补丁列表
- translate_list：翻译后的字符串值列表

### 返回值
- 返回更新后的补丁列表

### 异常
- 如果翻译列表中的项数与预期不符，将抛出TranslateKitError异常

### 示例
```python
jsonpatch = [
    {"op": "add", "path": "/name", "value": "John"},
    {"op": "replace", "path": "/city", "value": "New York"}
]
translate_list = ["张三", "北京"]

result = kit.apply_list_patch(jsonpatch, translate_list)
# 输出：
# [
#   {"op": "add", "path": "/name", "value": "张三"},
#   {"op": "replace", "path": "/city", "value": "北京"}
# ]
```


## 函数flatten_with_paths(data, prefix="")
该函数将嵌套的数据结构扁平化为路径-值对的列表，方便使用jsonpatch库进行操作。

### 参数
- data：要扁平化的数据（可以是字典或列表）
- prefix：路径前缀，默认为空字符串

### 返回值
- 返回包含操作-路径-值对的列表

### 示例
```python
data = {"user": {"name": "John", "hobbies": ["reading", "swimming"]}}
result = kit.flatten_with_paths(data)

# 输出：
# [
#   {"path": "", "value": {}},
#   {"path": "/user", "value": {}},
#   {"path": "/user/name", "value": "John"},
#   {"path": "/user/hobbies", "value": []},
#   {"path": "/user/hobbies/0", "value": "reading"},
#   {"path": "/user/hobbies/1", "value": "swimming"}
# ]
```

## 函数deoptimize_patch(original_patch)
由于jsonpatch库的优化机制，可能会将一些操作合并为一个操作，导致value值变成列表或字典。本函数将JSON Patch拆分为多个单一操作的patch，确保所有值为字符串类型。

### 参数
- original_patch：原始的JSON Patch对象（列表）

### 返回值
- 拆分后的JSON Patch对象（列表的列表）

### 示例
```python
original_patch = [{"op": "add", "path": "/user", "value": {"name": "John", "age": 30}}]
result = kit.deoptimize_patch(original_patch)

# 输出：
# [
#   {"op": "add", "path": "/user", "value": {}},
#   {"op": "add", "path": "/user/name", "value": "John"},
#   {"op": "add", "path": "/user/age", "value": 30}
# ]
```

## 函数filted_patchs(jsonpatchs, allow_list, disallow_list, disallow_op)
通过正则表达式或操作类型过滤补丁，返回过滤后的补丁列表。

### 参数
- jsonpatchs：原始JSON补丁列表
- allow_list：允许的路径模式列表，默认为['.*']（允许所有）
- disallow_list：不允许的路径模式列表，默认为['$.']（不允许根路径）
- disallow_op：不允许的操作类型列表

### 返回值
- 返回过滤后的补丁列表

### 示例
```python
patches = [
    {"op": "add", "path": "/datalist/0/name", "value": "John"},
    {"op": "add", "path": "/data/age", "value": 30},
    {"op": "replace", "path": "/data/city", "value": "New York"}
]

filtered = kit.filted_patchs(
    patches,
    allow_list=[r".*/name", r"/data/.*"],
    disallow_op=["replace"]         # 不允许replace操作
)

# 输出：[{"op": "add", "path": "/datalist/0/name", "value": "John"},{"op": "add", "path": "/data/age", "value": 30},]
```

## 函数apply_filtered_patchs(original_jsonpatchs, filted_jsonpatchs, allow_list, disallow_list, disallow_op)
恢复被过滤的补丁，将过滤处理后的补丁重新合并到原始补丁列表中。

### 参数
- original_jsonpatchs：原始JSON补丁列表
- filted_jsonpatchs：经过过滤处理的补丁列表
- allow_list：允许的路径模式列表
- disallow_list：不允许的路径模式列表
- disallow_op：不允许的操作类型列表

### 返回值
- 返回恢复后的JSON补丁列表

### 示例
filted_patchs()函数的逆操作，此处不再赘述

# 完整示例
```python
from translatekit import *
import json
import jsonpatch
# 配置翻译参数
config = TranslationConfig(
    api_key={"appid":"filted","appkey":"secret"},
    target_lang="zh",  # 目标语言
    debug_mode=True,
    enable_cache=True,
    enable_metrics=True
)
# 创建翻译器实例
translator = BaiduTranslator(config=config)
with open(r"test_assets\EN_1D101A.json", "r", encoding="utf-8") as f:
    dicts = json.load(f)
jsonpatchs = kit.compare_json({}, dicts)
jsonpatchs = kit.deoptimize_patch(jsonpatchs)
allow_list = [r".*/teller", r".*/dialog", r".*/place", r".*/content"]
filted_jsonpatchs = kit.filted_patchs(jsonpatchs, allow_list=allow_list)
texts = kit.make_list_patch(filted_jsonpatchs)
[print(i) for i in texts]
results = translator.translate(texts)
[print(i) for i in results]
filted_jsonpatchs = kit.apply_list_patch(filted_jsonpatchs, results)
jsonpatchs = kit.apply_filtered_patchs(jsonpatchs, filted_jsonpatchs, allow_list=allow_list)
results = kit.apply_patch({}, jsonpatchs)
with open(r"test_assets\EN_1D101A_ZH.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)
print(translator.get_performance_metrics())
```