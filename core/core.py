import json
from typing import Optional, List, Dict
from openai import AsyncOpenAI

from core.schema import UserMessage, MessageEnv
from config.settings import settings
from config.prompt_templates import SYSTEM_PROMPT
from core.memory import MemoryManager

# TOOLS 定义以及 TOOL_MAP 函数映射字典
from tools.tool_manager import tool_manager


class AgentBrain:
    def __init__(self) -> None:
        #导入所有工具
        tool_manager.auto_load_tools()

        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.LLM_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT
        self.memory = MemoryManager()
        self.memory.load()

    async def process_message(self, msg: UserMessage) -> Optional[str]:

        # 过滤策略：如果是群聊且没有 @ 机器人，直接忽略，不浪费 API token
        if msg.message_env == MessageEnv.GROUP and not msg.is_at_me:
            return None

        history = self.memory.get_history(msg.channel_id)
        display_name = msg.user_name or "用户"
        message_to_send = f"{display_name}({msg.user_id}): {msg.content}"

        # 构造发送给 DeepSeek 的消息列表 (Messages Array)
        messages: List[Dict] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message_to_send})

        print(f"[Brain] 准备请求 DeepSeek ({self.model}) | 来自用户 {msg.user_name}: {msg.content}")
        print(f"已装载工具: {list(tool_manager.TOOL_MAP.keys())}")
        
        try:
            # 1. 第一次请求 DeepSeek API (带上工具配置)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,    # type: ignore
                stream=False,
                reasoning_effort="high",
                tools=tool_manager.TOOLS,            # type: ignore
                tool_choice="auto",
                extra_body={"thinking": {"type": "enabled"}},
                temperature=0.7,
            )

            agent_raw = response.choices[0].message

            # 2. 判断 DeepSeek 是否要求调用工具 (Tool Calls)
            if agent_raw.tool_calls:
                print(f"[Brain] DeepSeek 决定调用工具: {[tc.function.name for tc in agent_raw.tool_calls]}")

                # 先把 AI 发出的 tool_calls 消息追加到当前上下文消息队列中
                messages.append(agent_raw)  # type: ignore

                # 遍历处理所有的工具调用需求
                for tool_call in agent_raw.tool_calls:
                    func_name = tool_call.function.name
                    # 解析 AI 提取的参数 JSON 字符串 -> Python 字典
                    try:
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}

                    print(f"[Brain] 正在执行本地工具: {func_name} | 参数: {func_args}")

                    # 寻找并执行对应的 Python 函数
                    if func_name in tool_manager.TOOL_MAP:
                        target_func = tool_manager.TOOL_MAP[func_name]
                        try:
                            # 判断函数是否为异步函数，做兼容调用
                            import inspect
                            if inspect.iscoroutinefunction(target_func):
                                tool_result = await target_func(**func_args)
                            else:
                                tool_result = target_func(**func_args)
                        except Exception as exec_e:
                            tool_result = f"工具执行出错: {str(exec_e)}"
                    else:
                        tool_result = f"未找到名为 {func_name} 的本地工具函数。"

                    # 将工具执行结果包装成 role="tool" 追加到上下文队列
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })

                # 3. 第二次请求 DeepSeek：让 AI 结合工具返回结果，生成最终回复
                second_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore
                    stream=False,
                    temperature=0.7,
                )

                final_reply = second_response.choices[0].message.content
                if final_reply:
                    cleaned_reply = final_reply.strip()
                    print(f"[Brain] DeepSeek 结合工具结果思考完毕，最终回复: {cleaned_reply}")

                    # 只保存对话的最终成对结果到 memory（防止中间工具日志污染记忆）
                    self.memory.add_message(msg.channel_id, "user", message_to_send)
                    self.memory.add_message(msg.channel_id, "assistant", cleaned_reply)

                    return cleaned_reply

            # 4. 如果没有调用工具，直接提取回复文本
            elif agent_raw.content:
                cleaned_reply = agent_raw.content.strip()
                print(f"[Brain] DeepSeek 思考完毕，直接回复内容: {cleaned_reply}")

                self.memory.add_message(msg.channel_id, "user", message_to_send)
                self.memory.add_message(msg.channel_id, agent_raw.role, cleaned_reply)

                return cleaned_reply

            return None

        except Exception as e:
            # 捕获网络超时、API Key 错误等异常，打印日志并优雅兜底
            print(f"[Brain Error] 调用 DeepSeek API 发生错误: {e}")
            return "不好意思，我现在大脑连接有点不稳定，请稍后再试一次吧！"