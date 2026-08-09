import asyncio
from datetime import datetime
from typing import Callable, Coroutine, Any, Optional

from platforms.qq.client import QQWebSocketClient
# 请根据你存放 UserMessage 的实际路径调整 import
from core.schema import UserMessage, MessageType, MessageEnv


class qqAdapter:
    def __init__(self, client: QQWebSocketClient) -> None:
        self.client = client
        self.user_message_handler: Optional[Callable[[UserMessage], Coroutine[Any, Any, None]]] = None

        # 将 Adapter 自身的接收函数注册给 Client
        self.client.set_on_message(self._on_raw_message)

    def set_user_message_handler(
        self, handler: Callable[[UserMessage], Coroutine[Any, Any, None]]
    ) -> None:
        self.user_message_handler = handler

    # ------------------------------------------------------------------
    # 1. 消息接收与解析（Raw Dict -> Standard UserMessage）
    # ------------------------------------------------------------------
    async def _on_raw_message(self, raw_data: dict) -> None:
        # 过滤非用户消息（如心跳包 meta_event、通知 notice 等）
        post_type = raw_data.get("post_type")
        if post_type != "message":
            return

        # 提取消息环境 (PRIVATE / GROUP)
        raw_env = raw_data.get("message_type")
        message_env = MessageEnv.GROUP if raw_env == "group" else MessageEnv.PRIVATE

        user_id = str(raw_data.get("user_id", ""))
        message_id = str(raw_data.get("message_id", ""))
        self_id = str(raw_data.get("self_id", ""))

        # 确定 channel_id
        if message_env == MessageEnv.GROUP:
            channel_id = str(raw_data.get("group_id", ""))
        else:
            channel_id = user_id

        # 提取用户昵称
        sender = raw_data.get("sender", {})
        user_name = sender.get("card") or sender.get("nickname") or "未知用户"

        # 提取纯文本 content 与检测 is_at_me
        message_content = raw_data.get("message")
        extracted_text = ""
        is_at_me = False

        if isinstance(message_content, list):
            for seg in message_content:
                seg_type = seg.get("type")
                seg_data = seg.get("data", {})

                if seg_type == "at":
                    target_qq = str(seg_data.get("qq", ""))
                    if target_qq == self_id:
                        is_at_me = True
                elif seg_type == "text":
                    extracted_text += seg_data.get("text", "")
        elif isinstance(message_content, str):
            extracted_text = message_content

        if not extracted_text:
            extracted_text = raw_data.get("raw_message", "")

        # 时间戳转换
        time_sec = raw_data.get("time")
        msg_time = datetime.fromtimestamp(time_sec) if time_sec else datetime.now()

        # 构造符合定义的 UserMessage 实例
        user_msg = UserMessage(
            platform="qq",
            message_id=message_id,
            user_id=user_id,
            channel_id=channel_id,
            user_name=user_name,
            content=extracted_text.strip(),
            msg_type=MessageType.TEXT,
            message_env=message_env,
            is_at_me=is_at_me,
            timestamp=msg_time,
            raw_data=raw_data
        )

        print(f"[QQ Adapter] 收到 {message_env.value} 消息 | AtMe={is_at_me} | {user_name}({user_id}): {user_msg.content}")

        # 抛给上层 Agent
        if self.user_message_handler:
            asyncio.create_task(self.user_message_handler(user_msg))

    # ------------------------------------------------------------------
    # 2. 消息发送 API（上层 Agent 调用的统一回复接口）
    # ------------------------------------------------------------------
    async def send_message(
        self,
        channel_id: str,
        message_env: MessageEnv,
        content: str,
        at_user_id: Optional[str] = None
    ) -> bool:
        """
        统一消息发送函数
        :param channel_id: 群号 或 私聊用户QQ号
        :param message_env: MessageEnv.GROUP 或 MessageEnv.PRIVATE
        :param content: 要发送的文本内容
        :param at_user_id: 可选，在群聊中需要 @ 的用户 QQ 号
        """
        if message_env == MessageEnv.GROUP:
            # 构造 OneBot V11 发送群消息 API 数据包
            # 如果指定了 at_user_id，在消息前面加上 @ 节点
            message_payload = []
            if at_user_id:
                message_payload.append({"type": "at", "data": {"qq": at_user_id}})
                message_payload.append({"type": "text", "data": {"text": f" {content}"}})
            else:
                message_payload = content

            payload = {
                "action": "send_group_msg",
                "params": {
                    "group_id": int(channel_id),
                    "message": message_payload
                }
            }
        else:
            # 构造 OneBot V11 发送私聊消息 API 数据包
            payload = {
                "action": "send_private_msg",
                "params": {
                    "user_id": int(channel_id),
                    "message": content
                }
            }

        return await self.client.send_raw(payload)