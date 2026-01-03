import translatekit as tkit
from translatekit import *

a = dir(tkit)
for i in a:
    if isinstance(getattr(tkit, i), type) and issubclass(getattr(tkit, i), TranslatorBase):
        target_class = getattr(tkit, i)
        print(f'{i}: {target_class.METADATA.short_description}')
        for argu in target_class.DEFAULT_API_KEY:
            if argu in dir(TranslationConfig):
                print('警告：api_setting参数名与类属性名重复，请修改API_KEY参数名')