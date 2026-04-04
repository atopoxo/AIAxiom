import threading
import uuid
import subprocess
from pathlib import Path

class BackgroundMgrBase:
    def __init__(self):
        self.tasks = {}  # task_id -> {status, result, command}
        self.notification_queue = []  # completed task results
        self.task_lock = threading.Lock()
        self.work_dir = Path.cwd()
    
    def _execute(self, task_id: str, command: str):
        """Thread target: run subprocess, capture output, push to queue."""
        try:
            r = subprocess.run(
                command, shell=True, cwd=self.work_dir,
                capture_output=True, text=True, timeout=300
            )
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            output = f"Error: {e}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        with self.task_lock:
            self.notification_queue.append({
                "task_id": task_id,
                "status": status,
                "command": command[:80],
                "result": (output or "(no output)")[:500],
            })
    
    def _drain_notifications(self) -> list:
        """Return and clear all pending completion notifications."""
        with self.task_lock:
            notifs = list(self.notification_queue)
            self.notification_queue.clear()
        return notifs