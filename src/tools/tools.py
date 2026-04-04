import json
from pathlib import Path
from tools.todo_mgr.todo_mgr import TodoManager
from tools.skill_loader.skill_loader import SkillLoader
from tools.task_mgr.task_mgr import TaskMgr
from tools.background_mgr.background_mgr import BackgroundMgr
from tools.system_tools.system_tools import SystemTools
from tools.message_bus.msg_bus import MsgBus
from tools.team_mgr.team_mgr import TeamMgr


WORKDIR = Path.cwd()

SYSTEM_TOOLS = SystemTools()
SYSTEM_TOOLS.set_work_dir(WORKDIR)
SKILL_LOADER = SkillLoader(WORKDIR)
TASKS = TaskMgr(WORKDIR)
BG = BackgroundMgr()
BG.set_work_dir(WORKDIR)
TODO = TodoManager()
BUS = MsgBus(WORKDIR)
TEAM = TeamMgr(WORKDIR)
TEAM.set_message_bus(BUS)
TEAM.set_system_tools(SYSTEM_TOOLS)


TOOL_HANDLERS = {
    "task_create":      lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_update":      lambda **kw: TASKS.update(kw["task_id"], kw.get("status"), kw.get("add_blocked_by"), kw.get("add_blocks")),
    "task_list":        lambda **kw: TASKS.list_all(),
    "task_get":         lambda **kw: TASKS.get(kw["task_id"]),
    "bash":             lambda **kw: SYSTEM_TOOLS.run_bash(kw["command"]),
    "read_file":        lambda **kw: SYSTEM_TOOLS.run_read(kw["path"], kw.get("limit")),
    "write_file":       lambda **kw: SYSTEM_TOOLS.run_write(kw["path"], kw["content"]),
    "edit_file":        lambda **kw: SYSTEM_TOOLS.run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":             lambda **kw: TODO.update(kw["items"]),
    "load_skill":       lambda **kw: SKILL_LOADER.get_content(kw["name"]),
    "compact":          lambda **kw: "Manual compression requested.",
    "background_run":   lambda **kw: BG.run(kw["command"]),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
    "spawn_teammate":  lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates":  lambda **kw: TEAM.list_all(),
    "send_message":    lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":      lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2),
    "broadcast":       lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names())
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
    }
]

PARENT_TOOLS = CHILD_TOOLS
# [
#     {
#         "type": "function",
#         "function": {
#             "name": "task", 
#             "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
#             "parameters": {
#                 "type": "object", 
#                 "properties": {
#                     "prompt": {"type": "string"}, 
#                     "description": {"type": "string", "description": "Short description of the task"}
#                 }, 
#                 "required": ["prompt"]
#             }
#         }
#     }
# ]