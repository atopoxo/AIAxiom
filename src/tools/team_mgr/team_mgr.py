import threading
import uuid
from pathlib import Path
from tools.team_mgr.team_mgr_base import TeamMgrBase
from tools.msg_bus.msg_bus import MsgBus
from tools.system_tools.system_tools import SystemTools

class TeamMgr(TeamMgrBase):
    def __init__(self, work_dir: Path):
        super().__init__(work_dir)

    def set_msg_bus(self, bus: MsgBus):
        self.msg_bus = bus

    def set_system_tools(self, tools: SystemTools):
        self.system_tools = tools
    
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
        thread = threading.Thread(
            target=self._teammate_loop,
            args=(name, role, prompt),
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
