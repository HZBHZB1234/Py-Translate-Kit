from typing import List, Tuple, Union, Dict, Any
import jsonpatch
from copy import deepcopy
import json
import re
from functools import lru_cache


class TranslateKitError(Exception):
    '''翻译工具包异常类'''
    pass

def compare_json(json1: Dict, json2: Dict) -> List:
    '''比对JSON对象，返回差异'''
    patch = jsonpatch.make_patch(json1, json2)
    return patch

def apply_patch(json1: Dict, patch: List) -> Dict:
    '''应用JSON补丁，返回结果'''
    return jsonpatch.apply_patch(json1, patch)

def flatten_with_paths(data: Union[Dict, List], prefix: str = "") -> List[Dict[str, Any]]:
    """
    将嵌套的数据结构扁平化为路径-值对的列表。
    对于数组，会先添加数组本身，再添加数组元素。
    
    Args:
        data: 要扁平化的数据
        prefix: 路径前缀，默认为空
    
    Returns:
        包含操作-路径-值对的列表
    """
    result = []
    
    def _flatten(current, path):
        # 如果是数组
        if isinstance(current, list):
            # 先添加数组本身（空数组）
            result.append({"path": path, "value": []})
            
            # 递归处理数组的每个元素
            for i, item in enumerate(current):
                _flatten(item, f"{path}/{i}")
                
        # 如果是字典/对象
        elif isinstance(current, dict):
            # 先添加对象本身（空字典）
            result.append({"path": path, "value": {}})
            
            # 递归处理对象的每个键值对
            for key, value in current.items():
                _flatten(value, f"{path}/{key}")
                
        # 如果是基本类型（字符串、数字、布尔值、None等）
        else:
            result.append({"path": path, "value": current})
    
    # 开始递归处理
    _flatten(data, prefix)
    return result

def deoptimize_patch(original_patch):
    """
    将 JSON Patch 拆分为多个单一操作的 patch，确保所有值为字符串类型
    
    Args:
        original_patch: 原始的 JSON Patch 对象（列表）
    
    Returns:
        拆分后的 JSON Patch 对象（列表的列表）
    """
    deoptimized_patches = []
    
    for operation in original_patch:
        op_type = operation.get('op')
        path = operation.get('path')
        
        # 处理不同类型的操作
        if op_type == 'add' or op_type == 'replace':
            value = operation.get('value')
            if not isinstance(value, list) and not isinstance(value, dict):
                # 非容器类型的值直接添加到结果中
                deoptimized_patches.append(operation)
                continue
            
            if op_type == 'replace':
                # 对于替换操作，先删除原有路径，再添加新值
                deoptimized_patches.append({
                    'op': 'remove',
                    'path': path
                })

            
            flat_json = flatten_with_paths(value)
            for item in flat_json:
                deoptimized_patches.append({
                    'op': "add",
                    'path': f"{path}{item['path']}",
                    'value': item['value']
                })
            
            
        else:
            # 其他操作直接添加到结果中
            deoptimized_patches.append(operation)
    
    return deoptimized_patches

def make_list_patch(_jsonpatch : List) -> List:
    '''从JSON补丁中提取值列表'''
    list_jsonpatch = [i['value'] for i in _jsonpatch if i['op'] in ['add', 'replace']]
    list_jsonpatch = [i for i in list_jsonpatch if isinstance(i, str)]
    return list_jsonpatch

def apply_list_patch(_jsonpatch : List, translate_list : List) -> List:
    '''将翻译后的值应用到JSON补丁中，返回更新后的补丁'''
    translation_iter = iter(translate_list)
    applied_patches = []
    
    for patch_op in _jsonpatch:
        if patch_op['op'] in ['add', 'replace']:
            try:
                if not isinstance(patch_op['value'], str):
                    applied_patches.append(patch_op)
                    continue
                applied_patches.append({**patch_op, 'value': next(translation_iter)})
            except StopIteration:
                raise TranslateKitError("Translation list has fewer items than expected.")
        else:
            applied_patches.append(patch_op)
    try:
        next(translation_iter)
        raise TranslateKitError("Translation list has more items than expected.")
    except StopIteration:
        pass
    return applied_patches

def filted_patchs(jsonpatchs : List[dict],
                          allow_list : List[str] = [".*"],
                          disallow_list : List[str] = ["$."],
                          disallow_op : List[str] = [],
                          disallow_type : List[type] = []) -> List[dict]:
    """通过正则表达式或op或类型过滤补丁，返回过滤后的补丁列表"""
    # 编译正则表达式
    allow_regex = re.compile("|".join(allow_list))
    disallow_regex = re.compile("|".join(disallow_list))
    
    # 过滤补丁
    filtered_patchs = []
    for patch in jsonpatchs:
        path = patch.get('path')
        op = patch.get('op')
        value = patch.get('value',None)
        if (allow_regex.search(path) and
            not disallow_regex.search(path) and
            not op in disallow_op and
            not isinstance(value, tuple(disallow_type))):
            filtered_patchs.append(patch)
    return filtered_patchs

