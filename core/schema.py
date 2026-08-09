from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    MIXED = "mixed"


class MessageEnv(str, Enum):
    PRIVATE = "private"
    GROUP = "group"

@dataclass
class UserMessage:
    #基础信息
    platform: str
    message_id: str     #可以暂时不用到
    

    #会话粒度字段
    user_id: str                     # 发送者 ID
    channel_id: str                  # 对应群号 group_id 或 private_id
    user_name: Optional[str] = None  # 用户昵称/群名片（Prompt 生成时很好用，如：Alice: Hello）

    #内容
    content: str = ""
    msg_type: MessageType = MessageType.TEXT
    
    message_env: MessageEnv = MessageEnv.PRIVATE
    is_at_me: bool = False           # 是否在群聊中 @ 了机器人

    #额外
    timestamp: Optional[datetime] = None
    raw_data: Optional[Any] = None