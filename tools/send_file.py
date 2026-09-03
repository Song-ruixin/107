# tools/send_file.py

import os
from tools.tool_manager import tool_manager

SEND_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "send_file_to_user",
        "description": "当用户明确要求获取、下载某个本地文件、文档或图片时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "本地文件的绝对或相对路径",
                },
                "display_name": {
                    "type": "string",
                    "description": "展示给用户的具体文件名",
                }
            },
            "required": ["file_path"],
        },
    },
}

@tool_manager.register(SEND_FILE_TOOL)
def send_file_to_user(file_path: str, display_name: str = "") -> str:
    if not os.path.exists(file_path):
        return f"错误：找不到本地文件 '{file_path}'"
    # 返回带有格式化指令的标记给 AgentBrain
    return f"[SEND_FILE:{file_path}|{display_name}]"