from typing import Any, List
class ModelBase:
    def __init__(self, config):
        self.config = config

    def get_response(self, data: Any) -> Any:
        raise NotImplementedError("Method not implemented.")
    
    def get_chunk(self, chunk: Any, stream: bool) -> Any:
        raise NotImplementedError("Method not implemented.")
    
    def message_update(self, message: Any, stream: bool, delta: Any = None, chunk: Any = None):
        raise NotImplementedError("Method not implemented.")
    
    def is_finish(self, chunk: Any = None) -> Any:
        raise NotImplementedError("Method not implemented.")