from typing import Dict, List, Union
import importlib
class TranslationHelper:
    def get_json_patch(self, json1: Union[Dict,List], json2: Union[Dict,List]) -> List[Dict]:
        """比较两个JSON对象生成补丁"""
        try:
            self.jsonpatch = importlib.import_module('jsonpatch')
        except ImportError:
            raise ImportError("请安装jsonpatch库以使用此功能")
        return self.jsonpatch.make_patch(json1, json2).patch
    
    def apply_json_patch(self, json: Union[Dict,List], patch: List[Dict]) -> Union[Dict,List]:
        """应用JSON补丁"""
        try:
            self.jsonpatch = importlib.import_module('jsonpatch')
        except ImportError:
            raise ImportError("请安装jsonpatch库以使用此功能")
        return self.jsonpatch.apply_patch(json, patch)
    
    def _get_list_jsonpatch(self, json_patch: List[Dict]) -> List[str]:
        '''根据JSON补丁获取需要翻译的文本列表'''
        values_to_translate = [operation['value'] for operation in json_patch 
                    if operation['op'] in ['add', 'replace']]
        return values_to_translate
    
    def _apply_lsit_jsonpatch(self, translated_values: List[str], patch: List[Dict]):
        '''将翻译后的值重新整合进原始 patch 结构中'''
        translated_patch = []
        translation_index = 0
        for operation in patch:
            if operation['op'] in ['add', 'replace']:
                # 创建一个新操作，使用翻译后的值替换原值
                updated_operation = {**operation, 'value': translated_values[translation_index]}
                translated_patch.append(updated_operation)
                translation_index += 1
            else:
                # 对于其他操作类型，直接复制原始操作
                translated_patch.append(operation)
                
        return translated_patch