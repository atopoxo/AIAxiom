import threading
import uuid
from pathlib import Path
from tools.msg_bus.msg_bus import MsgBus
from agents.teammate.teammate import Teammate
from core.model.base.model_base import ModelBase
from core.json.json_parser import get_json_parser
from tools.task_mgr.task_mgr import TaskMgr

class TeamMgr:
    def __init__(self, work_dir: Path):
        self.json_parser = get_json_parser()
        self.work_dir = work_dir / ".team"
        self.work_dir.mkdir(exist_ok=True)
        self.config_path = self.work_dir / "config.json"
        self.config = self._load_config()
        self.threads = {}

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
    
    def set_task_mgr(self, mgr: TaskMgr):
        self.task_mgr = mgr

    def get_task_mgr(self):
        return self.task_mgr
    
    def set_msg_bus(self, bus: MsgBus):
        self.msg_bus = bus

    def get_msg_bus(self):
        return self.msg_bus

    def get_model(self) -> ModelBase:
        return self.model
    
    def set_model(self, model: ModelBase):
        self.model = model
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def set_model_name(self, model_name: str):
        self.model_name = model_name
    
    def get_stream(self) -> bool:
        return self.stream
    
    def set_stream(self, stream: bool):
        self.stream = stream
    
    def set_tools(self, tools: list):
        self.tools = tools

    def get_tools(self):
        return self.tools
    
    def set_tool_handlers(self, tool_handlers: dict):
        self.tool_handlers = tool_handlers

    def get_tool_handlers(self) -> dict:
        return self.tool_handlers
    
    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()

        sys_prompt = (
            f"You are '{name}', role: {role}, at {self.work_dir}. "
            f"Use idle tool when you have no more work. You will auto-claim new tasks. You need to pass in_progress task."
            f"You can only claim a task every times."
            f"you must finish all the tasks if and only if all the tasks are done, then return <<<-done->>>"
        )
        teammate = Teammate(member)
        teammate.set_system_prompt(sys_prompt)
        teammate.set_model(self.get_model())
        teammate.set_model_name(self.get_model_name())
        teammate.set_stream(self.get_stream())
        teammate.set_tool_handlers(self.get_tool_handlers())
        teammate.set_tools(self.get_tools())
        teammate.set_msg_bus(self.get_msg_bus())
        teammate.set_task_mgr(self.get_task_mgr())
        thread = threading.Thread(
            target=teammate.loop,
            args=(self.config["team_name"], name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"
    
    def list_all(self) -> str:
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)
    
    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]
    
    def handle_shutdown_request(self, teammate: str) -> str:
        req_id = str(uuid.uuid4())[:8]
        with self.tracker_lock:
            self.shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
        self.msg_bus.send(
            "lead", teammate, "Please shut down gracefully.",
            "shutdown_request", {"request_id": req_id},
        )
        return f"Shutdown request {req_id} sent to '{teammate}' (status: pending)"
    
    def handle_plan_review(self, request_id: str, approve: bool, feedback: str = "") -> str:
        with self.tracker_lock:
            req = self.plan_requests.get(request_id)
        if not req:
            return f"Error: Unknown plan request_id '{request_id}'"
        with self.tracker_lock:
            req["status"] = "approved" if approve else "rejected"
        self.msg_bus.send(
            "lead", req["from"], feedback, "plan_approval_response",
            {"request_id": request_id, "approve": approve, "feedback": feedback},
        )
        return f"Plan {req['status']} for '{req['from']}'"
    
    def check_shutdown_status(self, request_id: str) -> str:
        with self.tracker_lock:
            return self.json_parser.to_json_str(self.shutdown_requests.get(request_id, {"error": "not found"}))