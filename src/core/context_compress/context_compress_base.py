from typing import Any
from pathlib import Path
from core.json.json_parser import get_json_parser
from core.model.base.model_base import ModelBase

class ContextCompressBase:
    def __init__(self, work_dir: Path, keep_recent: int):
        self.keep_recent = keep_recent
        self.transcript_dir = work_dir / ".transcripts"
        self.json_parser = get_json_parser()
        self.model = None
        self.model_name = None
        self.stream = True
        self.threshold = 50000

    def _get_model(self) -> ModelBase:
        return self.model
    
    def _get_model_name(self) -> str:
        return self.model_name
    
    def _get_stream(self) -> bool:
        return self.stream
    
    def _get_threshold(self) -> int:
        return self.threshold
    
    def _get_data(self, sub_tools: list, prompt: str) -> Any:
        history = []
        history.append({"role": "user", "content": prompt})
        data = {
            "model_name": self._get_model_name(),
            "messages": history,
            "stream": True,
            "max_tokens": 8000,
            "index": -1,
            "tools": sub_tools,
            "tool_choice": "auto",
            "extra": {},
        }
        return data
    
    def _estimate_tokens(self, messages: list) -> int:
        """Rough token count: ~4 chars per token."""
        return len(str(messages)) // 4