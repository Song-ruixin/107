import asyncio
import json
import websockets
from websockets.asyncio.server import ServerConnection  # 新版 websockets 推荐的正确类型
from typing import Callable, Awaitable, Optional, Coroutine, Any

class QQWebSocketClient:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.active_websocket :Optional[ServerConnection] = None
        self.on_message_callback: Optional[Callable[[dict], Coroutine[Any, Any, None]]] = None 
        # 回调函数，用于消息处理，本体位于adapter
        # Callable[[输入参数类型1,输入参数类型2],返回值类型]
    
    def set_on_message(self, callback: Callable[[dict], Coroutine[Any, Any, None]]) -> None:
        self.on_message_callback = callback

    async def start(self) -> None:
        print(f"正在启动 QQ Websockert服务， 监听http：//{self.host}: {self.port}...")
        async with websockets.serve(self._handle_connection, self.host , self.port):
            await asyncio.Future()



    async def _handle_connection(self, websocket: ServerConnection):
        self.active_websocket = websocket
        print("[QQ Client] NapCat 已成功连接至本服务端！")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    print(f"[QQ Client] 收到非 JSON 格式的消息: {message}")
                    continue

                if self.on_message_callback:
                    asyncio.create_task(self.on_message_callback(data))

        except websockets.ConnectionClosed:
            print("[QQ Client] NapCat 断开了连接。")
        finally:
            self.active_websocket = None

    async def send_raw(self, payload: dict) -> bool:
        if not self.active_websocket:
            print("[QQ Client] 发送消息失败：NapCat 尚未建立连接！")
            return False

        try:
            message = json.dumps(payload, ensure_ascii=False)
            await self.active_websocket.send(message)
            return True
        except websockets.ConnectionClosed:
            print("[QQ Client] 发送消息失败：网络连接已断开。")
            self.active_websocket = None
            return False
        except Exception as e:
            print(f"[QQ Client] 发送消息发生未知异常: {e}")
            return False
            