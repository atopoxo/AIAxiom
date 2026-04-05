from pathlib import Path
import threading
from core.json.json_parser import get_json_parser

class TaskMgrBase:
    def __init__(self, work_dir: Path):
        self.dir = work_dir / ".tasks"
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1
        self.json_parser = get_json_parser()
        self.claim_lock = threading.Lock()

    def _max_id(self) -> int:
        ids = []
        for f in self.dir.glob("task_*.json"):
            try:
                ids.append(int(f.stem.split("_")[1]))
            except Exception:
                pass
        return max(ids) if ids else 0
    
    def _path(self, task_id: int) -> Path:
        return self.dir / f"task_{task_id}.json"
    
    def _load(self, task_id: int) -> dict:
        path = self._path(task_id)
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        result = self.json_parser.read_json_file(path)
        return result
    
    def _save(self, task: dict):
        path = self._path(task['id'])
        json_str = self.json_parser.to_json_str(task, indent=4)
        path.write_text(json_str, encoding='utf-8')
    
    def _clear_dependency(self, completed_id: int):
        for f in self.dir.glob("task_*.json"):
            task = self.json_parser.read_json_file(f)
            if completed_id in task.get("blocked_by", []):
                task["blocked_by"].remove(completed_id)
                self._save(task)