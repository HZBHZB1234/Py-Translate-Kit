"""
MyMemory翻译服务实现
"""

import requests
from typing import Dict, Any, Optional, Union, List
from .base import TranslatorBase, TranslationConfig, APIError, ConfigurationError, Metadata

class MyMemoryTranslator(TranslatorBase):
    """MyMemory翻译服务实现类"""
    
    # 服务元信息
    SERVICE_NAME = "mymemory_translator"
    SUPPORTED_LANGUAGES = {
        "ace-ID": "acehnese", "af-ZA": "afrikaans", "ak-GH": "akan", "sq-AL": "albanian",
        "am-ET": "amharic", "aig-AG": "antigua and barbuda creole english",
        "ar-SA": "arabic", "ar-EG": "arabic egyptian", "an-ES": "aragonese",
        "hy-AM": "armenian", "as-IN": "assamese", "ast-ES": "asturian",
        "de-AT": "austrian german", "awa-IN": "awadhi", "quy-PE": "ayacucho quechua",
        "az-AZ": "azerbaijani", "bah-BS": "bahamas creole english", "bjs-BB": "bajan",
        "ban-ID": "balinese", "rm-RO": "balkan gipsy", "bm-ML": "bambara",
        "bjn-ID": "banjar", "ba-RU": "bashkir", "eu-ES": "basque", "be-BY": "belarusian",
        "fr-BE": "belgian french", "bem-ZM": "bemba", "bn-IN": "bengali",
        "bho-IN": "bhojpuri", "bh-IN": "bihari", "bi-VU": "bislama", "gax-KE": "borana",
        "bs-BA": "bosnian", "bs-Cyrl-BA": "bosnian (cyrillic)", "br-FR": "breton",
        "bug-ID": "buginese", "bg-BG": "bulgarian", "my-MM": "burmese",
        "ca-ES": "catalan", "cav-ES": "catalan valencian", "ceb-PH": "cebuano",
        "tzm-MA": "central atlas tamazight", "ayr-BO": "central aymara",
        "knc-NG": "central kanuri (latin script)", "shu-TD": "chadian arabic",
        "ch-GU": "chamorro", "chr-US": "cherokee", "hne-IN": "chhattisgarhi",
        "zh-CN": "chinese simplified", "zh-HK": "chinese trad. (hong kong)",
        "zh-TW": "chinese traditional", "zh-MO": "chinese traditional macau",
        "ctg-BD": "chittagonian", "cjk-AO": "chokwe", "grc-GR": "classical greek",
        "zdj-KM": "comorian ngazidja", "cop-EG": "coptic", "crh-RU": "crimean tatar",
        "pov-GW": "crioulo upper guinea", "hr-HR": "croatian", "cs-CZ": "czech",
        "da-DK": "danish", "prs-AF": "dari", "diq-TR": "dimli", "nl-NL": "dutch",
        "dyu-CI": "dyula", "dz-BT": "dzongkha", "ydd-US": "eastern yiddish",
        "vmw-MZ": "emakhuwa", "en-GB": "english", "en-AU": "english australia",
        "en-CA": "english canada", "en-IN": "english india", "en-IE": "english ireland",
        "en-NZ": "english new zealand", "en-SG": "english singapore",
        "en-ZA": "english south africa", "en-US": "english us", "eo-EU": "esperanto",
        "et-EE": "estonian", "ee-GH": "ewe", "fn-FNG": "fanagalo", "fo-FO": "faroese",
        "fj-FJ": "fijian", "fil-PH": "filipino", "fi-FI": "finnish", "nl-BE": "flemish",
        "fon-BJ": "fon", "fr-FR": "french", "fr-CA": "french canada",
        "fr-CH": "french swiss", "fur-IT": "friulian", "ff-FUL": "fula",
        "gl-ES": "galician", "mfi-NG": "gamargu", "grt-IN": "garo", "ka-GE": "georgian",
        "de-DE": "german", "gil-KI": "gilbertese", "glw-NG": "glavda", "el-GR": "greek",
        "gcl-GD": "grenadian creole english", "gn-PY": "guarani", "gu-IN": "gujarati",
        "gyn-GY": "guyanese creole english", "ht-HT": "haitian creole french",
        "khk-MN": "halh mongolian", "ha-NE": "hausa", "haw-US": "hawaiian",
        "he-IL": "hebrew", "hig-NG": "higi", "hil-PH": "hiligaynon",
        "mrj-RU": "hill mari", "hi-IN": "hindi", "hmn-CN": "hmong", "hu-HU": "hungarian",
        "is-IS": "icelandic", "ibo-NG": "igbo ibo", "ig-NG": "igbo ig",
        "ilo-PH": "ilocano", "id-ID": "indonesian", "kl-GL": "inuktitut greenlandic",
        "ga-IE": "irish gaelic", "it-IT": "italian", "it-CH": "italian swiss",
        "jam-JM": "jamaican creole english", "ja-JP": "japanese", "jv-ID": "javanese",
        "kac-MM": "jingpho", "quc-GT": "k'iche'", "kbp-TG": "kabiyè",
        "kea-CV": "kabuverdianu", "kab-DZ": "kabylian", "kln-KE": "kalenjin",
        "kam-KE": "kamba", "kn-IN": "kannada", "kr-KAU": "kanuri", "kar-MM": "karen",
        "ks-IN": "kashmiri (devanagari script)", "kas-IN": "kashmiri (arabic script)",
        "kk-KZ": "kazakh", "kha-IN": "khasi", "km-KH": "khmer", "kik-KE": "kikuyu kik",
        "ki-KE": "kikuyu ki", "kmb-AO": "kimbundu", "rw-RW": "kinyarwanda",
        "rn-BI": "kirundi", "guz-KE": "kisii", "kg-CG": "kongo", "kok-IN": "konkani",
        "ko-KR": "korean", "kmr-TR": "northern kurdish", "ckb-IQ": "kurdish sorani",
        "ky-KG": "kyrgyz", "lo-LA": "lao", "ltg-LV": "latgalian", "la-XN": "latin",
        "lv-LV": "latvian", "lij-IT": "ligurian", "li-NL": "limburgish",
        "ln-LIN": "lingala", "lt-LT": "lithuanian", "lmo-IT": "lombard",
        "lua-CD": "luba-kasai", "lg-UG": "luganda", "luy-KE": "luhya", "luo-KE": "luo",
        "lb-LU": "luxembourgish", "mas-KE": "maa", "mk-MK": "macedonian",
        "mag-IN": "magahi", "mai-IN": "maithili", "mg-MG": "malagasy", "ms-MY": "malay",
        "ml-IN": "malayalam", "dv-MV": "maldivian", "mt-MT": "maltese",
        "mfi-CM": "mandara", "mni-IN": "manipuri", "gv-IM": "manx gaelic",
        "mi-NZ": "maori", "mr-IN": "marathi", "mrt-NG": "margi", "mhr-RU": "mari",
        "mh-MH": "marshallese", "men-SL": "mende", "mer-KE": "meru",
        "nyf-KE": "mijikenda", "min-ID": "minangkabau", "lus-IN": "mizo",
        "mn-MN": "mongolian", "sr-ME": "montenegrin", "mfe-MU": "morisyen",
        "ar-MA": "moroccan arabic", "mos-BF": "mossi", "ndc-MZ": "ndau",
        "nr-ZA": "ndebele", "ne-NP": "nepali", "fuv-NG": "nigerian fulfulde",
        "niu-NU": "niuean", "azj-AZ": "north azerbaijani", "nso-ZA": "sesotho",
        "uzn-UZ": "northern uzbek", "nb-NO": "norwegian bokmål",
        "nn-NO": "norwegian nynorsk", "nus-SS": "nuer", "ny-MW": "nyanja",
        "oc-FR": "occitan", "oc-ES": "occitan aran", "or-IN": "odia", "ory-IN": "oriya",
        "ur-PK": "urdu", "pau-PW": "palauan", "pi-IN": "pali", "pag-PH": "pangasinan",
        "pap-CW": "papiamentu", "ps-PK": "pashto", "fa-IR": "persian", "pis-SB": "pijin",
        "plt-MG": "plateau malagasy", "pl-PL": "polish", "pt-PT": "portuguese",
        "pt-BR": "portuguese brazil", "pot-US": "potawatomi", "pa-IN": "punjabi",
        "pnb-PK": "punjabi (pakistan)", "qu-PE": "quechua", "rhg-MM": "rohingya",
        "rhl-MM": "rohingyalish", "ro-RO": "romanian", "roh-CH": "romansh",
        "run-BI": "rundi", "ru-RU": "russian", "acf-LC": "saint lucian creole french",
        "sm-WS": "samoan", "sg-CF": "sango", "sa-IN": "sanskrit", "sat-IN": "santali",
        "sc-IT": "sardinian", "gd-GB": "scots gaelic", "seh-ZW": "sena",
        "sr-Cyrl-RS": "serbian cyrillic", "sr-Latn-RS": "serbian latin",
        "crs-SC": "seselwa creole french", "tn-ZA": "setswana (south africa)",
        "shn-MM": "shan", "sn-ZW": "shona", "scn-IT": "sicilian", "szl-PL": "silesian",
        "snd-PK": "sindhi snd", "sd-PK": "sindhi sd", "si-LK": "sinhala",
        "sk-SK": "slovak", "sl-SI": "slovenian", "so-SO": "somali",
        "st-LS": "sotho southern", "azb-AZ": "south azerbaijani",
        "pbt-PK": "southern pashto", "dik-SS": "southwestern dinka", "es-ES": "spanish",
        "es-AR": "spanish argentina", "es-CO": "spanish colombia",
        "es-419": "spanish latin america", "es-MX": "spanish mexico",
        "es-US": "spanish united states", "srn-SR": "sranan tongo",
        "lvs-LV": "standard latvian", "zsm-MY": "standard malay", "su-ID": "sundanese",
        "sw-KE": "swahili", "ss-SZ": "swati", "sv-SE": "swedish", "de-CH": "swiss german",
        "syc-TR": "syriac (aramaic)", "tl-PH": "tagalog", "ty-PF": "tahitian",
        "tg-TJ": "tajik", "tmh-DZ": "tamashek (tuareg)", "taq-ML": "tamasheq",
        "ta-IN": "tamil india", "ta-LK": "tamil sri lanka", "trv-TW": "taroko",
        "tt-RU": "tatar", "te-IN": "telugu", "tet-TL": "tetum", "th-TH": "thai",
        "bo-CN": "tibetan", "ti-ET": "tigrinya", "tpi-PG": "tok pisin",
        "tkl-TK": "tokelauan", "to-TO": "tongan", "als-AL": "tosk albanian",
        "ts-ZA": "tsonga", "tsc-MZ": "tswa", "tn-BW": "tswana", "tum-MW": "tumbuka",
        "tr-TR": "turkish", "tk-TM": "turkmen", "tvl-TV": "tuvaluan", "tw-GH": "twi",
        "udm-RU": "udmurt", "uk-UA": "ukrainian", "ppk-ID": "uma", "umb-AO": "umbundu",
        "uig-CN": "uyghur uig", "ug-CN": "uyghur ug", "uz-UZ": "uzbek",
        "vec-IT": "venetian", "vi-VN": "vietnamese",
        "svc-VC": "vincentian creole english", "vic-US": "virgin islands creole english",
        "wls-WF": "wallisian", "war-PH": "waray (philippines)", "cy-GB": "welsh",
        "gaz-ET": "west central oromo", "pes-IR": "western persian", "wo-SN": "wolof",
        "xh-ZA": "xhosa", "yi-YD": "yiddish", "yo-NG": "yoruba", "zu-ZA": "zulu",
        "auto": "auto"
    }
    
    # MyMemory翻译API端点
    BASE_ENDPOINT = "http://api.mymemory.translated.net/get"
    
    DEFAULT_API_KEY = {
        "email": ""
    }
    
    DESCRIBE_API_KEY = [
        {
            "id": "email",
            "name": "MyMemory翻译API邮箱",
            "type": "string",
            "required": False,
            "description": "MyMemory翻译API的邮箱"
        }
    ]
 
    
    METADATA = Metadata(
        console_url="https://mymemory.translated.net/",
        description="MyMemory翻译服务实现，免费的翻译记忆库服务",
        documentation_url="https://mymemory.translated.net/doc/spec.php",
        short_description="MyMemory翻译服务（免费翻译记忆库）",
        usage_documentation="无需API密钥，但有请求频率限制，支持多种语言对，基于翻译记忆库"
    )
    
    def __init__(self, config: Optional[TranslationConfig] = None, **kwargs):
        """
        初始化MyMemory翻译器
        
        Args:
            config: 翻译配置对象
            **kwargs: 额外配置参数，支持email等
        """
        super().__init__(config, **kwargs)


    def _translate_default(self, text: str, source_lang: str, target_lang: str, **kwargs) -> Dict[str, Any]:
        """
        调用MyMemory翻译API
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 额外参数
        """
        params = {
            "langpair": f"{source_lang}|{target_lang}",
            "q": text,
        }

        # 如果提供了email，添加到参数中
        if self.email:
            params["de"] = self.email

        response = self._session.get(self.BASE_ENDPOINT, params=params, timeout=self.config.timeout)

        if response.status_code == 429:
            raise APIError("MyMemory API请求频率超限，请稍后重试")
        elif response.status_code >= 400:
            raise APIError(f"MyMemory API错误: {response.status_code} - {response.text}")

        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, response: Dict[str, Any], **kwargs) -> str:
        """解析API响应"""
        if not response:
            raise APIError("MyMemory API响应为空")

        response_data = response.get("responseData", {})
        translation = response_data.get("translatedText", "")
        all_matches = response.get("matches", [])

        if translation:
            return translation
        elif all_matches:
            # 如果没有直接的翻译结果，返回第一个匹配项
            first_match = all_matches[0] if all_matches else {}
            return first_match.get("translation", "")
        else:
            raise APIError("MyMemory API响应中未找到翻译结果")

    def translate_with_all_matches(self, text: str, source_lang: str = None, target_lang: str = None) -> Dict[str, Any]:
        """
        翻译并返回所有匹配结果
        
        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            包含翻译结果和所有匹配项的字典
        """
        source_lang = source_lang or self.config.source_lang
        target_lang = target_lang or self.config.target_lang

        self._validate_languages(source_lang, target_lang)

        params = {
            "langpair": f"{source_lang}|{target_lang}",
            "q": text,
        }

        if self.email:
            params["de"] = self.email

        response = self._session.get(self.BASE_ENDPOINT, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        response_data = response.json()

        translation = response_data.get("responseData", {}).get("translatedText", "")
        all_matches = response_data.get("matches", [])

        return {
            "translation": translation,
            "all_matches": all_matches,
            "source_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }

    def get_special_api_reference(self) -> Dict[str, Any]:
        """
        获取MyMemory翻译特殊API方法的引用规范
        """
        return {
            "translate_with_all_matches": {
                "description": "翻译并返回所有匹配结果，包括相似翻译和置信度信息",
                "parameters": {
                    "text": "要翻译的文本",
                    "source_lang": "源语言（可选，默认使用配置）",
                    "target_lang": "目标语言（可选，默认使用配置）"
                },
                "return_type": "Dict[str, Any] 包含翻译结果和所有匹配项的字典",
                "example": "translator.translate_with_all_matches('Hello world', 'en', 'fr')"
            }
        }