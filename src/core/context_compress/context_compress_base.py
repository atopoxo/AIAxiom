from typing import Any
from pathlib import Path
from core.json.json_parser import get_json_parser
from core.model_operator.model_operator import ModelOperator

class ContextCompressBase(ModelOperator):
    def __init__(self, work_dir: Path, keep_recent: int):
        super().__init__()
        self.keep_recent = keep_recent
        self.transcript_dir = work_dir / ".transcripts"
        self.json_parser = get_json_parser()
        self.threshold = 50000
    
    def _get_threshold(self) -> int:
        return self.threshold
    
    def _estimate_tokens(self, messages: list) -> int:
        """Rough token count: ~4 chars per token."""
        return len(str(messages)) // 4
    
    def _clean_message_for_json(self, msg):
        if not isinstance(msg, dict):
            return msg
        cleaned = {}
        for key, value in msg.items():
            if key == "tool_calls" and isinstance(value, list):
                # 清理tool_calls列表
                cleaned_tool_calls = []
                for tool_call in value:
                    if isinstance(tool_call, dict):
                        # 清理单个tool_call
                        cleaned_tool_call = {}
                        for tc_key, tc_value in tool_call.items():
                            # 跳过非JSON可序列化的值
                            if self.json_parser.is_json_serializable(tc_value):
                                cleaned_tool_call[tc_key] = tc_value
                            else:
                                # 替换为字符串表示
                                cleaned_tool_call[tc_key] = str(tc_value)
                        cleaned_tool_calls.append(cleaned_tool_call)
                    else:
                        # 如果不是dict，转换为字符串
                        cleaned_tool_calls.append(str(tool_call))
                cleaned[key] = cleaned_tool_calls
            elif self.json_parser.is_json_serializable(value):
                cleaned[key] = value
            else:
                # 对于非JSON可序列化的值，使用其字符串表示
                cleaned[key] = str(value)
        
        return cleaned