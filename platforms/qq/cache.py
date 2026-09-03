# platforms/qq/cache.py

from collections import OrderedDict
from typing import Optional
from core.schema import UserMessage


class MessageCache:
    """按 Message ID 缓存最近的消息记录，防止无限增长设置 maxsize"""

    def __init__(self, maxsize: int = 500):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, UserMessage] = OrderedDict()

    def add(self, msg: UserMessage) -> None:
        if not msg.message_id:
            return
        # 如果超出最大容量，移除最早入队的消息
        if len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)
        self._cache[msg.message_id] = msg

    def get(self, message_id: str) -> Optional[UserMessage]:
        return self._cache.get(str(message_id))


# 全局消息缓存单例
message_cache = MessageCache(maxsize=500)