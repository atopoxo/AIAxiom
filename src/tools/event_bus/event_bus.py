from pathlib import Path
import time
from core.json.json_parser import get_json_parser

class EventBus:
    def __init__(self, log_path: Path):
        self.path = log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.json_parser = get_json_parser()
        if not self.path.exists():
            self.path.write_text("")
        
    def emit(
        self,
        event: str,
        task: dict | None = None,
        worktree: dict | None = None,
        error: str | None = None,
    ):
        payload = {
            "event": event,
            "timestamp": time.time(),
            "task": task or {},
            "worktree": worktree or {},
        }
        if error:
            payload["error"] = error
        with self.path.open("a", encoding="utf-8") as f:
            f.write(self.json_parser.to_json_str(payload) + "\n")

    def list_recent(self, limit: int = 20) -> str:
        n = max(1, min(int(limit or 20), 200))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        recent = lines[-n:]
        items = []
        for line in recent:
            try:
                items.append(self.json_parser.parse(line))
            except Exception:
                items.append({"event": "parse_error", "raw": line})
        return self.json_parser.to_json_str(items, indent=4)