from typing import List, Optional, Union, Dict, Any
import jsonpatch
from copy import deepcopy
import json


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
                    'op': 'delete',
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
