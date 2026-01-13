"""
思知（Sizhi）对话 API 翻译服务实现
使用思知对话机器人 API 进行翻译
"""

import json
import time
import random
import hashlib
from typing import Dict, Any, Optional
from urllib.parse import quote
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata


class SizhiTranslator(TranslatorBase):
    """思知（Sizhi）对话 API 翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "sizhi_translator"
    SUPPORTED_LANGUAGES = {
        'auto': '自动检测',
        'en': '英语',
    }
    
    # API端点
    BASE_ENDPOINT = "https://api.sizhi.com"
    CHAT_ENDPOINT = "/chat"
    
    # 默认API配置
    DEFAULT_API_KEY = {
        "appid": "",
        "userid": "",
        "prompt": "请将以下文本进行翻译，只返回翻译结果：\n{text}"
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "appid",
            "name": "机器人ID",
            "type": "string",
            "required": True,
            "description": "思知机器人唯一标识，可在机器人形象设置中获取"
        },
        {
            "id": "userid",
            "name": "用户ID",
            "type": "string",
            "required": False,
            "description": "自定义用户标识，默认随机生成"
        },
        {
            "id": "prompt",
            "name": "翻译提示词",
            "type": "string",
            "required": False,
            "description": "翻译指令模板，使用 {text} 占位符"
        }
    ]
    
    metadata = Metadata(
        console_url="https://sizhi.com",
        description="思知（Sizhi）对话API翻译服务，使用对话机器人进行翻译",
        documentation_url="https://docs.sizhi.com",
        short_description="思知对话翻译服务",
        usage_documentation=""
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化思知翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)
        
        # 如果未提供userid，生成随机userid
        if not self.userid:
            self.userid = f"sizhi_user_{random.randint(10000, 99999)}_{int(time.time())}"
        
        # 线程本地存储，用于速率限制
        self.MIN_REQUEST_INTERVAL = 1.0  # 思知API建议的最小请求间隔
    
    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Any:
        """
        调用思知对话API进行翻译
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 使用prompt模板，将{text}替换为实际文本
        if hasattr(self, 'prompt'):
            prompt_text = self.prompt.format(text=text)
        else:
            # 默认prompt
            prompt_text = f"请将以下文本进行翻译，只返回翻译结果：\n{text}"
        
        # 构建API请求URL和参数
        url = f"{self.BASE_ENDPOINT}{self.CHAT_ENDPOINT}"
        
        # 构建请求参数
        params = {
            'appid': self.appid,
            'userid': self.userid,
            'spoken': prompt_text,
            'stream': 'false',
            'memory': 'true'
        }
        
        try:
            # 发送GET请求
            response = self._session.get(
                url, 
                params=params,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            return response.json()
                
        except Exception as e:
            raise APIError(f"思知API调用失败: {str(e)}")
    
    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """
        解析思知API响应
        
        Args:
            response: API响应字典
            **kwargs: 额外参数
            
        Returns:
            翻译结果文本
        """
        # 检查响应状态
        if response.get('status') != 0:
            error_msg = response.get('message', '未知错误')
            raise APIError(f"思知翻译失败: {error_msg} (状态码: {response.get('status')})")
        
        # 提取翻译结果
        if response.get('data') and response['data'].get('info'):
            translation = response['data']['info'].get('text', '')
            
            if translation:
                return translation.strip()
        
        raise APIError("无法解析翻译响应，响应格式错误")