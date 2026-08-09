from tools.tool_manager import tool_manager #这一句保留

#描述你的函数的具体信息，格式参见deepseek的开发文档，或者询问ai
WEATHER_SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称，例如：合肥、北京"
                    }
                },
                "required": ["location"] # 必填字段
            }
        }
    }


@tool_manager.register(WEATHER_SCHEMA)  #这一句需要添加到函数的前方
async def get_weather(location: str) -> str:
    # 这只是一个示范函数
    if "合肥" in location:
        return "合肥今天多云转晴，气温 25°C，湿度 60%"

    elif "泸州" in location:
        return "泸州天气小雨，气温 20°C，湿度 80%"
    
    return f"未查询到 {location} 的天气信息"