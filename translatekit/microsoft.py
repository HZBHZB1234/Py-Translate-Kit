"""
Microsoft翻译服务实现
"""

import warnings
from typing import Dict, Any, Optional, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class MicrosoftTranslator(TranslatorBase):
    """Microsoft翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "microsoft_translator"
    SUPPORTED_LANGUAGES = {}  # 将在初始化时从API获取
    
    DEFAULT_API_KEY = {
        "api_key": "",
        "region": "",
        "category": "general",
        "text_type": "plain",
        "profanity_action": "NoAction",
        "sentence_splitting": False
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "api_key",
            "name": "Microsoft翻译API密钥",
            "type": "string",
            "required": True,
            "description": "Microsoft翻译API密钥"
        },
        {
            "id": "region",
            "name": "区域",
            "type": "string",
            "required": False,
            "description": "Microsoft翻译API的区域"
        },
        {
            "id": "category",
            "name": "分类",
            "type": "string",
            "required": False,
            "description": "翻译的分类，比如通用、新闻等"
        },
        {
            "id": "text_type",
            "name": "文本类型",
            "type": "string",
            "required": False,
            "description": "文本类型（plain或html）"
        },
        {
            "id": "profanity_action",
            "name": "脏话处理",
            "type": "string",
            "required": False,
            "description": "翻译到脏话时处理方式（NoAction, Marked, Deleted）"
        },
        {
            "id": "sentence_splitting",
            "name": "句子拆分",
            "type": "boolean",
            "required": False,
            "description": "是否启用句子拆分"
        }
    ]
    
    # Microsoft翻译API端点
    BASE_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"
    API_VERSION = "3.0"
    
    METADATA = Metadata(
        console_url="https://azure.microsoft.com/services/cognitive-services/translator/",
        description="Microsoft翻译服务实现，基于Azure认知服务",
        documentation_url="https://docs.microsoft.com/azure/cognitive-services/translator/",
        short_description="Microsoft翻译服务（Azure认知服务）",
        usage_documentation="需要API密钥和区域信息，支持多种语言和高级功能"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化Microsoft翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数
        """
        super().__init__(config, **kwargs)

        try:
            self.SUPPORTED_LANGUAGES = self.get_supported_languages()
        except Exception as e:
            warnings.warn(f"获取支持的语言列表失败，使用默认列表: {e}", RuntimeWarning)

        # 设置请求头
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-type": "application/json"
        }
        # 如果提供了区域信息，添加到请求头
        if self.region:
            self.headers["Ocp-Apim-Subscription-Region"] = self.region

    def _get_supported_languages(self) -> Dict[str, str]:
        """从Microsoft API获取支持的语言列表"""
        try:
            languages_url = f"https://api.cognitive.microsofttranslator.com/languages?api-version=3.0&scope=translation"
            response = self.session.get(languages_url, timeout=self.config.timeout)
            response.raise_for_status()
            
            translation_dict = response.json()["translation"]
            # 返回语言名称小写的映射
            return {
                k.lower(): translation_dict[k]["nativeName"].lower()
                for k in translation_dict.keys()
            }
        except Exception as e:
            self.logger.warning(f"无法获取Microsoft支持的语言列表，使用默认列表: {e}")
            # 返回一个默认的常见语言列表
            return {
                "af": "afrikaans", "ar": "arabic", "bg": "bulgarian", "ca": "catalan",
                "zh-hans": "chinese (simplified)", "zh-hant": "chinese (traditional)",
                "cs": "czech", "da": "danish", "nl": "dutch", "en": "english", "et": "estonian",        
                "fi": "finnish", "fr": "french", "de": "german", "el": "greek",
                "ht": "haitian creole", "he": "hebrew", "hi": "hindi", "hu": "hungarian",
                "is": "icelandic", "id": "indonesian", "it": "italian", "ja": "japanese",
                "ko": "korean", "lv": "latvian", "lt": "lithuanian", "nb": "norwegian",
                "pl": "polish", "pt": "portuguese", "ro": "romanian", "ru": "russian",
                "sk": "slovak", "sl": "slovenian", "es": "spanish", "sv": "swedish", "th": "thai",      
                "tr": "turkish", "uk": "ukrainian", "vi": "vietnamese",
                "auto": "auto"
            }

    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用Microsoft翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        # 构建请求URL参数
        params = {
            'api-version': self.API_VERSION,
            'to': target_lang
        }

        if source_lang != 'auto':
            params['from'] = source_lang

        # 构建请求体
        body = [{
            'text': text
        }]

        # 添加可选参数
        if self.category != 'general':
            params['category'] = self.category
        if self.text_type != 'plain':
            params['textType'] = self.text_type
        if self.profanity_action != 'NoAction':
            params['profanityAction'] = self.profanity_action
        if self.sentence_splitting:
            params['sentenceLength'] = 'true'

        # 发送请求
        response = self.session.post(
            self.BASE_ENDPOINT,
            params=params,
            headers=self.headers,
            json=body,
            timeout=self.config.timeout
        )

        # 检查响应状态
        if response.status_code == 401:
            raise APIError("Microsoft API认证失败，请检查API密钥和区域设置")
        elif response.status_code == 403:
            raise APIError("Microsoft API访问被拒绝，请检查订阅权限")
        elif response.status_code == 429:
            raise APIError("Microsoft API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            error_detail = response.text
            raise APIError(f"Microsoft API错误: {response.status_code} - {error_detail}")

        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if not response or not isinstance(response, list) or len(response) == 0:
            raise APIError("Microsoft API响应格式错误或为空")

        # 获取翻译结果
        translations = response[0].get("translations", [])
        if not translations:
            raise APIError("Microsoft API响应中未找到翻译结果")

        # 返回第一个翻译结果
        translated_texts = [item["text"] for item in translations]
        return "\n".join(translated_texts)

    def get_detected_language(self, text: str) -> Dict[str, Any]:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            包含检测结果的字典
        """
        detect_url = f"https://api.cognitive.microsofttranslator.com/detect?api-version=3.0"
        body = [{"text": text}]

        response = self.session.post(
            detect_url,
            headers=self.headers,
            json=body,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()[0]

    def transliterate_text(self, text: str, source_lang: str, target_script: str) -> str:
        """
        文本转写（转换文字系统）
        
        Args:
            text: 要转写的文本
            source_lang: 源语言
            target_script: 目标文字系统
            
        Returns:
            转写后的文本
        """
        transliterate_url = f"https://api.cognitive.microsofttranslator.com/transliterate?api-version=3.0&language={source_lang}&toScript={target_script}"
        body = [{"text": text}]

        response = self.session.post(
            transliterate_url,
            headers=self.headers,
            json=body,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        result = response.json()
        return result[0].get("text", "")

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取Microsoft翻译特殊API方法的引用规范
        """
        return {
            "get_detected_language": {
                "description": "检测输入文本的语言",
                "parameters": {
                    "text": "要检测的文本"
                },
                "return_type": "Dict[str, Any] 检测结果字典，包含语言代码和置信度",
                "example": "translator.get_detected_language('Hello world')"
            },
            "transliterate_text": {
                "description": "将文本从一种文字系统转换为另一种文字系统（如西里尔文转拉丁文）",
                "parameters": {
                    "text": "要转写的文本",
                    "source_lang": "源语言代码",
                    "target_script": "目标文字系统代码"
                },
                "return_type": "str 转写后的文本",
                "example": "translator.transliterate_text('Привет', 'ru', 'Latn')"
            }
        }

    def set_text_type(self, text_type: str):
        """设置文本类型（plain或html）"""
        if text_type in ['plain', 'html']:
            self.text_type = text_type
        else:
            raise ValueError("文本类型必须是 'plain' 或 'html' 中的一个")

    def set_profanity_action(self, action: str):
        """
        设置脏话处理方式
        Args:
            action: 'NoAction', 'Marked', 'Deleted'
        """
        if action in ['NoAction', 'Marked', 'Deleted']:
            self.profanity_action = action
        else:
            raise ValueError("脏话处理方式必须是 'NoAction', 'Marked' 或 'Deleted' 中的一个")
