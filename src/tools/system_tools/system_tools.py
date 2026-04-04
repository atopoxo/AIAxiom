import subprocess
from tools.system_tools.system_tools_base import SystemToolsBase

class SystemTools(SystemToolsBase):
    def __init__(self):
        super().__init__()

    def set_work_dir(self, work_dir: str):
        self.work_dir = work_dir

    def run_bash(self, command: str) -> str:
        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            return "Error: Dangerous command blocked"
        try:
            r = subprocess.run(command, shell=True, cwd=self.work_dir,
                            capture_output=True, timeout=120)
            # 解码输出，优先使用UTF-8，失败时使用系统编码
            try:
                stdout = r.stdout.decode('utf-8') if r.stdout else ""
            except UnicodeDecodeError:
                import locale
                stdout = r.stdout.decode(locale.getpreferredencoding(), errors='replace') if r.stdout else ""
            
            try:
                stderr = r.stderr.decode('utf-8') if r.stderr else ""
            except UnicodeDecodeError:
                import locale
                stderr = r.stderr.decode(locale.getpreferredencoding(), errors='replace') if r.stderr else ""
            
            out = stdout + stderr.strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (120s)"
        
    def run_read(self, path: str, limit: int | None = None) -> str:
        try:
            text = self.__safe_path(path).read_text()
            lines = text.splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
            return "\n".join(lines)[:50000]
        except Exception as e:
            return f"Error: {e}"
        
    def run_write(self, path: str, content: str) -> str:
        try:
            fp = self.__safe_path(path)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error: {e}"
        
    def run_edit(self, path: str, old_text: str, new_text: str) -> str:
        try:
            fp = self._safe_path(path)
            content = fp.read_text()
            if old_text not in content:
                return f"Error: Text not found in {path}"
            fp.write_text(content.replace(old_text, new_text, 1))
            return f"Edited {path}"
        except Exception as e:
            return f"Error: {e}"