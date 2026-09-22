import asyncio
from config.settings import settings
from platforms.qq.client import QQWebSocketClient
from platforms.qq.adapter import qqAdapter
from core.schema import UserMessage, MessageEnv
from core.core import AgentBrain

# 1. 在全局单例实例化 AgentBrain（只加载一次工具与记忆，保持长连接）
brain = AgentBrain()


async def handle_user_message(msg: UserMessage, adapter: qqAdapter) -> None:
    print(f"\n[Agent Info] 平台: {msg.platform} | 环境: {msg.message_env.value}")
    print(f"发送者: {msg.user_name} ({msg.user_id}) | 会话: {msg.channel_id}")
    print(f"内容: '{msg.content}' | 是否@机器人: {msg.is_at_me}")

    # 交给 AgentBrain 处理（内部已有群聊未 @ 过滤逻辑）
    reply_text = await brain.process_message(msg)

    if reply_text:
        # 如果是群聊，回复时 @ 发送者
        at_target = msg.user_id if msg.message_env == MessageEnv.GROUP else None

        # 调用 Adapter 发送回复
        await adapter.send_message(
            channel_id=msg.channel_id,
            message_env=msg.message_env,
            content=reply_text,
            at_user_id=at_target,
        )


async def main():
    # 2. 实例化 WebSocket 服务端 Client (从配置读取并强转端口为 int)
    client = QQWebSocketClient(
        host=settings.QQ_WS_HOST, 
        port=int(settings.QQ_WS_PORT)
    )

    # 3. 实例化 Adapter 适配器
    qqadapter = qqAdapter(client)

    # 关键：把 qqadapter 传给全局单例的 brain
    brain.adapter = qqadapter

    # 4. 挂载消息处理回调
    qqadapter.set_user_message_handler(
        lambda msg: handle_user_message(msg, qqadapter)
    )

    # 5. 启动客户端服务
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系统] 服务已安全关闭。")