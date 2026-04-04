import threading
from pathlib import Path
from tools.team_mgr.team_mgr_base import TeamMgrBase
from tools.message_bus.msg_bus import MsgBus
from tools.system_tools.system_tools import SystemTools

class TeamMgr(TeamMgrBase):
    def __init__(self, work_dir: Path):
        super().__init__(work_dir)

    def set_message_bus(self, bus: MsgBus):
        self.message_bus = bus

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