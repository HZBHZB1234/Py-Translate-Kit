from typing import List, Optional, Union, Dict, Any
import jsonpatch


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

def make_list_patch(_jsonpatch : List) -> List:
    '''从JSON补丁中提取值列表'''
    list_jsonpatch = [i['value'] for i in _jsonpatch if i['op'] in ['add', 'replace']]
    return list_jsonpatch

def apply_list_patch(_jsonpatch : List, translate_list : List) -> List:
    '''将翻译后的值应用到JSON补丁中，返回更新后的补丁'''
    translation_iter = iter(translate_list)
    applied_patches = []
    
    for patch_op in _jsonpatch:
        if patch_op['op'] in ['add', 'replace']:
            try:
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
