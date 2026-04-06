from typing import Any
from core.model.base.model_base import ModelBase
from core.context_compress.context_compress import ContextCompression
from core.model_operator.model_operator import ModelOperator
from core.json.json_parser import get_json_parser

class AgentBase(ModelOperator):
    def __init__(self):
        self.context_compress = None
        self.tools = []
        self.tool_handlers = {}
        self.custom_finish_reason = None
        self.system_prompt = None
        self.json_parser = get_json_parser()
    
    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def get_system_prompt(self) -> str:
        return self.system_prompt
    
    def set_context_compress(self, context_compress: ContextCompression):
        self.context_compress = context_compress

    def get_context_compress(self) -> ContextCompression:
        return self.context_compress
    
    def set_tools(self, tools: list):
        self.tools = tools

    def get_tools(self) -> list:
        return self.tools
    
    def set_tool_handlers(self, tool_handlers: dict):
        self.tool_handlers = tool_handlers

    def get_tool_handlers(self) -> dict:
        return self.tool_handlers
    
    def set_custom_finish_reason(self, reason: str):
        self.custom_finish_reason = reason

    def get_custom_finish_reason(self) -> str:
        return self.custom_finish_reason

    def is_finish(self, message: str, model: ModelBase, trunk: Any):
        custom_finish_reason = self.get_custom_finish_reason()
        if custom_finish_reason:
            return custom_finish_reason in message["conclusion"]
        else:
            return model.is_finish(trunk)