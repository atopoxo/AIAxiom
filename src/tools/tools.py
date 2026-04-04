import subprocess
from pathlib import Path
from src.tools.todo_mgr import TodoManager
from src.tools.skill_loader.skill_loader import SkillLoader
from src.tools.task_mgr.task_mgr import TaskMgr

TODO = TodoManager()

WORKDIR = Path.cwd()

TASKS_DIR = WORKDIR / ".tasks"
SKILLS_DIR = WORKDIR / "skills"

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
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
    
def run_read(path: str, limit: int | None = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"
    
def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

SKILL_LOADER = SkillLoader(SKILLS_DIR)
TASKS = TaskMgr(TASKS_DIR)

TOOL_HANDLERS = {
    "task_create":  lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_update":  lambda **kw: TASKS.update(kw["task_id"], kw.get("status"), kw.get("add_blocked_by"), kw.get("add_blocks")),
    "task_list":    lambda **kw: TASKS.list_all(),
    "task_get":     lambda **kw: TASKS.get(kw["task_id"]),
    "bash":         lambda **kw: run_bash(kw["command"]),
    "read_file":    lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":   lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":    lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":         lambda **kw: TODO.update(kw["items"]),
    "load_skill":   lambda **kw: SKILL_LOADER.get_content(kw["name"]),
    "compact":      lambda **kw: "Manual compression requested.",
}

CHILD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "task_create", 
            "description": "Create a new task.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "subject": {"type": "string"}, 
                    "description": {"type": "string"}
                }, 
                "required": ["subject"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_update", 
            "description": "Update a task's status or dependencies.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "task_id": {"type": "integer"}, 
                    "status": {
                        "type": "string", 
                        "enum": ["pending", "in_progress", "completed"]
                    }, 
                    "add_blocked_by": {
                        "type": "array", 
                        "items": {"type": "integer"}
                    }, 
                    "add_blocks": {
                        "type": "array", 
                        "items": {"type": "integer"}
                    }
                }, 
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_list", 
            "description": "List all tasks with status summary.",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_get", 
            "description": "Get full details of a task by ID.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "task_id": {"type": "integer"}
                }, 
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bash", 
            "description": "Run a shell command.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "command": {"type": "string"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file", 
            "description": "Read file contents.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "path": {"type": "string"}, 
                    "limit": {"type": "integer"}
                }, 
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file", 
            "description": "Write content to file.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "path": {"type": "string"}, 
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file", 
            "description": "Replace exact text in file.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "path": {"type": "string"}, 
                    "old_text": {"type": "string"}, 
                    "new_text": {"type": "string"}
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "todo", 
            "description": "Update task list. Track progress on multi-step tasks.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "items": {
                        "type": "array", 
                        "item": {
                            "type": "object", 
                            "properties": {
                                "id": {"type": "string"}, 
                                "text": {"type": "string"}, 
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                            },
                            "required": ["id", "text", "status"]
                        }
                    }
                }, 
                "required": ["items"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill", 
            "description": "Load specialized knowledge by name.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "name": {
                        "type": "string", 
                        "description": "Skill name to load"
                    }
                }, 
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compact", 
            "description": "Trigger manual conversation compression.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "focus": {
                        "type": "string", 
                        "description": "What to preserve in the summary"
                    }
                }
            }
        }
    }
]

PARENT_TOOLS = CHILD_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "task", 
            "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "prompt": {"type": "string"}, 
                    "description": {"type": "string", "description": "Short description of the task"}
                }, 
                "required": ["prompt"]
            }
        }
    }
]