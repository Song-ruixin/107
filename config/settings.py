import os
from pathlib import Path
from dotenv import load_dotenv  # 新增导入

# 显式加载项目根目录下的 .env 文件
load_dotenv(override=True)

#读取systme prompt文件
# 1. 环境变量优先；若未配置，默认在容器工作目录下寻找 /app/SYSTEM_PROMPT.txt
SYSTEM_PROMPT_PATH_STR = os.getenv("SYSTEM_PROMPT_PATH", "./SYSTEM_PROMPT.txt")
SYSTEM_PROMPT_PATH = Path(SYSTEM_PROMPT_PATH_STR).resolve()

if SYSTEM_PROMPT_PATH.is_file():
    try:
        system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8-sig").strip()
        print(f"[Config] 成功加载系统提示词文件: {SYSTEM_PROMPT_PATH}")
    except Exception as e:
        print(f"[Config] 读取系统提示词文件失败 ({SYSTEM_PROMPT_PATH}): {e}")
        system_prompt = "You are a helpful agent in qq."
else:
    print(f"[Config Warning] 未找到系统提示词文件 ({SYSTEM_PROMPT_PATH})，将使用默认简短 Prompt！")
    system_prompt = "You are a helpful agent in qq."

class Settings:
    #1. QQ WebSocket 配置
    QQ_WS_HOST = os.getenv("QQ_WS_HOST", "0.0.0.0")
    QQ_WS_PORT = os.getenv("QQ_WS_PORT", "8080")  
    QQ_WS_TOKEN = os.getenv("QQ_WS_TOKEN", "107")

    #2. Agent 配置

    SYSTEM_PROMPT = system_prompt

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "your_deepseek_key_here")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

    VISION_API_KEY: str = os.getenv("VISION_API_KEY", "sk-pffmxshjwmqefxwoslxzlyaczstibkigowlpcksjztbxcgio")
    VISION_BASE_URL: str = os.getenv("VISION_BASE_URL", "https://maas.qianwenaiapi.com/compatible-mode/v1")
    VISION_MODEL_NAME: str = os.getenv("VISION_MODEL_NAME", "qwen-vl-plus")

    # 3. 路径映射
    CONTAINER_BASE_DIR = "/usr/src/app/napcat/files" 
    HOST_BASE_DIR = os.getenv("HOST_BASE_DIR", "./files")

    # 白名单相关配置
    ENABLE_WHITELIST: bool = os.getenv("ENABLE_WHITELIST", "false").lower() == "true"
    
    _allowed_users_raw = os.getenv("ALLOWED_USERS", "")
    ALLOWED_USERS: list[str] = [u.strip() for u in _allowed_users_raw.split(",") if u.strip()]

    _allowed_groups_raw = os.getenv("ALLOWED_GROUPS", "")
    ALLOWED_GROUPS: list[str] = [g.strip() for g in _allowed_groups_raw.split(",") if g.strip()]

settings = Settings()
