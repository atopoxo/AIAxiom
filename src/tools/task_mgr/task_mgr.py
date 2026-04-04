from pathlib import Path
from core.json.json_parser import get_json_parser

class TaskMgr:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1
        self.json_parser = get_json_parser()

    def _max_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0
    
    def _load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return self.json_parser.parse(path.read_text())
    
    def _save(self, task: dict):
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(self.json_parser.to_json_str(task, indent=2))

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id, "subject": subject, "description": description,
            "status": "pending", "blocked_by": [], "blocks": [], "owner": "",
        }
        self._save(task)
        self._next_id += 1
        return self.json_parser.to_json_str(task, indent=2)
    
    def get(self, task_id: int) -> str:
        return self.json_parser.to_json_str(self._load(task_id), indent=2)
    
    def update(self, task_id: int, status: str = None,
               add_blocked_by: list = None, add_blocks: list = None) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
            if status == "completed":
                self._clear_dependency(task_id)
        if add_blocked_by:
            task["blocked_by"] = list(set(task["blocked_by"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
            for blocked_id in add_blocks:
                try:
                    blocked = self._load(blocked_id)
                    if task_id not in blocked["blocked_by"]:
                        blocked["blocked_by"].append(task_id)
                        self._save(blocked)
                except ValueError:
                    pass
        self._save(task)
        return self.json_parser.to_json_str(task, indent=2)
    
    def _clear_dependency(self, completed_id: int):
        for f in self.dir.glob("task_*.json"):
            task = self.json_parser.parse(f.read_text())
            if completed_id in task.get("blocked_by", []):
                task["blocked_by"].remove(completed_id)
                self._save(task)

    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            tasks.append(self.json_parser.parse(f.read_text()))
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            blocked = f" (blocked by: {t['blocked_by']})" if t.get("blocked_by") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{blocked}")
        return "\n".join(lines)