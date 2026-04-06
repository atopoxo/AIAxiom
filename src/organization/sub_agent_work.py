from typing import Any
from pathlib import Path
from tools.tools import TOOL_HANDLERS, CHILD_TOOLS, PARENT_TOOLS
from core.context_compress.context_compress import ContextCompression
from agents.coder.coder import Coder

class SubAgentWork:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.main_coder = Coder()
    
    def _get_subagent_data(self, sub_tools: list, prompt: str) -> Any:
        SUBAGENT_SYSTEM = f"You are a coding subagent at {self.work_dir}. Complete the given task, then summarize your findings."
        SUBAGENT_SYSTEM  += "if all the tasks are done, then return <<<-subagent-done->>>"
        history = []
        history.append({"role": "system", "content": SUBAGENT_SYSTEM})
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

    def run_subagent(self, prompt: str) -> str:
        sub_tools = CHILD_TOOLS
        data = self._get_subagent_data(sub_tools=sub_tools, prompt=prompt)
        self.sub_coder = Coder()
        self.sub_coder.loop(data=data)
        messages = data["messages"]
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
        self.main_coder.set_context_compress(self.get_context_compress())
        self.main_coder.set_tools(PARENT_TOOLS)
        self.main_coder.set_tool_handlers(TOOL_HANDLERS)
        self.main_coder.set_custom_finish_reason("<<<-done->>>")
        self.main_coder.set_model(self.get_model())
        self.main_coder.loop(data=data)