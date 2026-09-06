import os
import json
import asyncio
from typing import List
from core.schema import MessageEnv

from tools.tool_manager import tool_manager

SEND_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_file",
        "description": "通过 QQ 将本地文件直接发送给当前对话的用户或群聊。当用户要求发送、传送或下载文件时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要发送的本地文件绝对路径列表"
                }
            },
            "required": ["file_paths"]
        }
    }
}

@tool_manager.register(SEND_FILE_SCHEMA)
async def execute_send_file(
    file_paths: List[str],
    adapter=None,                                   # 隐式参数：由 Brain 注入
    channel_id: str = "",                           # 隐式参数：由 Brain 注入
    message_env: MessageEnv = MessageEnv.PRIVATE    # 隐式参数：由 Brain 注入
) -> str:
    if not adapter:
        print("[send_file] 系统未配置发送适配器")
        return json.dumps({"status": "failed", "reason": "系统未配置发送适配器"})
        
    results = {"success_count": 0, "failed_count": 0, "details": []}

    for path in file_paths:
        if not os.path.exists(path):
            results["failed_count"] += 1
            print(f"[send_file] 文件不存在(path: {path})")
            results["details"].append({"path": path, "status": "failed", "reason": "文件不存在"})
            continue

        print(f"[send_file] 准备发送文件(path: {path})")
        # 核心逻辑：直接拉起 qqAdapter 现成的 send_file！
        success = await adapter.send_file(
            channel_id=channel_id,
            message_env=message_env,
            file_path=os.path.abspath(path),
            file_name=os.path.basename(path)
        )

        if success:
            print(f"[send_file] 发送成功(path: {path})")
            results["success_count"] += 1
            results["details"].append({"path": path, "status": "success"})
        else:
            print(f"[send_file] QQ 消息发送失败(path: {path})")
            results["failed_count"] += 1
            results["details"].append({"path": path, "status": "failed", "reason": "QQ发送失败"})

        # 防风控延迟
        await asyncio.sleep(1)

    return json.dumps(results, ensure_ascii=False)