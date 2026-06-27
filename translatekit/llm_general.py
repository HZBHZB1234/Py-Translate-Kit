"""
通用大模型翻译服务实现
允许所有支持OpenAI API格式请求的大模型（OpenAI/智谱/讯飞/DeepSeek等）
"""

import warnings
from typing import Dict, Any, Optional, List, Union
from .base import (
    TranslatorBase, TranslationConfig, APIError, 
    TranslationWarning, ConfigurationError, ConfigWarning, Metadata
)

class LLMGeneralTranslator(TranslatorBase):
    """通用大模型翻译服务实现类（兼容OpenAI API格式）"""
    
    # 服务元信息
    SERVICE_NAME = "llmGeneral_translator"
    SUPPORTED_LANGUAGES = {
        'auto': 'auto',
        'en': 'en'
    }

    DEFAULT_CONFIG = TranslationConfig()

    # 默认API配置（兼容OpenAI API格式）
    DEFAULT_API_KEY = {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-3.5-turbo",
        "temperature": 1.0,
        "max_tokens": 4000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "system_prompt": "你是一个专业的翻译助手，严格按照要求完成翻译任务，只返回翻译结果，不添加任何额外解释、说明或格式。",
        "response_format": "text",
        "extra_body": {}
    }

    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "API密钥",
            "type": "string",
            "required": True,
            "description": "大模型平台的API密钥（如OpenAI/智谱/讯飞等）"
        },
        {
            "id": "base_url",
            "name": "API基础地址",
            "type": "string",
            "required": False,
            "description": "自定义API基础URL（支持OpenAI兼容接口，如https://api.openai.com/v1、https://open.bigmodel.cn/api/paas/v4等）"
        },
        {
            "id": "model_name",
            "name": "模型名称",
            "type": "string",
            "required": False,
            "description": "使用的模型名称（如gpt-3.5-turbo、gpt-4、glm-4、deepseek-chat等）"
        },
        {
            "id": "temperature",
            "name": "温度系数",
            "type": "number",
            "required": False,
            "description": "生成温度（0-2，越低越精准，翻译建议0.0）"
        },
        {
            "id": "top_p",
            "name": "核采样阈值",
            "type": "number",
            "required": False,
            "description": "OpenAI风格核采样参数，取值0~1，越小生成越保守，默认1.0"
        },
        {
            "id": "frequency_penalty",
            "name": "频率惩罚",
            "type": "number",
            "required": False,
            "description": "降低重复token生成概率，取值-2~2，默认0.0"
        },
        {
            "id": "presence_penalty",
            "name": "存在惩罚",
            "type": "number",
            "required": False,
            "description": "增加新主题生成概率，取值-2~2，默认0.0"
        },
        {
            "id": "max_tokens",
            "name": "最大生成令牌数",
            "type": "number",
            "required": False,
            "description": "单次请求最大生成令牌数（需匹配模型支持的上下文长度）"
        },
        {
            "id": "system_prompt",
            "name": "系统提示词",
            "type": "string",
            "required": False,
            "description": "翻译助手的系统角色定义（控制翻译行为）"
        },
        {
            "id": "response_format",
            "name": "响应格式",
            "type": "string",
            "required": False,
            "description": "响应格式定义，可选json_object，text"
        },
        {
            "id": "extra_body",
            "name": "额外请求体",
            "type": "dictionary",
            "required": False,
            "description": "额外的请求体参数，将以字典形式合并到API请求体中，用于传递特殊参数（如OpenAI的reasoning_effort、seed等）"
        }
    ]
    
    INNER_API = {
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-3.5-turbo"
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4"
        },
        "xunfei": {
            "base_url": "https://spark-api.xf-yun.com/v1",
            "model": "spark-pro"
        },
        "baidu": {
            "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
            "model": "ernie-4.0"
        },
        "ali": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus"
        },
        "bytedance": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "doubao-pro"
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "model": "claude-3-opus-20240229"
        },
        "google": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-pro"
        },
        "moonshot": {
            "base_url": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-8k"
        },
        "zhiyuan": {
            "base_url": "https://api.baai.ac.cn/v1",
            "model": "wudao-2.0"
        }
    }
    
    # API端点（拼接base_url使用）
    CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"
    
    # 服务元数据
    METADATA = Metadata(
        console_url="",
        description="通用大模型翻译服务，兼容所有支持OpenAI API格式的大模型（OpenAI/智谱AI/讯飞星火/DeepSeek/百度文心等）",
        documentation_url="",
        short_description="通用大模型翻译（OpenAI API兼容）",
        usage_documentation="""
1. 配置api_key：对应平台的API密钥
2. 配置base_url：
   - OpenAI: https://api.openai.com/v1
   - 智谱AI: https://open.bigmodel.cn/api/paas/v4
   - 讯飞星火: https://spark-api.xf-yun.com/v1
   - DeepSeek: https://api.deepseek.com/v1
3. 配置model：对应平台的模型名称
4. 翻译支持所有主流语言，自动识别源语言
        """
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化通用大模型翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数（覆盖DEFAULT_API_KEY）
        """
        self.DEFAULT_CONFIG.target_lang = 'auto'

        super().__init__(config, **kwargs)
        
        # 初始化请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 拼接完整的API端点
        self.complete_api_url = f"{self.base_url.rstrip('/')}{self.CHAT_COMPLETIONS_ENDPOINT}"
        
        self.logger.debug(f"LLM翻译器初始化完成，API地址: {self.complete_api_url}，模型: {self.model_name}")

    def _validate_languages(self, source_lang: str, target_lang: str):
        """无需验证语言对"""
        pass
    
    def _update_config_from_kwargs(self, kwargs: Dict):
        """更新配置参数"""
        if "model" in kwargs:
            model = kwargs.pop("model")
            if model in self.INNER_API:
                modal_description = self.INNER_API[model]
                self.base_url = modal_description["base_url"]
                self.model_name = modal_description["model"]
                self.config.api_setting["base_url"] = self.base_url
                self.config.api_setting["model_name"] = self.model_name
            else:
                self.logger.debug(f"未知内置模型: {model}，已忽略")
                
        super()._update_config_from_kwargs(kwargs)

    def validate_config(self):
        """验证配置合法性"""
        super().validate_config()
        
        if not (0.0 <= self.temperature <= 2.0):
            warnings.warn("temperature应在0.0-2.0之间，已自动修正为0.0", ConfigWarning)
            self.temperature = 1.0
            
        # URL格式校验
        if not self.base_url.startswith(('http://', 'https://')):
            raise ConfigurationError(f"base_url格式错误: {self.base_url}，必须以http://或https://开头")

    def _build_translation_prompt(self, text) -> List[Dict[str, str]]:
        """构建翻译请求的Prompt（适配Chat Completions格式）"""
        user_prompt = text
        
        # 构建messages（兼容OpenAI Chat API格式）
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return messages

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用OpenAI API格式的大模型翻译接口
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数（覆盖单次请求的模型参数）
        """
        # 构建请求参数
        request_data = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "response_format": {"type": self.response_format},
            "messages": self._build_translation_prompt(text)
        }

        # 合并额外请求体参数（extra_body中的键会覆盖已有键）
        if self.extra_body:
            request_data.update(self.extra_body)
                
        try:
            # 发送API请求
            response = self._session.post(
                url=self.complete_api_url,
                headers=self.headers,
                json=request_data,
                timeout=self.config.timeout
            )
            
            # 状态码处理
            if response.status_code == 400:
                try:
                    error_message = response.json()
                    self.logger.debug(f"API错误: {error_message}")
                except Exception:
                    pass
                raise APIError("请求构造错误")
            elif response.status_code == 401:
                raise APIError("API认证失败，请检查api_key是否正确")
            elif response.status_code == 403:
                raise APIError("API访问被拒绝，可能是密钥权限不足或IP受限")
            elif response.status_code == 429:
                raise APIError("请求频率超限，请降低请求速度或等待配额重置")
            elif response.status_code == 404:
                raise APIError(f"API地址不存在: {self.complete_api_url}，请检查base_url配置")
            elif response.status_code >= 500:
                raise APIError(f"服务器内部错误: {response.status_code} - {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"调用大模型API失败: {str(e)}") from e

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析OpenAI API格式的响应"""
        try:
            # 校验响应结构
            if not response or "choices" not in response:
                raise APIError("大模型API响应格式错误：缺少choices字段")
            
            choices = response["choices"]
            if not choices or len(choices) == 0:
                raise APIError("大模型API响应为空：choices列表为空")
            
            # 提取翻译结果
            translation = choices[0]["message"]["content"].strip()
            
            if not translation:
                raise APIError("大模型返回空的翻译结果")
            
            return translation
            
        except KeyError as e:
            raise APIError(f"解析响应失败：缺少字段 {e}") from e
        except Exception as e:
            raise APIError(f"解析响应失败：{str(e)}") from e

    def get_inner_modal(self, modal_name: str) -> Dict[str,str]:
        """获取内置模型"""
        return self.INNER_API[modal_name]