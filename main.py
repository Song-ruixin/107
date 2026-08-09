import asyncio
from platforms.qq.client import QQWebSocketClient
from platforms.qq.adapter import qqAdapter
from core.schema import UserMessage, MessageEnv, MessageType

from core.core import AgentBrain


async def handle_user_message(msg: UserMessage, adapter: qqAdapter) -> None:
    """
    模拟一个简单的 Echo Agent（复读机/自动回复测试）
    """
    print(f"[Agent info] \n平台: {msg.platform} | 环境 : {msg.message_env.value}")
    print(f"发送者: {msg.user_name} ({msg.user_id}) | 会话: {msg.channel_id}")
    print(f"内容: '{msg.content}' | 是否@机器人: {msg.is_at_me}")


    Agent = AgentBrain()

    # 如果是群聊且没有 @ 机器人，可以在这里跳过（测试时也可以把这个判断注释掉）
    if msg.message_env == MessageEnv.GROUP and not msg.is_at_me:
        print("[Agent] 群聊中未 @ 机器人，静默忽略。")
        return

    reply_text = await Agent.process_message(msg)
    if (reply_text):
 
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
    # 1. 实例化 WebSocket 服务端 Client (端口保持与 NapCat 配置一致，如 8080)
    # 如果在 NapCat 设了 Token，这里加上 token="你的Token"
    client = QQWebSocketClient(host="0.0.0.0", port=8080)

    # 2. 实例化 Adapter 适配器
    qqadapter = qqAdapter(client)

    # 3. 将 Agent 的消息处理函数挂载到 Adapter 上
    # 使用 lambda 闭包把 adapter 实例一起传进去
    qqadapter.set_user_message_handler(
        lambda msg: handle_user_message(msg, qqadapter)
    )
    '''
    lambda 用于写小函数：
    
    def add(x, y):
        return x + y

    等价于：
    add = lambda x, y: x+y
    '''
    # 4. 启动客户端服务
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系统] 服务已安全关闭。")