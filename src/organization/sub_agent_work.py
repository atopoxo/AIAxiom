from typing import Any
from pathlib import Path
from tools.tools import TOOL_HANDLERS, CHILD_TOOLS, PARENT_TOOLS
from core.context_compress.context_compress import ContextCompression
from agents.coder.coder import Coder
from core.model.base.model_base import ModelBase

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
        self.sub_coder.set_model(self.get_model())
        self.sub_coder.set_model_name(self.get_model_name())
        self.sub_coder.set_stream(self.get_stream())
        self.sub_coder.loop(data=data)
        messages = data["messages"]
        return messages[-1]["content"] if messages[-1]["role"] == "assistant" else "(no summary)"
    
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

    def set_context_compress(self, context_compress: ContextCompression):
        self.context_compress = context_compress

    def get_context_compress(self) -> ContextCompression:
        return self.context_compress

    def loop(self, query: str):
        sys_prompt = ("You are a coding agent at {WORKDIR}. "
                    "Use task + worktree tools for multi-task work. "
                    "For parallel or risky changes: create tasks, allocate worktree lanes, "
                    "run commands in those lanes, then choose keep/remove for closeout. "
                    "Use worktree_events when you need lifecycle visibility.")
        sys_prompt  += "you must finish all the tasks if and only if all the tasks are done, then return <<<-done->>>"
        self.main_coder.set_system_prompt(sys_prompt)
        self.main_coder.set_context_compress(self.get_context_compress())
        self.main_coder.set_tools(PARENT_TOOLS)
        self.main_coder.set_tool_handlers(TOOL_HANDLERS)
        # self.main_coder.set_custom_finish_reason("<<<-done->>>")
        self.main_coder.set_model(self.get_model())
        self.main_coder.set_model_name(self.get_model_name())
        self.main_coder.set_stream(self.get_stream())
        self.main_coder.loop('coder', query)