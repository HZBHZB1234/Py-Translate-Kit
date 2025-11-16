from typing import Dict, List, Union, Any, Optional
import importlib
import os
from abc import ABC, abstractmethod


class BaseFormatConverter(ABC):
    """基础格式转换器抽象类"""
    
    @abstractmethod
    def extract_text(self, source: Any) -> List[str]:
        """从源数据中提取需要翻译的文本"""
        pass
    
    @abstractmethod
    def apply_translation(self, source: Any, translated_texts: List[str]) -> Any:
        """将翻译后的文本应用回源数据"""
        pass


class JSONConverter(BaseFormatConverter):
    """JSON格式转换器"""
    
    def __init__(self):
        try:
            self.jsonpatch = importlib.import_module('jsonpatch')
        except ImportError:
            raise ImportError("请安装jsonpatch库以使用JSON转换功能")
    
    def extract_text(self, source: Union[Dict, List]) -> List[str]:
        """从JSON对象中提取需要翻译的文本"""
        return self._extract_text_recursive(source)
    
    def _extract_text_recursive(self, data: Any) -> List[str]:
        """递归提取JSON中的所有文本"""
        texts = []
        
        if isinstance(data, dict):
            for value in data.values():
                texts.extend(self._extract_text_recursive(value))
        elif isinstance(data, list):
            for item in data:
                texts.extend(self._extract_text_recursive(item))
        elif isinstance(data, str) and data.strip():
            # 只提取非空字符串
            texts.append(data)
        
        return texts
    
    def apply_translation(self, source: Union[Dict, List], translated_texts: List[str]) -> Union[Dict, List]:
        """将翻译后的文本应用回JSON对象"""
        return self._apply_translation_recursive(source, translated_texts.copy())
    
    def _apply_translation_recursive(self, data: Any, translated_texts: List[str]) -> Any:
        """递归应用翻译"""
        if isinstance(data, dict):
            return {key: self._apply_translation_recursive(value, translated_texts) 
                   for key, value in data.items()}
        elif isinstance(data, list):
            return [self._apply_translation_recursive(item, translated_texts) for item in data]
        elif isinstance(data, str) and data.strip():
            # 替换非空字符串
            return translated_texts.pop(0) if translated_texts else data
        else:
            return data
    
    def get_json_patch(self, json1: Union[Dict, List], json2: Union[Dict, List]) -> List[Dict]:
        """比较两个JSON对象生成补丁"""
        return self.jsonpatch.make_patch(json1, json2).patch
    
    def apply_json_patch(self, json: Union[Dict, List], patch: List[Dict]) -> Union[Dict, List]:
        """应用JSON补丁"""
        return self.jsonpatch.apply_patch(json, patch)
    
    def extract_text_from_patch(self, json_patch: List[Dict]) -> List[str]:
        """从JSON补丁中提取需要翻译的文本"""
        return [operation['value'] for operation in json_patch 
                if operation['op'] in ['add', 'replace'] and 
                isinstance(operation.get('value'), str) and 
                operation['value'].strip()]
    
    def apply_translation_to_patch(self, translated_texts: List[str], patch: List[Dict]) -> List[Dict]:
        """将翻译后的文本应用回JSON补丁"""
        translated_patch = []
        translation_index = 0
        
        for operation in patch:
            if (operation['op'] in ['add', 'replace'] and 
                isinstance(operation.get('value'), str) and 
                operation['value'].strip()):
                updated_operation = operation.copy()
                updated_operation['value'] = translated_texts[translation_index]
                translated_patch.append(updated_operation)
                translation_index += 1
            else:
                translated_patch.append(operation)
                
        return translated_patch


class TextConverter(BaseFormatConverter):
    """纯文本格式转换器"""
    
    def extract_text(self, source: str) -> List[str]:
        """从文本中提取需要翻译的内容"""
        # 按段落分割文本
        paragraphs = source.split('\n\n')
        # 过滤空段落
        return [p.strip() for p in paragraphs if p.strip()]
    
    def apply_translation(self, source: str, translated_texts: List[str]) -> str:
        """将翻译后的文本应用回原文本结构"""
        paragraphs = source.split('\n\n')
        result_paragraphs = []
        trans_index = 0
        
        for para in paragraphs:
            if para.strip():
                if trans_index < len(translated_texts):
                    result_paragraphs.append(translated_texts[trans_index])
                    trans_index += 1
                else:
                    result_paragraphs.append(para)
            else:
                result_paragraphs.append('')
        
        return '\n\n'.join(result_paragraphs)


