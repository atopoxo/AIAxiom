import time
from pathlib import Path
import uuid
import threading
from core.json.json_parser import get_json_parser
from core.model_operator.model_operator import ModelOperator

class TeamMgrBase(ModelOperator):
    def __init__(self, work_dir: Path):
        super().__init__()
        self.work_dir = work_dir / ".team"
        self.work_dir.mkdir(exist_ok=True)
        self.config_path = self.work_dir / "config.json"
        self.json_parser = get_json_parser()
        self.config = self._load_config()
        self.threads = {}
        self.msg_bus = None
        self.system_tools = None
        self.tracker_lock = threading.Lock()
        self.shutdown_requests = {}
        self.plan_requests = {}
        self.idle_timeout = 60
        self.poll_interval = 5
        self.task_mgr = None

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return self.json_parser.parse(self.config_path.read_text())
        return {"team_name": "default", "members": []}
    
    def _save_config(self):
        self.config_path.write_text(self.json_parser.to_json_str(self.config, indent=4))

    def _find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None
    
    def _set_status(self, name: str, status: str):
        member = self._find_member(name)
        if member:
            member["status"] = status
            self._save_config()
    
    def _teammate_loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        sys_prompt = (
            f"You are '{name}', role: {role}, at {self.work_dir}. "
            f"Use idle tool when you have no more work. You will auto-claim new tasks. You need to pass in_progress task."
            f"You can only claim a task every times."
            f"you must finish all the tasks if and only if all the tasks are done, then return <<<-done->>>"
        )
        tools = self._teammate_tools()
        data = self.get_model_contex(tools=tools, query=prompt, prompt=sys_prompt)
        messages = data["messages"]
        for _ in range(50):
            inbox = self.msg_bus.read_inbox(name)
            for msg in inbox:
                if msg.get("type") == "shutdown_request":
                    self._set_status(name, "shutdown")
                    return
                messages.append({"role": "user", "content": self.json_parser.to_json_str(msg)})
            message = self.get_model_result(data)
            if not message:
                self._set_status(name, "idle")
                break
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, is_subagent=False):
                break
            tool_results = []
            idle_requested = False
            for tool_call in message["tool_calls"]:
                arguments = self.json_parser.parse(tool_call["arguments"])
                try:
                    if tool_call["name"] == "idle":
                        idle_requested = True
                        output = "Entering idle phase. Will poll for new tasks."
                    else:
                        output = self._exec(name, tool_call["name"], arguments)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(output)
                    })
                except Exception as ex:
                    output = f"[{name}] excute tool[{tool_call['name']}] error: {str(ex)}"
                print(f"  [{name}] {tool_call['name']}: {str(output)}")
            if len(tool_results) > 0:
                messages.extend(tool_results)
            if idle_requested:
                break
        self._set_status(name, "idle")
        resume = False
        polls = self.idle_timeout // max(self.poll_interval, 1)
        for _ in range(polls):
            time.sleep(self.poll_interval)
            inbox = self.msg_bus.read_inbox(name)
            if len(inbox) > 0:
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": self.json_parser.to_json_str(msg)})
                resume = True
                break
            unclaimed = self.task_mgr.scan_unclaimed_tasks()
            if unclaimed:
                task = unclaimed[0]
                self.task_mgr.claim_task(task["id"], name)
                task_prompt = (
                    f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                    f"{task.get('description', '')}</auto-claimed>"
                )
                if len(messages) <= 3:
                    messages.insert(0, self.make_identity_block(name, role, team_name))
                    messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                messages.append({"role": "user", "content": task_prompt})
                messages.append({"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                resume = True
                break
        if not resume:
            self._set_status(name, "shutdown")
            return
        self._set_status(name, "working")

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
        # these base tools are unchanged from s02
        if tool_name == "bash":
            return self.system_tools.run_bash(args["command"])
        if tool_name == "read_file":
            return self.system_tools.run_read(args["path"])
        if tool_name == "write_file":
            return self.system_tools.run_write(args["path"], args["content"])
        if tool_name == "edit_file":
            return self.system_tools.run_edit(args["path"], args["old_text"], args["new_text"])
        if tool_name == "send_message":
            return self.msg_bus.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return self.json_parser.to_json_str(self.msg_bus.read_inbox(sender), indent=4)
        if tool_name == "shutdown_response":
            req_id = args["request_id"]
            approve = args["approve"]
            with self.tracker_lock:
                if req_id in self.shutdown_requests:
                    self.shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
            self.msg_bus.send(
                sender, "lead", args.get("reason", ""),
                "shutdown_response", {"request_id": req_id, "approve": approve},
            )
            return f"Shutdown {'approved' if approve else 'rejected'}"
        if tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            req_id = str(uuid.uuid4())[:8]
            with self.tracker_lock:
                self.plan_requests[req_id] = {"from": sender, "plan": plan_text, "status": "pending"}
            self.msg_bus.send(
                sender, "lead", plan_text, "plan_approval_response",
                {"request_id": req_id, "plan": plan_text},
            )
            return f"Plan submitted (request_id={req_id}). Waiting for lead approval."
        if tool_name == "claim_task":
            return self.task_mgr.claim_task(args["task_id"], sender)
        if tool_name == "task_list":
            return self.task_mgr.list_all()
        return f"Unknown tool: {tool_name}"
    
    def _teammate_tools(self) -> list:
        # these base tools are unchanged from s02
        return [
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
                            "to": {"type": "string"}, 
                            "content": {"type": "string"}, 
                            "msg_type": {"type": "string", "enum": list(self.msg_bus.get_valid_msg_types())}
                        },
                        "required": ["to", "content"]
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
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "shutdown_response", 
                    "description": "Respond to a shutdown request. Approve to shut down, reject to keep working.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "request_id": {"type": "string"}, 
                            "approve": {"type": "boolean"}, 
                            "reason": {"type": "string"}
                        }, 
                        "required": ["request_id", "approve"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "plan_approval", 
                    "description": "Submit a plan for lead approval. Provide plan text.",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "plan": {"type": "string"}
                        }, 
                        "required": ["plan"]
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
                            "task_id": {"type": "integer"}
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
            }
        ]