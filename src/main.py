import os
from pathlib import Path
from core.model.mgr.model_mgr import ModelMgr
from core.auto_agent.auto_agent import AutoAgent
from tools.tools import TEAM
from core.context_compress.context_compress import ContextCompression

custom_model_config = {
    "url": "https://kspmas.ksyun.com/v1/chat/completions",
    "id": "deepseek-v3.2",
    "platform": "online",
    "code_name": "deepseek",
    "model_name": "deepseek-v3.2",
    "name": "deepseek-v3.2",
    "type": "外网-快速响应",
    "temperature": 1,
    "max_tokens": 8192,
    "api_key": "b97817b4-295c-4b91-ae53-2cf530d8772c",
}

# custom_model_config = {
#     "url": "https://api.deepseek.com",
#     "id": "deepseek-v3.2",
#     "platform": "online",
#     "code_name": "deepseek",
#     "model_name": "deepseek-chat",
#     "name": "deepseek-v3.2",
#     "type": "外网-快速响应",
#     "temperature": 1,
#     "max_tokens": 8192,
#     "api_key": "sk-068888fff48f460ab9f367fb3975c911",
# }

WORKDIR = Path.cwd()

SYSTEM = f"You are a team lead at {WORKDIR}. Spawn teammates and communicate via inboxes."
SYSTEM  += "you must finish all the tasks if and only if all the tasks are done, then return <<<-done->>>"

SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."
SUBAGENT_SYSTEM  += "if all the tasks are done, then return <<<-subagent-done->>>"

if __name__ == "__main__":
    history = []
    stream = True
    model_name = custom_model_config["model_name"]
    model_mgr = ModelMgr()
    model_mgr.add_model_config(custom_model_config)
    model = model_mgr.get_model(custom_model_config["id"])
    context_compress = ContextCompression(WORKDIR, 3)
    context_compress.set_model(model)
    context_compress.set_model_name(model_name)
    context_compress.set_stream(stream)
    context_compress.set_threshold(50000)
    agent = AutoAgent()
    agent.set_model(model)
    agent.set_model_name(model_name)
    agent.set_subagent_prompt(SUBAGENT_SYSTEM)
    agent.set_context_compress(context_compress)
    TEAM.set_model(model)
    TEAM.set_model_name(model_name)
    
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "system", "content": SYSTEM})
        history.append({"role": "user", "content": query})
        data = {
            "messages": history,
            "stream": stream,
            "max_tokens": 8000,
            "index": -1,
            "tool_choice": "auto",
            "extra": {},
        }
        agent.loop(data)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()