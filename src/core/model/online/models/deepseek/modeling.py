import copy
from typing import Any, List
from openai import OpenAI
from core.function.base_function import *
from core.model.online.base.online_model_base import OnlineModelBase

class DeepSeek(OnlineModelBase):
    def __init__(self, config):
        super().__init__(config)
        self.client: OpenAI = OpenAI(
            api_key=config['api_key'],
            base_url=config['url']
        )

    def _get_message(self, message: Any) -> Any:
        if message:
            return {
                "reasoning": getattr(message, "reasoning_content", None) if hasattr(message, "reasoning_content") else None,
                "conclusion": getattr(message, "content", None) if hasattr(message, "content") else None,
                "tool_calls": [],
                "raw_tool_calls": getattr(message, "tool_calls", None) if hasattr(message, "tool_calls") else []
            }
        else:
            return {
                "reasoning": None,
                "conclusion": None,
                "tool_calls": [],
                "raw_tool_calls": []
            }

    def _tool_call_update(self, message: Any, tool_call: Any) -> Any:
        if tool_call.id is None:
            tool_calls = message["tool_calls"]
            current_tool_call = tool_calls[-1]
            if tool_call.function.arguments:
                current_tool_call["arguments"] += tool_call.function.arguments
        else:
            current_tool_call = {
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            }
            message["tool_calls"].append(current_tool_call)
            message["raw_tool_calls"].append(tool_call)
        
    def get_response(self, data: Any) -> Any:
        client = self.client
        index = data["index"]
        messages = data["messages"]
        extra = data["extra"]
        
        params = {
            "model": data["model_name"],
            "messages": messages[:index + 1] if index >= 0 else messages,
            "max_tokens": data["max_tokens"],
            "stream": data["stream"],
            "tool_choice": data["tool_choice"],
            "tools": data["tools"]
        }
        if extra:
            extra_body = {'extra_body': extra}
            params = merge(copy.deepcopy(params), extra_body)
        
        return client.chat.completions.create(**params)
    
    def get_chunk(self, chunk: Any, stream: bool) -> Any:
        choice = chunk.choices[0] if chunk.choices else None
        if stream:
            message = choice.delta if choice else None
        else:
            message = choice.message if choice else None
        return self._get_message(message)
        
    def message_update(self, message: Any, stream: bool, delta: Any = None, chunk: Any = None):
        if delta is None:
            delta = self.get_chunk(chunk, stream=stream)
        if delta: 
            if delta["conclusion"]:
                message["conclusion"] += delta["conclusion"]
            if delta["raw_tool_calls"]:
                for tool_call in delta["raw_tool_calls"]:
                    self._tool_call_update(message, tool_call)
            if delta["reasoning"]:
                message["reasoning"] += delta["reasoning"]
        
    def is_finish(self, chunk: Any = None) -> Any:
        choice = chunk.choices[0] if hasattr(chunk, 'choices') and chunk.choices else chunk
        if choice and hasattr(choice, 'finish_reason'):
            return choice.finish_reason != "tool_calls"
        return False
    
    def get_tool_calls(self, tool_calls: List[Any]) -> Any:
        result = []
        for tool_call in tool_calls:
            new_tool_call = {
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            }
            result.append(new_tool_call)
        return result
    
def get_class(config):
    return DeepSeek(config)