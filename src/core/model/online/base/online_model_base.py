from typing import Any, Generator
from core.model.base.model_base import ModelBase

class OnlineModelBase(ModelBase):
    def __init__(self, config: Any):
        super().__init__(config)