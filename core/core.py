import json
import re
import inspect
from typing import Optional, List, Dict
from openai import AsyncOpenAI

from core.schema import UserMessage, MessageEnv
from config.settings import settings

from core.memory import MemoryManager

# TOOLS 定义以及 TOOL_MAP 函数映射字典
from tools.tool_manager import tool_manager


class AgentBrain:
    def __init__(self, adapter=None) -> None:
        # 导入所有工具
        self.adapter = adapter  # 保存 adapter 引用
        tool_manager.auto_load_tools()

        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.LLM_MODEL_NAME
        self.system_prompt = settings.SYSTEM_PROMPT
        self.memory = MemoryManager()
        self.memory.load()

    def check_permission(self, msg: UserMessage) -> bool:
        """
        基于 settings.py 环境变量对 UserMessage 进行权限拦截校验
        """
        if not settings.ENABLE_WHITELIST:
            return True

        if msg.message_env == MessageEnv.PRIVATE:
            return not settings.ALLOWED_USERS or msg.user_id in settings.ALLOWED_USERS

        if msg.message_env == MessageEnv.GROUP:
            return not settings.ALLOWED_GROUPS or msg.channel_id in settings.ALLOWED_GROUPS

        return True

    async def process_message(self, msg: UserMessage) -> Optional[str]:
        # 1. 过滤策略：白名单和是否@同时检验
        if not self.check_permission(msg):
            return None
        
        if msg.message_env == MessageEnv.GROUP and not msg.is_at_me:
            return None

        clean_content = msg.content.strip().lower()
        if clean_content in ["/reset", "/clear", "/new", "重置记忆", "清空记忆"]:
            self.memory.clear(msg.channel_id)
            print(f"[Brain] 收到硬指令，已物理清空 {msg.channel_id} 的历史记忆")
            return "🧹 记忆已成功重置，我们可以重新开始对话了！"
        
        history = self.memory.get_history(msg.channel_id)
        display_name = msg.user_name or "用户"

        # 2. 针对消息内容中包含的附件，生成语义化提示追加到 prompt
        attachment_prompts = []
        if msg.attachments:
            for idx, att in enumerate(msg.attachments, 1):
                att_info = (
                    f"附件#{idx}: [类型={att.type.value}] "
                    f"文件名={att.file_name or '未命名'} "
                    f"地址/URL={att.url_or_path}"
                )
                attachment_prompts.append(att_info)

        user_content_parts = [f"{display_name}({msg.user_id}): {msg.content}"]
        if attachment_prompts:
            user_content_parts.append("\n【本条消息包含以下附件信息】:")
            user_content_parts.extend(attachment_prompts)
            user_content_parts.append("提示：如果需要读取或分析上述附件的具体内容，请调用 read_file_content 工具并传入对应地址。")

        final_user_prompt = "\n".join(user_content_parts)

        # 3. 构造发送给 DeepSeek 的消息列表 (Messages Array)
        messages: List[Dict] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": final_user_prompt})

        print(f"[Brain] 准备请求 DeepSeek ({self.model}) | 来自用户 {msg.user_name}: {msg.content}")
        print(f"已装载工具: {list(tool_manager.TOOL_MAP.keys())}")
        
        try:
            # 4. 使用 while 循环支持多轮工具调用链（设定最大循环轮数防止死循环）
            max_turns = 6
            turn = 0
            final_reply = "抱歉，处理您的请求时遇到了一点小状况。"

            while turn < max_turns:
                turn += 1
                print(f"[Brain] 正在进行第 {turn} 轮对话/工具调用...")

                # 请求 DeepSeek API (每次循环都带上完整的 tools 和 thinking 配置)
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore
                    stream=False,
                    reasoning_effort="high" if turn == 1 else "medium",
                    tools=tool_manager.TOOLS,  # type: ignore
                    tool_choice="auto",
                    extra_body={"thinking": {"type": "enabled"}},
                    temperature=0.7,
                )  # type: ignore

                agent_raw = response.choices[0].message

                # A. 如果 AI 决定调用工具
                if agent_raw.tool_calls:
                    print(f"[Brain] 第 {turn} 轮：DeepSeek 决定调用工具: {[tc.function.name for tc in agent_raw.tool_calls]}")

                    # ⭐️ 核心规范：必须先将 assistant 的 tool_calls 消息追加到队列中
                    messages.append(agent_raw)  # type: ignore

                    # 遍历处理所有的工具调用需求
                    for tool_call in agent_raw.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            func_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}

                        print(f"[Brain] 正在执行本地工具: {func_name} | 参数: {func_args}")

                        # 寻找并执行对应的 Python 函数
                        if func_name in tool_manager.TOOL_MAP:
                            target_func = tool_manager.TOOL_MAP[func_name]
                            try:
                                context_args = {
                                    "adapter": self.adapter,
                                    "channel_id": msg.channel_id,
                                    "message_env": msg.message_env
                                }

                                sig = inspect.signature(target_func)
                                for k, v in context_args.items():
                                    if k in sig.parameters:
                                        func_args[k] = v

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

                    # 工具执行完毕后，进入下一轮循环，让 AI 依据工具返回结果继续决策（如：find_file 完接着调 send_file）
                    continue

                # B. 如果 AI 给出了最终的文本回复
                elif agent_raw.content:
                    raw_content = agent_raw.content.strip()

                    # 安全兜底：如果模型不小心把 DSML 标记文本吐出来了，做正则清理或拦截
                    if "<｜｜DSML｜｜" in raw_content:
                        print("[Brain 警告] 检测到大模型将 Tool Call 以文本形式输出，正在清洗...")
                        raw_content = re.sub(r'<｜｜DSML｜｜.*?</｜｜DSML｜｜.*?>', '', raw_content, flags=re.DOTALL).strip()
                        if not raw_content:
                            raw_content = "操作已执行完毕。"

                    final_reply = raw_content
                    print(f"[Brain] 思考完毕，最终回复内容: {final_reply}")
                    break
                else:
                    final_reply = "操作已完成。"
                    break

            # 5. 记录记忆并返回最终结果
            self.memory.add_message(msg.channel_id, "user", final_user_prompt)
            self.memory.add_message(msg.channel_id, "assistant", final_reply)

            return final_reply

        except Exception as e:
            print(f"[Brain Error] 调用 DeepSeek API 发生错误: {e}")
            return "不好意思，我现在大脑连接有点不稳定，请稍后再试一次吧！"

        
