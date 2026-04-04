from pathlib import Path
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
        self.message_bus = None
        self.system_tools = None

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
    
    def _teammate_loop(self, name: str, role: str, prompt: str):
        sys_prompt = (
            f"You are '{name}', role: {role}, at {self.work_dir}. "
            f"Use send_message to communicate. Complete your task."
            f"you must finish all the tasks if and only if all the tasks are done, then return <<<-done->>>"
        )
        tools = self._teammate_tools()
        data = self.get_model_contex(tools=tools, query=prompt, prompt=sys_prompt)
        messages = data["messages"]
        for _ in range(50):
            inbox = self.message_bus.read_inbox(name)
            for msg in inbox:
                messages.append({"role": "user", "content": self.json_parser.to_json_str(msg)})
            message = self.get_model_result(data)
            if not message:
                continue
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, is_subagent=False):
                break
            tool_results = []
            for tool_call in message["tool_calls"]:
                arguments = self.json_parser.parse(tool_call["arguments"])
                output = self._exec(name, tool_call["name"], arguments)
                print(output)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(output)
                })
            messages.extend(tool_results)
        member = self._find_member(name)
        if member and member["status"] != "shutdown":
            member["status"] = "idle"
            self._save_config()

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
            return self.message_bus.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return self.json_parser.to_json_str(self.message_bus.read_inbox(sender), indent=4)
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
                            "msg_type": {"type": "string", "enum": list(self.message_bus.get_valid_msg_types())}
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
        ]