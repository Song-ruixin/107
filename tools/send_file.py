import os
import json
import asyncio
from typing import Optional, List, Dict  # 确保导入了 Optional
from core.schema import MessageEnv

from tools.tool_manager import tool_manager

SEND_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_file",
        "description": "通过 QQ 将本地文件直接发送给当前对话的用户或群聊。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要发送的本地文件绝对路径列表"
                },
                "file_path": {
                    "type": "string",
                    "description": "单个文件的绝对路径（兼容参数）"
                },
                "path": {
                    "type": "string",
                    "description": "单个文件的绝对路径（兼容参数）"
                }
            }
        }
    }
}

@tool_manager.register(SEND_FILE_SCHEMA)
async def execute_send_file(
    file_paths: Optional[List[str]] = None,  # <--- 这里加上 Optional
    file_path: Optional[str] = None,          # 顺便把其他的也规范一下
    path: Optional[str] = None,
    adapter=None,
    channel_id: str = "",
    message_env: MessageEnv = MessageEnv.PRIVATE
) -> str:
    # 兼容大模型可能传错参数名的情况（把单数字段统一转成列表）
    resolved_paths = []
    if file_paths:
        resolved_paths.extend(file_paths)
    if file_path:
        resolved_paths.append(file_path)
    if path:
        resolved_paths.append(path)

    # 去重防重复发送
    resolved_paths = list(set(resolved_paths))

    if not resolved_paths:
        return json.dumps({"status": "failed", "reason": "未提供有效的文件路径参数"})

    if not adapter:
        return json.dumps({"status": "failed", "reason": "系统未配置发送适配器"})
        
    results = {"success_count": 0, "failed_count": 0, "details": []}

    for p in resolved_paths:
        if not os.path.exists(p):
            results["failed_count"] += 1
            results["details"].append({"path": p, "status": "failed", "reason": "文件不存在"})
            continue

        success = await adapter.send_file(
            channel_id=channel_id,
            message_env=message_env,
            file_path=os.path.abspath(p),
            file_name=os.path.basename(p)
        )

        if success:
            results["success_count"] += 1
            results["details"].append({"path": p, "status": "success"})
        else:
            results["failed_count"] += 1
            results["details"].append({"path": p, "status": "failed", "reason": "QQ发送失败"})

        await asyncio.sleep(1)

    return json.dumps(results, ensure_ascii=False)