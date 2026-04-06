import json
from pathlib import Path
import subprocess
from tools.todo_mgr.todo_mgr import TodoManager
from tools.skill_loader.skill_loader import SkillLoader
from tools.task_mgr.task_mgr import TaskMgr
from tools.background_mgr.background_mgr import BackgroundMgr
from tools.system_tools.system_tools import SystemTools
from tools.msg_bus.msg_bus import MsgBus
from tools.team_mgr.team_mgr import TeamMgr
from tools.event_bus.event_bus import EventBus
from tools.worktree_mgr.worktree_mgr import WorktreeMgr

def detect_repo_root(cwd: Path) -> Path | None:
    """Return git repo root if cwd is inside a repo, else None."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return None
        root = Path(r.stdout.strip())
        return root if root.exists() else None
    except Exception:
        return None

WORKDIR = Path.cwd()
REPO_ROOT = detect_repo_root(WORKDIR) or WORKDIR

SYSTEM_TOOLS = SystemTools()
SKILL_LOADER = SkillLoader(WORKDIR)
TASKS = TaskMgr(WORKDIR)
BG = BackgroundMgr()
TODO = TodoManager()
BUS = MsgBus(WORKDIR)
TEAM = TeamMgr(WORKDIR)
EVENTS = EventBus(REPO_ROOT / ".worktrees" / "events.jsonl")
WORKTREES = WorktreeMgr(REPO_ROOT, TASKS, EVENTS)

TEAMMATE_HANDLERS = {
    "bash":                 lambda **kw: SYSTEM_TOOLS.run_bash(kw["command"]),
    "read_file":            lambda **kw: SYSTEM_TOOLS.run_read(kw["path"], kw.get("limit")),
    "write_file":           lambda **kw: SYSTEM_TOOLS.run_write(kw["path"], kw["content"]),
    "edit_file":            lambda **kw: SYSTEM_TOOLS.run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "send_message":         lambda **kw: BUS.send(kw["sender"], kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":           lambda **kw: json.dumps(BUS.read_inbox(kw["sender"]), indent=4),
    "claim_task":           lambda **kw: TASKS.claim_task(kw["task_id"], kw["sender"]),
    "task_list":            lambda **kw: TASKS.list_all()
}

TEAMMATE_TOOLS = [
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
                    "path": {"type": "string"}
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
            "name": "send_message", 
            "description": "Send message to a teammate.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "sender": {"type": "string"}, 
                    "to": {"type": "string"}, 
                    "content": {"type": "string"}, 
                    "msg_type": {"type": "string", "enum": list(BUS.get_valid_msg_types())}
                },
                "required": ["sender", "to", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox", 
            "description": "Read and drain your inbox.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "sender": {"type": "string"},
                },
                "required": ["sender"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "idle", 
            "description": "Signal that you have no more work. Enters idle polling phase.",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "claim_task", 
            "description": "Claim a task from the task board by ID.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "task_id": {"type": "integer"},
                    "sender": {"type": "string"},
                }, 
                "required": ["task_id", "sender"]
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
    }
]

TOOL_HANDLERS = {
    "task_create":          lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_update":          lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":            lambda **kw: TASKS.list_all(),
    "task_get":             lambda **kw: TASKS.get(kw["task_id"]),
    "task_bind_worktree":   lambda **kw: TASKS.bind_worktree(kw["task_id"], kw["worktree"], kw.get("owner", "")),
    "claim_task":           lambda **kw: TASKS.claim_task(kw["task_id"], "lead"),
    "worktree_create":      lambda **kw: WORKTREES.create(kw["name"], kw.get("task_id"), kw.get("base_ref", "HEAD")),
    "worktree_list":        lambda **kw: WORKTREES.list_all(),
    "worktree_status":      lambda **kw: WORKTREES.status(kw["name"]),
    "worktree_run":         lambda **kw: WORKTREES.run(kw["name"], kw["command"]),
    "worktree_keep":        lambda **kw: WORKTREES.keep(kw["name"]),
    "worktree_remove":      lambda **kw: WORKTREES.remove(kw["name"], kw.get("force", False), kw.get("complete_task", False)),
    "worktree_events":      lambda **kw: EVENTS.list_recent(kw.get("limit", 20)),
    "bash":                 lambda **kw: SYSTEM_TOOLS.run_bash(kw["command"]),
    "read_file":            lambda **kw: SYSTEM_TOOLS.run_read(kw["path"], kw.get("limit")),
    "write_file":           lambda **kw: SYSTEM_TOOLS.run_write(kw["path"], kw["content"]),
    "edit_file":            lambda **kw: SYSTEM_TOOLS.run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":                 lambda **kw: TODO.update(kw["items"]),
    "todo_reminder":        lambda **kw: TODO.get_reminder(),
    "load_skill":           lambda **kw: SKILL_LOADER.get_content(kw["name"]),
    "compact":              lambda **kw: "Manual compression requested.",
    "update_notifications": lambda **kw: BG.publish_notifications(kw["messages"]),
    "background_run":       lambda **kw: BG.run(kw["command"]),
    "check_background":     lambda **kw: BG.check(kw.get("task_id")),
    "spawn_teammate":       lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates":       lambda **kw: TEAM.list_all(),
    "send_message":         lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":           lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=4),
    "update_messages":      lambda **kw: BUS.publish_inbox_messages("lead", kw["messages"]),
    "broadcast":            lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request":     lambda **kw: TEAM.handle_shutdown_request(kw["teammate"]),
    "shutdown_response":    lambda **kw: TEAM.check_shutdown_status(kw.get("request_id", "")),
    "plan_approval":        lambda **kw: TEAM.handle_plan_review(kw["request_id"], kw["approve"], kw.get("feedback", "")),
    "idle":                 lambda **kw: "Lead does not idle.",
    "sun_sub_agent":        lambda **kw: "Lead does not idle.",
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
            "name": "task_bind_worktree",
            "description": "Bind a task to a worktree name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "worktree": {"type": "string"},
                    "owner": {"type": "string"},
                },
                "required": ["task_id", "worktree"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "claim_task", 
            "description": "Claim a task from the board by ID.",
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
            "name": "worktree_create",
            "description": "Create a git worktree and optionally bind it to a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "task_id": {"type": "integer"},
                    "base_ref": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_list",
            "description": "List worktrees tracked in .worktrees/index.json.",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_status",
            "description": "Show git status for one worktree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_run",
            "description": "Run a shell command in a named worktree directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "command": {"type": "string"}
                },
                "required": ["name", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_remove",
            "description": "Remove a worktree and optionally mark its bound task completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "force": {"type": "boolean"},
                    "complete_task": {"type": "boolean"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_keep",
            "description": "Mark a worktree as kept in lifecycle state without removing it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "worktree_events",
            "description": "List recent worktree/task lifecycle events from .worktrees/events.jsonl.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"}
                }
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
            "name": "todo_reminder", 
            "description": "If the rounds is exceeded 3 times, then call this function to remind the user.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "update_notifications", 
            "description": "Return and clear all pending completion notifications, then update the context.",
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
            "name": "background_run", 
            "description": "Run command in background thread. Returns task_id immediately.",
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
            "name": "check_background", 
            "description": "Check background task status. Omit task_id to list all.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "task_id": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_teammate", 
            "description": "Spawn a persistent teammate that runs in its own thread.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "name": {"type": "string"}, 
                    "role": {"type": "string"}, 
                    "prompt": {"type": "string"}
                }, 
                "required": ["name", "role", "prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_teammates", 
            "description": "List all teammates with name, role, status.",
            "parameters": {
                "type": "object", "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_message", 
            "description": "Send a message to a teammate's inbox.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "to": {"type": "string"}, 
                    "content": {"type": "string"}, 
                    "msg_type": {"type": "string", "enum": list(BUS.get_valid_msg_types())}
                }, 
                "required": ["to", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox", 
            "description": "Read and drain the lead's inbox.",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_messages", 
            "description": "Read and drain the lead's inbox then update the context.",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "broadcast", 
            "description": "Send a message to all teammates.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "content": {"type": "string"}
                }, 
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_request", 
            "description": "Request a teammate to shut down gracefully. Returns a request_id for tracking.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "teammate": {"type": "string"}
                }, 
                "required": ["teammate"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_response", 
            "description": "Check the status of a shutdown request by request_id.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "request_id": {"type": "string"}
                }, 
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plan_approval", 
            "description": "Approve or reject a teammate's plan. Provide request_id + approve + optional feedback.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "request_id": {"type": "string"}, 
                    "approve": {"type": "boolean"}, 
                    "feedback": {"type": "string"}
                }, 
                "required": ["request_id", "approve"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "idle", 
            "description": "Enter idle state (for lead -- rarely used).",
            "parameters": {
                "type": "object", 
                "properties": {}
            }
        }
    }
]

PARENT_TOOLS = CHILD_TOOLS
[
    {
        "type": "function",
        "function": {
            "name": "create_agent", 
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

SYSTEM_TOOLS.set_work_dir(WORKDIR)
BG.set_work_dir(WORKDIR)
TEAM.set_msg_bus(BUS)
TEAM.set_task_mgr(TASKS)
TEAM.set_tools(TEAMMATE_TOOLS)
TEAM.set_tool_handlers(TEAMMATE_HANDLERS)