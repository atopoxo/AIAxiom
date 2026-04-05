from pathlib import Path
import time
from core.json.json_parser import get_json_parser
from tools.task_mgr.task_mgr_base import TaskMgrBase

class TaskMgr(TaskMgrBase):
    def __init__(self, work_dir: Path):
        super().__init__(work_dir)

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id, 
            "subject": subject, 
            "description": description,
            "status": "pending",
            "owner": "",
            "worktree": "",
            "blockedBy": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._save(task)
        self._next_id += 1
        return self.json_parser.to_json_str(task, indent=4)
    
    def get(self, task_id: int) -> str:
        return self.json_parser.to_json_str(self._load(task_id), indent=4)
    
    def exists(self, task_id: int) -> bool:
        return self._path(task_id).exists()
    
    def update(self, task_id: int, status: str = None, owner: str = None) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
        if owner is not None:
            task["owner"] = owner
        task["updated_at"] = time.time()
        self._save(task)
        return self.json_parser.to_json_str(task, indent=4)
    
    def bind_worktree(self, task_id: int, worktree: str, owner: str = "") -> str:
        task = self._load(task_id)
        task["worktree"] = worktree
        if owner:
            task["owner"] = owner
        if task["status"] == "pending":
            task["status"] = "in_progress"
        task["updated_at"] = time.time()
        self._save(task)
        return self.json_parser.to_json_str(task, indent=4)
    
    def unbind_worktree(self, task_id: int) -> str:
        task = self._load(task_id)
        task["worktree"] = ""
        task["updated_at"] = time.time()
        self._save(task)
        return self.json_parser.to_json_str(task, indent=4)
    
    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            task = self.json_parser.read_json_file(f)
            tasks.append(task)
        if not tasks:
            return "No tasks."
        status_prompt = "\nall tasks has three status:\n"
        status_prompt += "\n".join(["pending: [ ]", "in_progress: [>]", "completed: [x]"])
        status_prompt += "\nnow tasks status:\n"
        lines = []
        for t in tasks:
            marker = {
                "pending": "[ ]", 
                "in_progress": "[>]",
                "completed": "[x]"
            }.get(t.get("status", ""), "[?]")
            owner = f" owner={t['owner']}" if t.get("owner") else ""
            wt = f" wt={t['worktree']}" if t.get("worktree") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{owner}{wt}")
        status_prompt += "\n".join(lines)
        return status_prompt
    
    def scan_unclaimed_tasks(self) -> list:
        unclaimed = []
        for f in sorted(self.dir.glob("task_*.json")):
            task = self.json_parser.parse(f.read_text())
            if (task.get("status") == "pending"
                    and not task.get("owner")
                    and not task.get("blockedBy")):
                unclaimed.append(task)
        return unclaimed
    
    def claim_task(self, task_id: int, owner: str) -> str:
        with self.claim_lock:
            path = self.dir / f"task_{task_id}.json"
            if not path.exists():
                return f"Error: Task {task_id} not found"
            task = self.json_parser.parse(path.read_text())
            task["owner"] = owner
            task["status"] = "in_progress"
            path.write_text(self.json_parser.to_json_str(task, indent=4))
        return f"Claimed task #{task_id} for {owner}"