class WordConverter(BaseFormatConverter):
    """Word文档格式转换器"""
    
    def __init__(self):
        try:
            self.docx = importlib.import_module('docx')
        except ImportError:
            raise ImportError("请安装python-docx库以使用Word转换功能")
    
    def extract_text(self, source: str) -> List[str]:
        """从Word文档中提取文本"""
        doc = self.docx.Document(source)
        texts = []
        
        # 提取段落文本
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texts.append(paragraph.text)
        
        # 提取表格文本
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        texts.append(cell.text)
        
        return texts
    
    def apply_translation(self, source: str, translated_texts: List[str]) -> str:
        """将翻译后的文本应用到Word文档（创建新文档）"""
        doc = self.docx.Document(source)
        trans_index = 0
        
        # 翻译段落
        for paragraph in doc.paragraphs:
            if paragraph.text.strip() and trans_index < len(translated_texts):
                paragraph.text = translated_texts[trans_index]
                trans_index += 1
        
        # 翻译表格
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip() and trans_index < len(translated_texts):
                        cell.text = translated_texts[trans_index]
                        trans_index += 1
        
        # 保存翻译后的文档
        output_path = source.replace('.docx', '_translated.docx')
        doc.save(output_path)
        return output_path


class PDFConverter(BaseFormatConverter):
    """PDF文档格式转换器"""
    
    def __init__(self):
        try:
            self.fitz = importlib.import_module('fitz')
        except ImportError:
            raise ImportError("请安装PyMuPDF库以使用PDF转换功能: pip install PyMuPDF")
    
    def extract_text(self, source: str) -> List[str]:
        """从PDF文档中提取文本"""
        texts = []
        
        with self.fitz.open(source) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    # 按行分割并过滤空行
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    texts.extend(lines)
        
        return texts
    
    def apply_translation(self, source: str, translated_texts: List[str]) -> str:
        """将翻译后的文本应用到PDF文档（创建新文档）"""
        with self.fitz.open(source) as doc:
            # 创建新的PDF文档
            new_doc = self.fitz.open()
            
            # 将翻译后的文本逐行写入新PDF
            new_page = new_doc.new_page()
            
            # 设置初始位置
            current_y = 50
            font_size = 12
            
            for text in translated_texts:
                # 添加文本到页面
                new_page.insert_text((50, current_y), text, fontsize=font_size)
                current_y += font_size + 2  # 移动到下一行
                
                # 如果页面满了，创建新页面
                if current_y > 750:  # 假设页面高度约为800点
                    new_page = new_doc.new_page()
                    current_y = 50
                    
            # 生成输出文件路径
            output_path = source.replace('.pdf', '_translated.pdf')
            
            # 保存新文档
            new_doc.save(output_path)
            new_doc.close()
            
            return output_path


class TranslationHelper:
    """
    翻译助手类，支持多种格式的文本提取和翻译应用
    """
    
    def __init__(self):
        self.converters = {
            'json': JSONConverter(),
            'text': TextConverter(),
            'txt': TextConverter(),
            'word': WordConverter(),
            'docx': WordConverter(),
            'pdf': PDFConverter()
        }
    
    def get_converter(self, format_type: str) -> BaseFormatConverter:
        """获取指定格式的转换器"""
        if format_type not in self.converters:
            raise ValueError(f"不支持的格式: {format_type}。支持的格式: {list(self.converters.keys())}")
        return self.converters[format_type]
    
    def extract_text(self, source: Any, format_type: str) -> List[str]:
        """
        从源数据中提取需要翻译的文本
        
        Args:
            source: 源数据，可以是文件路径、JSON对象、字符串等
            format_type: 格式类型，如 'json', 'text', 'word', 'pdf' 等
        
        Returns:
            需要翻译的文本列表
        """
        converter = self.get_converter(format_type)
        return converter.extract_text(source)
    
    def apply_translation(self, source: Any, translated_texts: List[str], format_type: str) -> Any:
        """
        将翻译后的文本应用回源数据
        
        Args:
            source: 原始数据
            translated_texts: 翻译后的文本列表
            format_type: 格式类型
        
        Returns:
            应用翻译后的数据
        """
        converter = self.get_converter(format_type)
        return converter.apply_translation(source, translated_texts)
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        return list(self.converters.keys())


# 使用示例
if __name__ == "__main__":
    helper = TranslationHelper()
    from test import *
    lists=helper.extract_text('test.docx','word')
    print(lists)
    translator = BaiduTranslator(config=config)
    translated_texts = translator.translate(lists, source_lang='auto', target_lang='zh')
    print(translated_texts)
    helper.apply_translation('test.docx',translated_texts,'word')
    print(translator.get_performance_metrics())