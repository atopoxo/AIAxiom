from typing import Any
from core.json.json_parser import get_json_parser
from core.model_operator.model_operator import ModelOperator

class AutoAgentBase(ModelOperator):
    def __init__(self):
        super().__init__()
        self.json_parser = get_json_parser()
    
    def _get_subagent_data(self, sub_tools: list, prompt: str) -> Any:
        history = []
        history.append({"role": "system", "content": self.get_subagent_prompt()})
        history.append({"role": "user", "content": prompt})
        data = {
            "model_name": self.get_model_name(),
            "messages": history,
            "stream": True,
            "max_tokens": 8000,
            "index": -1,
            "tools": sub_tools,
            "tool_choice": "auto",
            "extra": {},
        }
        return data