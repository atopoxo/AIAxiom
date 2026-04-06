from typing import Any
from core.agent_base.agent_base import AgentBase

class Coder(AgentBase):
    def __init__(self):
        super().__init__()

    def loop(self, role: str, query: str):
        data = self.get_model_contex(tools=self.get_tools(), query=query, prompt=self.get_system_prompt())
        model = self.get_model()
        tool_handlers = self.get_tool_handlers()
        messages = data["messages"]

        while True:
            self.context_compress.compress(messages)
            message, response = self.get_model_result(data)
            if not message:
                continue
            messages.append({
                "role": "assistant", 
                "content": message["conclusion"],
                "tool_calls": message["raw_tool_calls"]
            })
            if self.is_finish(message, model=model, trunk=response):
                break
            manual_compact = False
            tool_results = []
            for tool_call in message["tool_calls"]:
                try:
                    arguments = self.json_parser.parse(tool_call["arguments"])
                    if tool_call["name"] == "compact":
                        manual_compact = True
                        output = "Compressing..."
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
                print(output)
            if len(tool_results) > 0:
                messages.extend(tool_results) 
            if manual_compact:
                print("[manual compact]")
                messages[:] = self.context_compress.auto_compact(messages)