"""
MyMemory翻译服务实现
"""

import requests
import json
from typing import Dict, Any, List, Optional, Union

from base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata


class MyMemoryTranslator(TranslatorBase):
    """MyMemory翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "mymemory_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测',
        'zh': '中文',
        'en': '英语',
        'ja': '日语',
        'ko': '韩语',
        'fr': '法语',
        'es': '西班牙语',
        'th': '泰语',
        'ar': '阿拉伯语',
        'ru': '俄语',
        'pt': '葡萄牙语',
        'de': '德语',
        'it': '意大利语',
        'el': '希腊语',
        'nl': '荷兰语',
        'pl': '波兰语',
        'bg': '保加利亚语',
        'et': '爱沙尼亚语',
        'da': '丹麦语',
        'fi': '芬兰语',
        'cs': '捷克语',
        'ro': '罗马尼亚语',
        'sl': '斯洛文尼亚语',
        'sv': '瑞典语',
        'hu': '匈牙利语',
        'id': '印尼语',
        'uk': '乌克兰语',
        'tr': '土耳其语',
        'vi': '越南语'
    }
    
    # MyMemory API端点
    BASE_ENDPOINT = "http://api.mymemory.translated.net/get"
    
    metadata = Metadata(
        console_url="https://mymemory.translated.net/",
        description="MyMemory翻译服务实现，基于众包翻译记忆库",
        documentation_url="https://mymemory.translated.net/doc/spec.php",
        short_description="MyMemory翻译服务",
        usage_documentation=""
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化MyMemory翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)
        
        # 可选的邮箱参数，有助于提高请求限制
        self.email = kwargs.get('email', None)
        
        # 线程本地存储，用于速率限制
        self.MIN_REQUEST_INTERVAL = 1.0  # MyMemory建议较长的请求间隔

    def _call_translate_api(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用MyMemory翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 构建请求参数
        params = {
            'q': text,
            'langpair': f'{source_lang}|{target_lang}'
        }
        
        if self.email:
            params['de'] = self.email  # 开发者邮箱，有助于提高API限制
            
        # 发送请求
        try:
            response = requests.get(
                self.BASE_ENDPOINT, 
                params=params, 
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise APIError(f"MyMemory翻译API调用失败: {str(e)}")

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if 'responseStatus' in response and response['responseStatus'] != 200:
            raise APIError(f"MyMemory API错误: {response.get('responseDetails', '未知错误')}")
            
        if 'responseData' not in response:
            raise APIError("无法解析翻译响应，缺少responseData字段")
            
        response_data = response['responseData']
        if 'translatedText' not in response_data:
            raise APIError("翻译结果为空")
            
        translated_text = response_data['translatedText']
        if not translated_text:
            raise APIError("翻译结果为空")
            
        return translated_text

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取MyMemory翻译特殊API方法的引用规范
        
        Returns:
            包含特殊API方法信息的字典
        """
        return {
            "translate": {
                "description": "基础翻译接口，支持文本翻译",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言代码（可选）",
                    "target_lang": "目标语言代码（可选）"
                },
                "return_type": "str 翻译结果",
                "example": "translator.translate('Hello world', 'en', 'zh')"
            },
            "translate_batch": {
                "description": "批量翻译接口，支持多个文本翻译",
                "parameters": {
                    "texts": "要翻译的文本列表",
                    "source_lang": "源语言代码（可选）",
                    "target_lang": "目标语言代码（可选）"
                },
                "return_type": "List[str] 翻译结果列表",
                "example": "translator.translate_batch(['Hello', 'World'], 'en', 'zh')"
            }
        }