import time
from pathlib import Path
from core.model.base.model_base import ModelBase
from core.context_compress.context_compress_base import ContextCompressBase

class ContextCompression(ContextCompressBase):
    def __init__(self, work_dir: Path, keep_recent: int):
        super().__init__(work_dir, keep_recent)
        
    def set_model(self, model: ModelBase):
        self.model = model
    
    def set_model_name(self, model_name: str):
        self.model_name = model_name
    
    def set_stream(self, stream: bool):
        self.stream = stream
    
    def set_threshold(self, threshold: int):
        self.threshold = threshold
    
    def compress(self, messages: list) -> list:
        self.micro_compact(messages=messages)
        if self._estimate_tokens(messages) > self._get_threshold():
            print("[auto_compact triggered]")
            messages[:] = self.auto_compact(messages)

    # -- Layer 1: micro_compact - replace old tool results with placeholders --
    def micro_compact(self, messages: list) -> list:
        tool_results = []
        for msg_idx, msg in enumerate(messages):
            if msg["role"] == "tool":
                tool_results.append((msg_idx, msg))
        if len(tool_results) <= self.keep_recent:
            return messages
        else:
            tool_name_map = {}
            for msg in messages:
                if msg.get("role") == "assistant":
                    tool_calls = self.model.get_tool_calls(msg.get("tool_calls", []))
                    for tool_call in tool_calls:
                        tool_id = tool_call.get("id")
                        tool_name = tool_call.get("name")
                        if tool_id and tool_name:
                            tool_name_map[tool_id] = tool_name
            to_clear = tool_results[:-self.keep_recent]
            for _, tool_result in to_clear:
                content = tool_result.get("content", "")
                if isinstance(content, str) and len(content) > 100:
                    tool_id = tool_result.get("tool_call_id", "")
                    tool_name = tool_name_map.get(tool_id, "unknown")
                    tool_result["content"] = f"[Previous: used {tool_name}]"
            return messages
    
    # -- Layer 2: auto_compact - save transcript, summarize, replace messages --
    def auto_compact(self, messages: list, filters: list) -> list:
        self.transcript_dir.mkdir(exist_ok=True)
        transcript_path = self.transcript_dir / f"transcript_{int(time.time())}.jsonl"
        with open(transcript_path, "w") as f:
            for msg in messages:
                f.write(self.json_parser.to_json_str(msg) + "\n")
        print(f"[transcript saved: {transcript_path}]")
        # Ask LLM to summarize
        model = self._get_model()
        stream = self._get_stream()
        conversation_text = self.json_parser.to_json_str(messages)[:80000]
        prompt = f"""
            Summarize this conversation for continuity. Include: 
            1) What was accomplished, 2) Current state, 3) Key decisions made.
            Be concise but preserve critical details.
            {conversation_text}
        """
        data = self._get_data(sub_tools=[], prompt=prompt)
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
            model.message_update(message, stream, chunk=response)
        summary = message["conclusion"]
        return [
            {"role": "user", "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}"},
            {"role": "assistant", "content": "Understood. I have the context from the summary. Continuing."},
        ]
    
    def _clean_message_for_json(self, msg):
        """清理消息对象，确保它可以被JSON序列化"""
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
                            if self._is_json_serializable(tc_value):
                                cleaned_tool_call[tc_key] = tc_value
                            else:
                                # 替换为字符串表示
                                cleaned_tool_call[tc_key] = str(tc_value)
                        cleaned_tool_calls.append(cleaned_tool_call)
                    else:
                        # 如果不是dict，转换为字符串
                        cleaned_tool_calls.append(str(tool_call))
                cleaned[key] = cleaned_tool_calls
            elif self._is_json_serializable(value):
                cleaned[key] = value
            else:
                # 对于非JSON可序列化的值，使用其字符串表示
                cleaned[key] = str(value)
        
        return cleaned
    
    def _is_json_serializable(self, value):
        """检查值是否可以被JSON序列化"""
        try:
            import json
            json.dumps(value)
            return True
        except (TypeError, ValueError):
            return False