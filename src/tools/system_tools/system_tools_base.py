from pathlib import Path

class SystemToolsBase:
    def __init__(self):
        self.work_dir = None

    def _safe_path(self, path: str) -> Path:
        path = (self.work_dir / path).resolve()
        if not path.is_relative_to(self.work_dir):
            raise ValueError(f"Path escapes workspace: {path}")
        return path