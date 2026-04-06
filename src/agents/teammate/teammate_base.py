import time
from pathlib import Path
import uuid
import threading
from core.agent_base.agent_base import AgentBase

class TeammateBase(AgentBase):
    def __init__(self, config: dict):
        super().__init__()
        self.msg_bus = None
        self.tracker_lock = threading.Lock()
        self.shutdown_requests = {}
        self.plan_requests = {}
        self.idle_timeout = 60
        self.poll_interval = 5
        self.task_mgr = None
        self.config = config
    
    def _set_status(self, status: str):
        self.config["status"] = status

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
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
        elif tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            req_id = str(uuid.uuid4())[:8]
            with self.tracker_lock:
                self.plan_requests[req_id] = {"from": sender, "plan": plan_text, "status": "pending"}
            self.msg_bus.send(
                sender, "lead", plan_text, "plan_approval_response",
                {"request_id": req_id, "plan": plan_text},
            )
            return f"Plan submitted (request_id={req_id}). Waiting for lead approval."
        else:
            return f"Unknown tool: {tool_name}"
        
    def _make_identity_block(self, name: str, role: str, team_name: str) -> dict:
        return {
            "role": "user",
            "content": f"<identity>You are '{name}', role: {role}, team: {team_name}. Continue your work.</identity>",
        }