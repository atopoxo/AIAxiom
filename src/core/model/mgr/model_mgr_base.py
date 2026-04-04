import os
from typing import Any, Dict
from core.json.json_parser import get_json_parser
from core.model.base.model_base import ModelBase

class ModelMgrBase:
    def __init__(self):
        self.json_parser = get_json_parser()
        self.default_model_configs = self._get_model_config_from_file('default_model_config.json')
        self.custom_model_configs = self._get_model_config_from_file('custom_model_config.json')
        self.models = {}

    def _get_model_config_from_file(self, file_name: str) -> Any:
        try:
            config_path = os.path.join(os.path.dirname(__file__), '../../../../', f'assets/config/{file_name}')
            config_path = os.path.abspath(config_path)
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = f.read()
            if raw_config:
                obj = self.json_parser.parse(raw_config)
                result = self._transform_valid_api_key(obj)
                return result
            else:
                return {}
        except Exception as error:
            print(f'加载模型配置失败: {error}')
            return {}
        
    def _add_custom_model_config(self, model_config: Dict):
        for model_config in self.custom_model_configs['models']:
            if model_config['id'] == model_config['id']:
                return
        self.custom_model_configs['models'].append(model_config)

    def _remove_custom_model_config(self, id: str):
        for model_config in self.custom_model_configs['models']:
            if model_config['id'] == id:
                self.custom_model_configs['models'].remove(model_config)
                break
        
    def _get_model_by_config(self, model_config: Dict) -> ModelBase:
        id = model_config['id']
        if id not in self.models:
            self._create_model(model_config, id)
        model = self.models.get(id)
        if not model:
            raise Exception(f"Model {id} not found")
        return model
    
    def _get_default_model_config(self, id: str) -> Any:
        for model in self.default_model_configs['models']:
            if model['id'] == id:
                return model
        return None
    
    def _get_custom_model_config(self, id: str) -> Any:
        for model in self.custom_model_configs['models']:
            if model['id'] == id:
                return model
        return None
        
    def _create_model(self, model_config: Any, id: str):
        platform = model_config['platform']
        code_name = model_config['code_name']
        try:
            from importlib import import_module
            model_file = import_module('core.model.{platform}.models.{code_name}.modeling'.format(platform=platform, code_name=code_name))
            instance = model_file.get_class(model_config)
            self.models[id] = instance
        except ImportError:
            raise ImportError(f"Could not import module platform={platform},model_name={code_name}")
        
    def _transform_valid_api_key(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return [self._transform_valid_api_key(item) for item in obj]
        elif obj is not None and isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == 'example_key':
                    result['api_key'] = "tc-" + str(value)
                else:
                    result[key] = self._transform_valid_api_key(value)
            return result
        else:
            return obj