def apply_filtered_patchs(original_jsonpatchs : List[dict],
                          filted_jsonpatchs : List[dict],
                          allow_list : List[str] = ['.*'],
                          disallow_list : List[str] = ["$."],
                          disallow_op : List[str] = [],
                          disallow_type : List[type] = []) -> List[dict]:
    """恢复被过滤的补丁，返回恢复后的JsonPatch列表"""
    # 编译正则表达式
    allow_regex = re.compile("|".join(allow_list))
    disallow_regex = re.compile("|".join(disallow_list))
    
    result = original_jsonpatchs.copy()
    _filted_jsonpatchs = deepcopy(filted_jsonpatchs)
    for index, patch in enumerate(original_jsonpatchs):
        path = patch.get('path')
        op = patch.get('op')
        value = patch.get('value',None)
        if (allow_regex.search(path) and
            not disallow_regex.search(path) and
            not op in disallow_op and
            not isinstance(value, tuple(disallow_type))):
            result[index] = _filted_jsonpatchs.pop(0)

    return result

class ProperNounMatcher:
    """
    专有名词匹配器（简化版）
    
    支持三种匹配模式：
    1. unordered: 无论顺序匹配（专有名词中的所有单词都出现，不考虑顺序）
    2. sequential: 顺序匹配（专有名词单词按顺序出现，可间隔）
    3. continuous: 连续匹配（专有名词单词连续出现）
    
    只返回匹配到的专有名词在原始列表中的索引
    """
    
    def __init__(self, proper_nouns: List[str]):
        """
        初始化匹配器
        
        Args:
            proper_nouns: 专有名词列表
        """
        self.proper_nouns = proper_nouns
        self._build_patterns()
    
    def _build_patterns(self):
        """构建各种匹配模式的正则表达式"""
        self.patterns = {
            'unordered': [],
            'sequential': [],
            'continuous': []
        }
        
        for idx, noun in enumerate(self.proper_nouns):
            # 清理和分割专有名词
            clean_noun = re.sub(r'\s+', ' ', noun.strip())
            words = clean_noun.split()
            
            if not words:
                continue
                
            # 转义单词中的特殊字符
            escaped_words = [re.escape(word) for word in words]
            
            # 连续匹配模式：单词必须连续出现
            continuous_pattern = r'\b' + r'\s+'.join(escaped_words) + r'\b'
            self.patterns['continuous'].append(
                (idx, re.compile(continuous_pattern, re.IGNORECASE))
            )
            
            # 顺序匹配模式：单词按顺序出现，可间隔
            sequential_pattern = r'\b.*?\b'.join(escaped_words)
            sequential_pattern = r'(?:(?<=\W)|^)' + sequential_pattern + r'(?:(?=\W)|$)' 
            self.patterns['sequential'].append(
                (idx, re.compile(sequential_pattern, re.IGNORECASE | re.DOTALL))
            )
            
            # 无论顺序匹配：所有单词都出现，不考虑顺序
            # 使用正向肯定预查确保所有单词都出现
            unordered_parts = [fr'(?=.*?\b{word}\b)' for word in escaped_words]
            unordered_pattern = ''.join(unordered_parts) + r'.*'
            self.patterns['unordered'].append(
                (idx, re.compile(unordered_pattern, re.IGNORECASE | re.DOTALL))
            )
    
    def match_single(self, text: str, mode: str = 'continuous') -> List[int]:
        """
        匹配单个文本，返回匹配到的专有名词索引列表
        
        Args:
            text: 要匹配的文本
            mode: 匹配模式，可选 'unordered', 'sequential', 'continuous'
            
        Returns:
            匹配到的专有名词索引列表
        """
        if mode not in self.patterns:
            raise ValueError(f"无效的匹配模式: {mode}。可选: {list(self.patterns.keys())}")
        
        matched_indices = []
        
        for idx, pattern in self.patterns[mode]:
            if pattern.search(text):
                matched_indices.append(idx)
        
        return matched_indices
    
    def match_multiple(self, texts: List[str], mode: str = 'continuous') -> List[List[int]]:
        """
        批量匹配多个文本，返回每个文本匹配到的专有名词索引列表
        
        Args:
            texts: 文本列表
            mode: 匹配模式
            
        Returns:
            每个文本匹配到的专有名词索引列表
        """
        return [self.match_single(text, mode) for text in texts]