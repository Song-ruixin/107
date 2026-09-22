from dataclasses import dataclass, field
from typing import Optional, Any, List
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
class Attachment:
    """单个附件信息"""
    type: MessageType                # IMAGE, FILE, VOICE 等
    url_or_path: str                 # 远程 URL 或本地路径
    file_name: Optional[str] = None  # 文件名（如果是文件）
    file_size: Optional[int] = None  # 文件大小（字节）

@dataclass
class UserMessage:
    #基础信息
    platform: str
    message_id: str                  # 可以暂时不用到
    user_id: str                     # 发送者 ID
    channel_id: str                  # 对应群号 group_id 或 private_id
    
    #可选字段
    user_name: Optional[str] = None  # 用户昵称/群名片（Prompt 生成时很好用，如：Alice: Hello）
    message_env: MessageEnv = MessageEnv.PRIVATE
    content: str = ""
    is_at_me: bool = False           # 是否在群聊中 @ 了机器人

    #附件
    attachments: List[Attachment] = field(default_factory=list)

    #额外
    timestamp: Optional[datetime] = None
    raw_data: Optional[Any] = None

