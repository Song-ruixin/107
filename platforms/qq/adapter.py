import asyncio
from datetime import datetime
from typing import Callable, Coroutine, Any, Optional, List

from config.settings import settings
from platforms.qq.client import QQWebSocketClient
from platforms.qq.cache import message_cache
from core.schema import UserMessage, MessageType, MessageEnv, Attachment


class qqAdapter:
    def __init__(self, client: QQWebSocketClient) -> None:
        self.client = client
        self.user_message_handler: Optional[Callable[[UserMessage], Coroutine[Any, Any, None]]] = None
        self.client.set_on_message(self._on_raw_message) # 将 Adapter 自身的接收函数注册给 Client

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

        raw_env = raw_data.get("message_type")      # 提取消息环境 (PRIVATE / GROUP)
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

        # 提取文本 content, 接收attachment 与检测 is_at_me
        message_content = raw_data.get("message")
        extracted_text = ""
        is_at_me = False
        attachments: List[Attachment] = []
        quoted_msg_id: Optional[str] = None

        if isinstance(message_content, list):
            for seg in message_content:
                seg_type = seg.get("type")
                seg_data = seg.get("data", {})


                if seg_type == "reply":
                    quoted_msg_id = str(seg_data.get("id", ""))

                elif seg_type == "at":
                    target_qq = str(seg_data.get("qq", ""))
                    if target_qq == self_id:
                        is_at_me = True

                elif seg_type == "text":
                    extracted_text += seg_data.get("text", "")

                elif seg_type == "image":
                    # 图片 Segment：优先读取网络 url，若无则使用 file 字段
                    img_url = seg_data.get("url") or seg_data.get("file", "")
                    file_name = seg_data.get("file") or "image.jpg"
                    
                    if img_url:
                        attachments.append(Attachment(
                            type=MessageType.IMAGE,
                            url_or_path=img_url,
                            file_name=file_name
                        ))
                    extracted_text += "[图片]"

                elif seg_type == "file":
                    # 文件 Segment：读取下载 url、文件名与文件大小
                    file_url = seg_data.get("url") or seg_data.get("file", "")
                    file_name = seg_data.get("name") or "file"
                    file_size = int(seg_data.get("size", 0)) if seg_data.get("size") else None

                    if file_url:
                        attachments.append(Attachment(
                            type=MessageType.FILE,
                            url_or_path=file_url,
                            file_name=file_name,
                            file_size=file_size
                        ))
                    extracted_text += f"[文件: {file_name}]"

        
        elif isinstance(message_content, str):
            extracted_text = message_content

        if not extracted_text:
            extracted_text = raw_data.get("raw_message", "")

        current_clean_text = extracted_text.strip()
        final_prompt_content = current_clean_text

        if quoted_msg_id:
            quoted_msg = message_cache.get(quoted_msg_id)
            if quoted_msg:
                # 构造引用文本前缀
                reply_prefix = f"[引用回复了 {quoted_msg.user_name} 的消息: \"{quoted_msg.content}\"]\n"
                
                # 拼接引用文本
                final_prompt_content = reply_prefix + current_clean_text
                
                # 如果引用的消息里有附件，也合并进来
                if quoted_msg.attachments:
                    attachments.extend(quoted_msg.attachments)

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
            content=final_prompt_content,

            attachments=attachments,
            message_env=message_env,
            is_at_me=is_at_me,
            timestamp=msg_time,
            raw_data=raw_data
        )
        
        message_cache.add(user_msg)

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


    async def send_file(
        self,
        channel_id: str,
        message_env: MessageEnv,
        file_path: str,
        file_name: Optional[str] = None
    ) -> bool:
        """调用 NapCat 的 upload_group_file / upload_private_file 发送本地文件"""
        import os

        # 定义宿主机挂载目录与容器内目录的对应关系
        HOST_BASE_DIR = settings.HOST_BASE_DIR                      # 宿主机映射根目录
        CONTAINER_BASE_DIR =  settings.CONTAINER_BASE_DIR           # 容器内对应的根目录

        # 1. 校验宿主机上的原始文件是否存在
        abs_host_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(abs_host_path):
            print(f"[QQ Adapter Error] 本地文件不存在: {abs_host_path}")
            return False

        # 2. 将宿主机绝对路径转换为容器内的绝对路径
        abs_host_base = os.path.abspath(HOST_BASE_DIR)
        
        # 检查文件是否确实处于挂载目录下
        if abs_host_path.startswith(abs_host_base):
            # 提取相对路径并拼接容器路径
            rel_path = os.path.relpath(abs_host_path, abs_host_base)
            container_file_path = os.path.join(CONTAINER_BASE_DIR, rel_path)
        else:
            print(f"[QQ Adapter Warning] 文件 {abs_host_path} 未在挂载目录 {abs_host_base} 下，NapCat 可能无法读取")
            container_file_path = abs_host_path  # 备用方案，尝试直接传参

        final_file_name = file_name or os.path.basename(abs_host_path)

        # 3. 构造发送 Payload（传入转换后的 container_file_path）
        if message_env == MessageEnv.GROUP:
            payload = {
                "action": "upload_group_file",
                "params": {
                    "group_id": int(channel_id),
                    "file": container_file_path,
                    "name": final_file_name
                }
            }
        else:
            payload = {
                "action": "upload_private_file",
                "params": {
                    "user_id": int(channel_id),
                    "file": container_file_path,
                    "name": final_file_name,
                    "filename": final_file_name
                }
            }

        print(f"[QQ Adapter] 请求 NapCat 发送文件: 宿主机={abs_host_path} -> 容器={container_file_path}")
        return await self.client.send_raw(payload)