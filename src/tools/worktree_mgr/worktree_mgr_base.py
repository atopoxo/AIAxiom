from pathlib import Path
import subprocess
import re
import time
from tools.task_mgr.task_mgr import TaskMgr
from tools.event_bus.event_bus import EventBus
from core.json.json_parser import get_json_parser

class WorktreeMgrBase:
    def __init__(self, work_dir: Path, tasks: TaskMgr, event_bus: EventBus):
        self.work_dir = work_dir
        self.tasks = tasks
        self.event_bus = event_bus
        self.worktree_dir = work_dir / ".worktrees"
        self.worktree_dir.mkdir(parents=True, exist_ok=True)
        self.json_parser = get_json_parser()
        self.index_path = self.worktree_dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(self.json_parser.to_json_str({"worktrees": []}, indent=4))
        self.git_available = self._is_git_repo()

    def _is_git_repo(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False
        
    def _run_git(self, args: list[str]) -> str:
        if not self.git_available:
            raise RuntimeError("Not in a git repository. worktree tools require git.")
        r = subprocess.run(
            ["git", *args],
            cwd=self.work_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            output = r.stdout if r.stdout else ""
            error = r.stderr if r.stderr else ""
            msg = (output + error).strip()
            raise RuntimeError(msg or f"git {' '.join(args)} failed")
        output = r.stdout if r.stdout else ""
        error = r.stderr if r.stderr else ""
        return (output + error).strip() or "(no output)"
    
    def _load_index(self) -> dict:
        return self.json_parser.parse(self.index_path.read_text())
    
    def _save_index(self, data: dict):
        self.index_path.write_text(self.json_parser.to_json_str(data, indent=4))

    def _find(self, name: str) -> dict | None:
        idx_map = self._load_index()
        for worktree in idx_map.get("worktrees", []):
            if worktree.get("name") == name:
                return worktree
        return None
    
    def _validate_name(self, name: str):
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", name or ""):
            raise ValueError(
                "Invalid worktree name. Use 1-40 chars: letters, numbers, ., _, -"
            )