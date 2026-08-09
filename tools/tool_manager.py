from typing import List, Dict, Callable, Any

import importlib
import pkgutil

import tools

class ToolManager:
    def __init__(self) -> None:
        self.TOOLS: List[Dict] = []
        self.TOOL_MAP: Dict[str, Callable] = {}

    def register(self, tool: Dict[str, Any]):

        def decorator(func: Callable):

            func_name = tool.get("function", {}).get("name", func.__name__)

            self.TOOL_MAP[func_name] = func
            self.TOOLS.append(tool)

            return func
            
        return decorator

    #from Gemini
    def auto_load_tools(self):
        """自动扫描并导入 tools 目录下的所有模块，触发装饰器注册"""
        for _, module_name, _ in pkgutil.iter_modules(tools.__path__):
            if module_name != "tool_manager":  # 排除注册中心自身
                importlib.import_module(f"tools.{module_name}")


tool_manager = ToolManager()