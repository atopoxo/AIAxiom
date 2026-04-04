from src.core.function.base_function import *
from src.core.log_mgr.log import *

@singleton
class LogMgr(LoggerShell):
    def __init__(self, config, db):
        LoggerShell.__init__(self)
        self.db = db

    # def send(self, info):
    #     func = getattr(self, info["app"] + "_send")
    #     return func(info)

    # def branch_tool_send(self, info):
    #     if self.db:
    #         return self.db.branch_tool_add_log(info["svn_user"], info["type"], info["timestamp"], info["detail"])

def get_logger(config = None, db = None):
    return LogMgr(config, db)

# 日志句柄
log_mgr = get_logger()