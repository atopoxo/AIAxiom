from typing import Any
from core.model.base.model_base import ModelBase
from core.json.json_parser import get_json_parser
from tools.tools import TOOL_HANDLERS, CHILD_TOOLS, PARENT_TOOLS, BG, BUS
from core.context_compress.context_compress import ContextCompression
from core.auto_agent.auto_agent_base import AutoAgentBase

class AutoAgent(AutoAgentBase):
    def __init__(self):
        super().__init__()
    
    def run_subagent(self, model: ModelBase, sub_tools: list, prompt: str) -> str:
        data = self._get_subagent_data(sub_tools=sub_tools, prompt=prompt)
        messages = data["messages"]
        rounds_since_todo = 0
        for _ in range(30):  # safety limit
            self.context_compress.compress(messages)
            message = self.get_model_result(data)
            if not message:
                continue
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, is_subagent=True):
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
        return messages[-1]["content"] if messages[-1]["role"] == "assistant" else "(no summary)"

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
        data["tools"] = PARENT_TOOLS
        while True:
            BG.publish_notifications(messages)
            BUS.publish_inbox_messages("lead", messages)
            self.context_compress.compress(messages)
            message = self.get_model_result(data)
            if not message:
                continue
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, is_subagent=False):
                break

            tool_results = []
            used_todo = False
            manual_compact = False
            for tool_call in message["tool_calls"]:
                try:
                    arguments = self.json_parser.parse(tool_call["arguments"])
                    if tool_call["name"] == "compact":
                        manual_compact = True
                        output = "Compressing..."
                    elif tool_call["name"] == "task":
                        output = self.run_subagent(model, CHILD_TOOLS, arguments["prompt"])
                    else:
                        handler = TOOL_HANDLERS.get(tool_call["name"])
                        output = handler(**arguments) if handler else f"Unknown tool: {tool_call['name']}"
                except Exception as ex:
                    output = f"[agent] excute tool[{tool_call['name']}] error: {str(ex)}"
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
                messages[:] = self.context_compress.auto_compact(messages)