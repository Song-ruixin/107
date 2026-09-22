# tools/clear_memory.py
import json
from tools.tool_manager import tool_manager

CLEAR_MEMORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "clear_memory",
        "description": "清空当前会话的历史记忆上下文。当用户用自然语言表达“忘了刚才说的”、“重新开始”、“清空聊天记录”、“别记着刚才的内容”等意图时调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

@tool_manager.register(CLEAR_MEMORY_SCHEMA)
async def clear_memory(channel_id: str, memory) -> str:
    """
    通过 AgentBrain 注入的 channel_id 和 memory 对象直接清空上下文
    """
    try:
        # 清空 MemoryManager 中对应的会话历史
        if hasattr(memory, "clear_session"):
            memory.clear_session(channel_id)
        elif hasattr(memory, "history") and channel_id in memory.history:
            memory.history[channel_id] = []
            
        return json.dumps({
            "status": "success",
            "message": "记忆已成功清空。请直接友好地回复用户，告诉他记忆已经重置，随时可以开始新话题。"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"清空记忆失败: {str(e)}"
        }, ensure_ascii=False)