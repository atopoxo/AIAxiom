import time
from tools.task_mgr.task_mgr import TaskMgr
from agents.teammate.teammate_base import TeammateBase
from tools.msg_bus.msg_bus import MsgBus

class Teammate(TeammateBase):
    def __init__(self, config: dict):
        super().__init__(config)
    
    def set_task_mgr(self, mgr: TaskMgr):
        self.task_mgr = mgr

    def get_task_mgr(self):
        return self.task_mgr
    
    def set_msg_bus(self, bus: MsgBus):
        self.msg_bus = bus

    def get_msg_bus(self):
        return self.msg_bus

    def loop(self, team_name: str, name: str, role: str, query: str):
        data = self.get_model_contex(tools=self.get_tools(), query=query, prompt=self.get_system_prompt())
        model = self.get_model()
        tool_handlers = self.get_tool_handlers()
        messages = data["messages"]
        task_mgr = self.get_task_mgr()
        while True:
            inbox = self.msg_bus.read_inbox(name)
            for msg in inbox:
                if msg.get("type") == "shutdown_request":
                    self._set_status("shutdown")
                    return
                messages.append({"role": "user", "content": self.json_parser.to_json_str(msg)})
            message, response = self.get_model_result(data)
            if not message:
                self._set_status("idle")
                break
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, model=model, trunk=response):
                break
            idle_requested = False
            manual_compact = False
            tool_results = []
            for tool_call in message["tool_calls"]:
                try:
                    arguments = self.json_parser.parse(tool_call["arguments"])
                    if tool_call["name"] == "compact":
                        manual_compact = True
                        output = "Compressing..."
                    elif tool_call["name"] == "idle":
                        idle_requested = True
                        output = "Entering idle phase. Will poll for new tasks."
                    elif tool_call["name"] in ["shutdown_response", "plan_approval"]:
                        output = self._exec(name, tool_call["name"], arguments)
                    else:
                        handler = tool_handlers.get(tool_call["name"])
                        output = handler(**arguments) if handler else f"Unknown tool: {tool_call['name']}"
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": output
                    })
                except Exception as ex:
                    output = f"[agent] excute tool[{tool_call['name']}] error: {str(ex)}"
                print(f"  [{name}] {tool_call['name']}: {str(output)}")
            if len(tool_results) > 0:
                messages.extend(tool_results) 
            if manual_compact:
                print("[manual compact]")
                messages[:] = self.context_compress.auto_compact(messages)
            if idle_requested:
                break

        self._set_status("idle")
        resume = False
        polls = self.idle_timeout // max(self.poll_interval, 1)
        for _ in range(polls):
            time.sleep(self.poll_interval)
            inbox = self.msg_bus.read_inbox(name)
            if len(inbox) > 0:
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status("shutdown")
                        return
                    messages.append({"role": "user", "content": self.json_parser.to_json_str(msg)})
                resume = True
                break
            unclaimed = task_mgr.scan_unclaimed_tasks()
            if unclaimed:
                task = unclaimed[0]
                task_mgr.claim_task(task["id"], name)
                task_prompt = (
                    f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                    f"{task.get('description', '')}</auto-claimed>"
                )
                if len(messages) <= 3:
                    messages.insert(0, self._make_identity_block(name, role, team_name))
                    messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                messages.append({"role": "user", "content": task_prompt})
                messages.append({"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                resume = True
                break
        if not resume:
            self._set_status("shutdown")
            return
        self._set_status("working")