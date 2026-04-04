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
    def auto_compact(self, messages: list) -> list:
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