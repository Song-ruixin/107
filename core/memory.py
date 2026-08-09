import json
import os
from typing import List, Dict, Any, Optional

class MemoryManager:
    def __init__(self, filepath: str = "data/memory.json", max_history: int = 30) -> None:
        self.filepath = filepath
        self.max_history = max_history

        self.storage: Dict[str, List[Dict[str, Any]]] = {}

        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.load()

    def _save_to_disk(self) ->None:
        #将内存写入目标文件
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.storage, f, ensure_ascii=True, indent=2)

        except Exception as e:
            print(f"[Memory Error] 无法写入内存持久化文件:{e}")

    def load(self) -> None:
        #读取
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.storage = json.load(f)
            print(f"[Memory] 成功加载本地记忆，包含 {len(self.storage)} 个会话。")

        except Exception as e:
            print(f"[Memory Error] 读取内存持久化文件失败: {e}")
            self.storage = {}

    def get_history(self, channel_id: str) -> List[Dict[str, Any]]:
        """获取指定会话的历史记录副本"""
        return self.storage.get(channel_id, []).copy()

    def add_message(self, channel_id: str, role: str, content: str) -> None:
        """追加单条消息并触发滑动窗口截断与持久化"""
        if channel_id not in self.storage:
            self.storage[channel_id] = []

        self.storage[channel_id].append({"role": role, "content": content})
 
        # 滑动窗口截断：保持历史记录在 max_history 范围内
        if len(self.storage[channel_id]) > self.max_history * 2:
            # 乘以 2 是因为一问一答包含 user 和 assistant 2 条记录
            self.storage[channel_id] = self.storage[channel_id][-(self.max_history * 2):]

        '''
        [-k:] 切片语法， 相当于取列表的倒数第k项往后的部分
        
        切片（slicing）：
            用于从序列类型提取子元素，语法：
            sequence[start:stop:step]
                索引值： 正序0， 逆序-1    
            省略了索引值就默认为开头或者结尾
            a = [1, 2, 3, 4, 5]

            # 批量替换
            a[1:4] = [20, 30]      # a 变成 [1, 20, 30, 5]

            # 清空列表
            a[:] = []              # a 变成 []

            # 局部插入
            a = [1, 5]
            a[1:1] = [2, 3, 4]     # a 变成 [1, 2, 3, 4, 5]
        '''

        # 写入本地文件
        self._save_to_disk()

    def clear(self, session_id: str) -> None:
        """清空某个会话的记忆（比如用户发送“重置”或“忘掉之前的话”时使用）"""
        if session_id in self.storage:
            del self.storage[session_id]
            self._save_to_disk()

    