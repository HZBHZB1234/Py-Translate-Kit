"""
通用大模型翻译服务实现
允许所有支持OpenAI API格式请求的大模型（OpenAI/智谱/讯飞/DeepSeek等）
"""

import warnings
from typing import Dict, Any, Optional, List
from .base import (
    TranslatorBase, TranslationConfig, APIError, 
    TranslationWarning, ConfigurationError, ConfigWarning, Metadata
)

class LLMGeneralTranslator(TranslatorBase):
    """通用大模型翻译服务实现类（兼容OpenAI API格式）"""
    
    # 服务元信息
    SERVICE_NAME = "llmGeneral_translator"
    SUPPORTED_LANGUAGES = {}  # 初始化时加载预设语言列表

    DEFAULT_CONFIG = TranslationConfig()

    # 默认API配置（兼容OpenAI API格式）
    DEFAULT_API_KEY = {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "temperature": 0.0,
        "max_tokens": 4000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "system_prompt": "你是一个专业的翻译助手，严格按照要求完成翻译任务，只返回翻译结果，不添加任何额外解释、说明或格式。",
        "user_prompt_base": "{0}"
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
            "id": "model",
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
        }
    ]
    
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
        
        # 加载预设支持的语言列表（LLM支持的主流语言）
        self.SUPPORTED_LANGUAGES = self._get_supported_languages()
        
        # 初始化请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 拼接完整的API端点
        self.complete_api_url = f"{self.base_url.rstrip('/')}{self.CHAT_COMPLETIONS_ENDPOINT}"
        
        self.logger.debug(f"LLM翻译器初始化完成，API地址: {self.complete_api_url}，模型: {self.model}")

    def validate_config(self):
        """验证配置合法性"""
        super().validate_config()
        
        # 基础校验
        if not self.api_key:
            raise ConfigurationError("API密钥(api_key)未配置，无法调用大模型API")
        
        # 数值范围校验
        if not (0.0 <= self.temperature <= 2.0):
            warnings.warn("temperature应在0.0-2.0之间，已自动修正为0.0", ConfigWarning)
            self.temperature = 0.0
            
        if self.max_tokens <= 0 or self.max_tokens > 16000:
            warnings.warn("max_tokens建议在1-16000之间，已自动修正为4000", ConfigWarning)
            self.max_tokens = 4000
            
        # URL格式校验
        if not self.base_url.startswith(('http://', 'https://')):
            raise ConfigurationError(f"base_url格式错误: {self.base_url}，必须以http://或https://开头")

    def _get_supported_languages(self) -> Dict[str, str]:
        """获取LLM支持的语言列表（预设主流语言）"""
        return {
            'auto': 'auto',
            'zh': '中文',
            'zh-hans': '中文(简体)',
            'zh-hant': '中文(繁体)',
            'en': '英语',
            'ja': '日语',
            'ko': '韩语',
            'fr': '法语',
            'de': '德语',
            'ru': '俄语',
            'es': '西班牙语',
            'pt': '葡萄牙语',
            'it': '意大利语',
            'ar': '阿拉伯语',
            'tr': '土耳其语',
            'vi': '越南语',
            'th': '泰语',
            'hi': '印地语'
        }

    def _build_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> List[Dict[str, str]]:
        """构建翻译请求的Prompt（适配Chat Completions格式）"""
        # 语言名称映射（提升Prompt可读性）
        lang_mapping = {
            'auto': '自动识别的语言',
            'zh': '中文',
            'zh-hans': '中文(简体)',
            'zh-hant': '中文(繁体)',
            'en': '英语',
            'ja': '日语',
            'ko': '韩语',
            'fr': '法语',
            'de': '德语',
            'ru': '俄语',
            'es': '西班牙语'
        }
        
        src_lang_name = lang_mapping.get(source_lang, source_lang)
        tgt_lang_name = lang_mapping.get(target_lang, target_lang)
        
        # 用户指令
        user_prompt = f"""将以下文本从{src_lang_name}翻译到{tgt_lang_name}：

{text}"""
        
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
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "messages": self._build_translation_prompt(text, source_lang, target_lang)
        }
        
        self.logger.debug(f"发送翻译请求到 {self.complete_api_url}，模型: {request_data['model']}")
        
        try:
            # 发送API请求
            response = self._session.post(
                url=self.complete_api_url,
                headers=self.headers,
                json=request_data,
                timeout=self.config.timeout
            )
            
            # 状态码处理
            if response.status_code == 401:
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
            
            self.logger.debug(f"翻译响应解析完成，结果长度: {len(translation)}")
            return translation
            
        except KeyError as e:
            raise APIError(f"解析响应失败：缺少字段 {e}") from e
        except Exception as e:
            raise APIError(f"解析响应失败：{str(e)}") from e

    def get_special_api_reference(self) -> Dict[str, Any]:
        """获取特殊API方法的引用规范"""
        return {
            "set_model": {
                "description": "动态设置翻译使用的模型",
                "parameters": {
                    "model_name": "模型名称（如gpt-3.5-turbo、glm-4、deepseek-chat等）"
                },
                "return_type": "None",
                "example": "translator.set_model('gpt-4')"
            },
            "set_temperature": {
                "description": "设置生成温度（翻译建议0.0）",
                "parameters": {
                    "temperature": "温度值（0.0-2.0）"
                },
                "return_type": "None",
                "example": "translator.set_temperature(0.1)"
            }
        }

    # 便捷方法：动态调整模型参数
    def set_model(self, model_name: str):
        """设置翻译使用的模型"""
        if not model_name:
            raise ValueError("模型名称不能为空")
        self.model = model_name
        self.logger.debug(f"已切换模型为: {model_name}")

    def set_temperature(self, temperature: float):
        """设置生成温度"""
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature必须在0.0-2.0之间")
        self.temperature = temperature
        self.logger.debug(f"已设置temperature为: {temperature}")

    def set_system_prompt(self, prompt: str):
        """自定义系统提示词"""
        self.system_prompt = prompt
        self.logger.debug("已更新系统提示词")