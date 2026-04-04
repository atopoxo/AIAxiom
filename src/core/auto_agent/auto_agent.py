from typing import Any
from core.model.base.model_base import ModelBase
from core.json.json_parser import get_json_parser
from tools.tools import TOOL_HANDLERS, CHILD_TOOLS, PARENT_TOOLS
from core.context_compress.context_compress import ContextCompression

class AutoAgent:
    def __init__(self):
        self.model = None
        self.model_name = None
        self.json_parser = get_json_parser()

    def _is_finish(self, message: str, is_subagent: bool = False):
        if is_subagent:
            return "<<<-subagent-done->>>" in message["conclusion"]
        else:
            return "<<<-done->>>" in message["conclusion"]
    
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
    
    def run_subagent(self, model: ModelBase, sub_tools: list, prompt: str) -> str:
        data = self._get_subagent_data(sub_tools=sub_tools, prompt=prompt)
        messages = data["messages"]
        stream = data["stream"]
        rounds_since_todo = 0
        for _ in range(30):  # safety limit
            self.context_compress.compress(messages)
            response = model.get_response(data=data)
            message = {
                "reasoning": "",
                "conclusion": "",
                "tool_calls": []
            }
            if stream:
                for chunk in response:
                    model.message_update(message, stream, chunk=chunk)
            else:
                message = model.message_update(message, stream, chunk=response)
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["tool_calls"]
            })
            if self._is_finish(message, is_subagent=True):
                break

            tool_results = []
            used_todo = False
            manual_compact = False
            for tool_call in message["tool_calls"]:
                arguments = self.json_parser.parse(tool_call["arguments"])
                if tool_call["name"] == "compact":
                    manual_compact = True
                    output = "Compressing..."
                else:
                    handler = TOOL_HANDLERS.get(tool_call["name"])
                    output = handler(**arguments) if handler else f"Unknown tool: {tool_call['name']}"
                print(output[:200])
                
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": output
                })
                if tool_call["name"] == "todo":
                    used_todo = True
            # messages.append({"role": "user", "content": self.json_parser.to_json_str(tool_results)})
            messages.extend(tool_results)
            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
            if rounds_since_todo >= 3:
                tool_results.insert(0, {"role": "user", "content": "<reminder>Update your todos.</reminder>"})
            if manual_compact:
                print("[manual compact]")
                messages[:] = self.context_compressauto_compact(messages)
        return messages[-1]["content"] if messages[-1]["role"] == "assistant" else "(no summary)"
    
    def set_model(self, model: ModelBase):
        self.model = model

    def get_model(self) -> ModelBase:
        return self.model

    def get_model_name(self) -> str:
        return self.model_name

    def set_model_name(self, model_name: str):
        self.model_name = model_name

    def set_subagent_prompt(self, prompt: str):
        self.subagent_prompt = prompt

    def get_subagent_prompt(self) -> str:
        return self.subagent_prompt
    
    def set_context_compress(self, context_compress: ContextCompression):
        self.context_compress = context_compress

    def get_context_compress(self) -> ContextCompression:
        return self.context_compress

    def loop(self, data: Any):
        rounds_since_todo = 0
        data["model_name"] = self.get_model_name()
        model = self.get_model()
        messages = data["messages"]
        stream = data["stream"]
        data["tools"] = PARENT_TOOLS
        while True:
            self.context_compress.compress(messages)
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
            else:
                model.message_update(message, stream, chunk=response)
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self._is_finish(message, is_subagent=False):
                break

            tool_results = []
            used_todo = False
            manual_compact = False
            for tool_call in message["tool_calls"]:
                arguments = self.json_parser.parse(tool_call["arguments"])
                if tool_call["name"] == "compact":
                    manual_compact = True
                    output = "Compressing..."
                elif tool_call["name"] == "task":
                    output = self.run_subagent(model, CHILD_TOOLS, arguments["prompt"])
                else:
                    handler = TOOL_HANDLERS.get(tool_call["name"])
                    output = handler(**arguments) if handler else f"Unknown tool: {tool_call['name']}"
                print(output)
                
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": output
                })
                if tool_call["name"] == "todo":
                    used_todo = True
            # messages.append({"role": "user", "content": self.json_parser.to_json_str(tool_results)})
            messages.extend(tool_results)
            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
            if rounds_since_todo >= 3:
                tool_results.insert(0, {"role": "user", "content": "<reminder>Update your todos.</reminder>"})
            if manual_compact:
                print("[manual compact]")
                messages[:] = self.context_compressauto_compact(messages)