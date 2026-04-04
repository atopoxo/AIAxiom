from typing import Dict, Any
from core.function.base_function import *
from core.model.mgr.model_mgr_base import ModelMgrBase
from core.model.base.model_base import ModelBase

@singleton
class ModelMgr(ModelMgrBase):
    def __init__(self):
        super().__init__()
    
    def get_model(self, mode_id: str) -> ModelBase:
        model = None
        model_config = self._get_default_model_config(mode_id)
        if not model_config:
            model_config = self._get_custom_model_config(mode_id)
        if model_config:
            model = self._get_model_by_config(model_config)
        return model
    
    def add_model_config(self, model_config: Dict):
        self._add_custom_model_config(model_config)

    def remove_model_config(self, id: str):
        self._remove_custom_model_config(id)