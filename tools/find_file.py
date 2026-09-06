# tools/file_find.py
import os
import json
from tools.tool_manager import tool_manager

FIND_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_file",
        "description": "扫描本地文件存储目录，检索匹配的文件名及路径。当需要查找文件、确定文件是否存在、或准备发送文件给用户前获取文件路径时调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户查询的关键词或文件主题（如：迎新推文、电磁学）"
                }
            },
            "required": ["query"]
        }
    }
}

SEARCH_DIR = "./files"

@tool_manager.register(FIND_FILE_SCHEMA)
async def find_file(query: str) -> str:
    if not os.path.isdir(SEARCH_DIR):
        result = {
            "status": "error",
            "matched_files": [],
            "total_count": 0,
            "message": "错误：本地文件目录 ./files 不存在。"
        }
        return json.dumps(result, ensure_ascii=False)

    keywords = [kw.lower() for kw in query.split() if kw.strip()]
    matched_files = []

    for root, _, filenames in os.walk(SEARCH_DIR):
        for fname in filenames:
            full_path = os.path.abspath(os.path.join(root, fname))
            
            # 如果无关键词则全量列出；有关键词则匹配文件名或父级路径
            if not keywords or any(kw in fname.lower() or kw in full_path.lower() for kw in keywords):
                matched_files.append({
                    "filename": fname,
                    "path": full_path  # 直接返回绝对路径，方便 send_file 无缝读取
                })

    # 未找到匹配文件时的处理
    if not matched_files:
        result = {
            "status": "success",
            "matched_files": [],
            "total_count": 0,
            "message": f"未能找到与 '{query}' 相关的本地文件。请直接如实回复用户未找到相关文件。"
        }
        return json.dumps(result, ensure_ascii=False)

    # 关键：给大模型的 Behavior Prompt / Instruction
    instruction = (
        f"已成功检索到 {len(matched_files)} 个相关文件。\n"
        "【下一步行动指南】\n"
        "1. 如果用户仅询问有哪些文件（如“有哪些资料”、“帮我找找迎新文件”），请直接在回复文本中列出匹配的文件名；\n"
        "2. 如果用户明确表达了获取/发送意图（如“把迎新推文发给我”、“收徐克尊近代物理学”、“传一下海报”），"
        "你必须立即在下一个 Action 中调用 `send_file` 工具，参数 `file_paths` 传入匹配文件的 `path` 字符串列表！绝对不要在回答中只打字而不调工具。"
    )

    result = {
        "status": "success",
        "matched_files": matched_files,
        "total_count": len(matched_files),
        "instruction": instruction  # 用明确的字段传递操作指南
    }
    return json.dumps(result, ensure_ascii=False)