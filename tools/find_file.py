# tools/file_find.py
import os
import json
from tools.tool_manager import tool_manager

FIND_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_file",
        "description": "扫描本地文件存储目录，检索匹配的文件名及路径。不能用于发送文件",
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


    result = {
        "status": "success",
        "matched_files": matched_files,
        "total_count": len(matched_files),
    }
    print(f"[find_file] 工具调用完毕，返回 {matched_files} 共 {len(matched_files)}个文件")
    return json.dumps(result, ensure_ascii=False)