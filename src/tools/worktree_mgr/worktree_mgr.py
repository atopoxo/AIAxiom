from pathlib import Path
import subprocess
import re
import time
from tools.task_mgr.task_mgr import TaskMgr
from tools.event_bus.event_bus import EventBus
from core.json.json_parser import get_json_parser
from tools.worktree_mgr.worktree_mgr_base import WorktreeMgrBase

class WorktreeMgr(WorktreeMgrBase):
    def __init__(self, work_dir: Path, tasks: TaskMgr, event_bus: EventBus):
        super().__init__(work_dir, tasks=tasks, event_bus=event_bus)
        
    def create(self, name: str, task_id: int = None, base_ref: str = "HEAD") -> str:
        self._validate_name(name)
        if self._find(name):
            raise ValueError(f"Worktree '{name}' already exists in index")
        if task_id is not None and not self.tasks.exists(task_id):
            raise ValueError(f"Task {task_id} not found")
        path = self.worktree_dir / name
        branch = f"worktree/{name}"
        self.event_bus.emit(
            "worktree.create.before",
            task={"id": task_id} if task_id is not None else {},
            worktree={"name": name, "base_ref": base_ref},
        )
        try:
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])
            entry = {
                "name": name,
                "path": str(path),
                "branch": branch,
                "task_id": task_id,
                "status": "active",
                "created_at": time.time(),
            }
            idx_map = self._load_index()
            idx_map["worktrees"].append(entry)
            self._save_index(idx_map)
            if task_id is not None:
                self.tasks.bind_worktree(task_id, name)
            self.event_bus.emit(
                "worktree.create.after",
                task={"id": task_id} if task_id is not None else {},
                worktree={
                    "name": name,
                    "path": str(path),
                    "branch": branch,
                    "status": "active",
                },
            )
            return self.json_parser.to_json_str(entry, indent=4)
        except Exception as e:
            self.event_bus.emit(
                "worktree.create.failed",
                task={"id": task_id} if task_id is not None else {},
                worktree={"name": name, "base_ref": base_ref},
                error=str(e),
            )
            raise

    def list_all(self) -> str:
        idx_map = self._load_index()
        worktrees = idx_map.get("worktrees", [])
        if not worktrees:
            return "No worktrees in index."
        lines = []
        for worktree in worktrees:
            suffix = f" task={worktree['task_id']}" if worktree.get("task_id") else ""
            lines.append(
                f"[{worktree.get('status', 'unknown')}] {worktree['name']} -> "
                f"{worktree['path']} ({worktree.get('branch', '-')}){suffix}"
            )
        return "\n".join(lines)
    
    def status(self, name: str) -> str:
        worktree = self._find(name)
        if not worktree:
            return f"Error: Unknown worktree '{name}'"
        path = Path(worktree["path"])
        if not path.exists():
            return f"Error: Worktree path missing: {path}"
        r = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        text = (r.stdout + r.stderr).strip()
        return text or "Clean worktree"
    
    def run(self, name: str, command: str) -> str:
        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            return "Error: Dangerous command blocked"
        worktree = self._find(name)
        if not worktree:
            return f"Error: Unknown worktree '{name}'"
        path = Path(worktree["path"])
        if not path.exists():
            return f"Error: Worktree path missing: {path}"
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (300s)"
        
    def remove(self, name: str, force: bool = False, complete_task: bool = False) -> str:
        worktree = self._find(name)
        if not worktree:
            return f"Error: Unknown worktree '{name}'"
        self.event_bus.emit(
            "worktree.remove.before",
            task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
            worktree={"name": name, "path": worktree.get("path")},
        )
        try:
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(worktree["path"])
            self._run_git(args)
            if complete_task and worktree.get("task_id") is not None:
                task_id = worktree["task_id"]
                before = self.json_parser.parse(self.tasks.get(task_id))
                self.tasks.update(task_id, status="completed")
                self.tasks.unbind_worktree(task_id)
                self.event_bus.emit(
                    "task.completed",
                    task={
                        "id": task_id,
                        "subject": before.get("subject", ""),
                        "status": "completed",
                    },
                    worktree={"name": name},
                )
            idx_map = self._load_index()
            for item in idx_map.get("worktrees", []):
                if item.get("name") == name:
                    item["status"] = "removed"
                    item["removed_at"] = time.time()
            self._save_index(idx_map)
            self.event_bus.emit(
                "worktree.remove.after",
                task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
                worktree={"name": name, "path": worktree.get("path"), "status": "removed"},
            )
            return f"Removed worktree '{name}'"
        except Exception as e:
            self.event_bus.emit(
                "worktree.remove.failed",
                task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
                worktree={"name": name, "path": worktree.get("path")},
                error=str(e),
            )
            raise

    def keep(self, name: str) -> str:
        worktree = self._find(name)
        if not worktree:
            return f"Error: Unknown worktree '{name}'"
        idx_map = self._load_index()
        kept = None
        for item in idx_map.get("worktrees", []):
            if item.get("name") == name:
                item["status"] = "kept"
                item["kept_at"] = time.time()
                kept = item
        self._save_index(idx_map)
        self.event_bus.emit(
            "worktree.keep",
            task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
            worktree={
                "name": name,
                "path": worktree.get("path"),
                "status": "kept",
            },
        )
        return self.json_parser.to_json_str(kept, indent=4) if kept else f"Error: Unknown worktree '{name}'"