import time
from pathlib import Path
from core.json.json_parser import get_json_parser

class MsgBus:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir / ".team"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.json_parser = get_json_parser()
        self.valid_msg_types = {
            "message",
            "broadcast",
            "shutdown_request",
            "shutdown_response",
            "plan_approval_response",
        }

    def get_valid_msg_types(self) -> set:
        return self.valid_msg_types
    
    def publish_inbox_messages(self, name: str, messages: list) -> str:
        inbox = self.read_inbox(name)
        if inbox:
            messages.append({
                "role": "user",
                "content": f"<inbox>{self.json_parser.to_json_str(inbox, indent=2)}</inbox>",
            })
            messages.append({
                "role": "assistant",
                "content": "Noted inbox messages.",
            })

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        if msg_type not in self.valid_msg_types:
            return f"Error: Invalid type '{msg_type}'. Valid: {self.valid_msg_types}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        inbox_path = self.work_dir / f"{to}.jsonl"
        with open(inbox_path, "a") as f:
            json_line = self.json_parser.to_json_str(msg, indent=0)
            f.write(json_line + "\n")
        return f"Sent {msg_type} to {to}"
    
    def read_inbox(self, name: str) -> list:
        inbox_path = self.work_dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text().strip().splitlines():
            if line:
                messages.append(self.json_parser.parse(line))
        inbox_path.write_text("")
        return messages
    
    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"Broadcast to {count} teammates"