'''import json
import re

from typing import Optional, List, Dict
from openai import AsyncOpenAI

from core.schema import UserMessage, MessageEnv
from config.settings import settings
from config.prompt_templates import SYSTEM_PROMPT
from core.memory import MemoryManager


# TOOLS 定义以及 TOOL_MAP 函数映射字典
from tools.tool_manager import tool_manager


class AgentBrain:
    def __init__(self, adapter=None) -> None:
        #导入所有工具
        self.adapter = adapter  # 保存 adapter 引用
        tool_manager.auto_load_tools()

        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.LLM_MODEL_NAME
        self.system_prompt = SYSTEM_PROMPT
        self.memory = MemoryManager()
        self.memory.load()

    def check_permission(self, msg: UserMessage) -> bool:
        """
        基于 settings.py 环境变量对 UserMessage 进行权限拦截校验
        """
        # 1. 如果未开启白名单，直接放行
        if not settings.ENABLE_WHITELIST:
            return True

        # 2. 私聊消息校验
        if msg.message_env == MessageEnv.PRIVATE:
            # 如果 ALLOWED_USERS 为空，表示不对私聊做限制；否则要求 user_id 在白名单中
            return not settings.ALLOWED_USERS or msg.user_id in settings.ALLOWED_USERS

        # 3. 群聊消息校验
        if msg.message_env == MessageEnv.GROUP:
            # channel_id 对应群号 group_id
            return not settings.ALLOWED_GROUPS or msg.channel_id in settings.ALLOWED_GROUPS

        return True

    async def process_message(self, msg: UserMessage) -> Optional[str]:

        # 过滤策略：白名单和是否@同时检验

        if not self.check_permission(msg):
            return None
        
        if msg.message_env == MessageEnv.GROUP and not msg.is_at_me:
            return None

        clean_content = msg.content.strip().lower()
        if clean_content in ["/reset", "/clear", "/new","重置记忆", "清空记忆"]:
            self.memory.clear(msg.channel_id)
            print(f"[Brain] 收到硬指令，已物理清空 {msg.channel_id} 的历史记忆")
            return "🧹 记忆已成功重置，我们可以重新开始对话了！"
        
        history = self.memory.get_history(msg.channel_id)
        display_name = msg.user_name or "用户"

        # 针对消息内容中包含的附件，生成语义化提示追加到 prompt
        attachment_prompts = []
        if msg.attachments:
            for idx, att in enumerate(msg.attachments, 1):
                att_info = (
                    f"附件#{idx}: [类型={att.type.value}] "
                    f"文件名={att.file_name or '未命名'} "
                    f"地址/URL={att.url_or_path}"
                )
                attachment_prompts.append(att_info)

        # 组装最终送给 AI 的 User Prompt
        # 包含了用户身份、消息文本以及所有附件的元数据
        user_content_parts = [f"{display_name}({msg.user_id}): {msg.content}"]
        if attachment_prompts:
            user_content_parts.append("\n【本条消息包含以下附件信息】:")
            user_content_parts.extend(attachment_prompts)
            user_content_parts.append("提示：如果需要读取或分析上述附件的具体内容，请调用 read_file_content 工具并传入对应地址。")


        final_user_prompt = "\n".join(user_content_parts)

        # 构造发送给 DeepSeek 的消息列表 (Messages Array)
        messages: List[Dict] = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": final_user_prompt})

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
                            # ===== 核心注入逻辑开始 =====
                            # 将当前的 adapter 和上下文元数据补充给 func_args
                            context_args = {
                                "adapter": self.adapter,
                                "channel_id": msg.channel_id,
                                "message_env": msg.message_env
                            }

                            # 只注入函数确实声明了的参数，避免多传报错
                            import inspect
                            sig = inspect.signature(target_func)
                            for k, v in context_args.items():
                                if k in sig.parameters:
                                    func_args[k] = v
                            # ===== 核心注入逻辑结束 =====

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

                # 3. 第二次请求 DeepSeek：让 AI 结合工具返回结果（必须带上 tools 和 thinking 配置！）
                second_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore
                    stream=False,
                    tools=tool_manager.TOOLS,            # type: ignore # <--- 加上这一行！允许它紧接着调用 send_file
                    tool_choice="auto",                 # <--- 加上这一行
                    extra_body={"thinking": {"type": "enabled"}}, # <--- 加上这一行
                    temperature=0.7,
                )

                second_raw = second_response.choices[0].message

                # 如果第二轮它依然通过标准的 tool_calls 触发了发送（比如这次它成功触发了 send_file）
                if second_raw.tool_calls:
                    # 如果需要支持连续多轮调用，这里可以递归或者用 while 循环处理
                    # 但对于你的场景，第二轮通常就是调 send_file 了
                    for tool_call in second_raw.tool_calls:
                        func_name = tool_call.function.name
                        try:
                            func_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}

                        print(f"[Brain] 第二轮正在执行工具: {func_name} | 参数: {func_args}")
                        if func_name in tool_manager.TOOL_MAP:
                            target_func = tool_manager.TOOL_MAP[func_name]
                            context_args = {
                                "adapter": self.adapter,
                                "channel_id": msg.channel_id,
                                "message_env": msg.message_env
                            }
                            import inspect
                            sig = inspect.signature(target_func)
                            for k, v in context_args.items():
                                if k in sig.parameters:
                                    func_args[k] = v
                            
                            if inspect.iscoroutinefunction(target_func):
                                tool_result = await target_func(**func_args)
                            else:
                                tool_result = target_func(**func_args)
                        else:
                            tool_result = f"未找到工具 {func_name}"

                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(tool_result)})

                    # 第三次请求：拿到发送结果后，获取最终的自然语言答复
                    third_response = await self.client.chat.completions.create( # type: ignore
                        model=self.model,
                        messages=messages, # type: ignore
                        stream=False,
                        temperature=0.7,
                    )
                    final_reply = third_response.choices[0].message.content or "文件已为你发送！"
                
                elif second_raw.content:
                    raw_content = second_raw.content.strip()
                    # 配合前面写好的 DSML 文本标签清洗逻辑
                    if "<｜｜DSML｜｜" in raw_content:
                        # 如果它还是吐了文本标签，用正则拦截并真正去执行它（参考前一步的代码）
                        ...
                        final_reply = "文件已成功发送！"
                    else:
                        final_reply = raw_content
                else:
                    final_reply = "操作已完成。"

                cleaned_reply = final_reply.strip()
                print(f"[Brain] 最终回复: {cleaned_reply}")

                self.memory.add_message(msg.channel_id, "user", final_user_prompt)
                self.memory.add_message(msg.channel_id, "assistant", cleaned_reply)

                return cleaned_reply

            return None

        except Exception as e:
            # 捕获网络超时、API Key 错误等异常，打印日志并优雅兜底
            print(f"[Brain Error] 调用 DeepSeek API 发生错误: {e}")
            return "不好意思，我现在大脑连接有点不稳定，请稍后再试一次吧！"
            '''