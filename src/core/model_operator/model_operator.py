from typing import Any
from core.model.base.model_base import ModelBase

class ModelOperator:
    def __init__(self):
        self.model = None
        self.model_name = None
        self.stream = True

    def get_model(self) -> ModelBase:
        return self.model
    
    def set_model(self, model: ModelBase):
        self.model = model
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def set_model_name(self, model_name: str):
        self.model_name = model_name
    
    def get_stream(self) -> bool:
        return self.stream
    
    def set_stream(self, stream: bool):
        self.stream = stream

    def get_model_contex(self, tools: list, query: str | None, prompt: str | None) -> Any:
        history = []
        if prompt:
            history.append({"role": "system", "content": prompt})
        if query:
            history.append({"role": "user", "content": query})
        data = {
            "model_name": self.get_model_name(),
            "messages": history,
            "stream": True,
            "max_tokens": 8000,
            "index": -1,
            "tools": tools,
            "tool_choice": "auto",
            "extra": {},
        }
        return data
        
    def get_model_result(self, data: Any):
        message = None
        last_trunk = None
        model = self.get_model()
        stream = self.get_stream()
        try:
            response = model.get_response(data=data)
            message = {
                "reasoning": "",
                "conclusion": "",
                "tool_calls": [],
                "raw_tool_calls": []
            }
            if stream:
                for chunk in response:
                    model.message_update(message, stream, chunk=chunk)
                    last_trunk = chunk
            else:
                message = model.message_update(message, stream, chunk=response)
                last_trunk = response
        except Exception as ex:
            print(f"model return error: {ex}")
        return message, last_trunk