import os

class Settings:
    #qq client
    QQ_WS_HOST = "0.0.0.0"
    QQ_WS_PORT = "8080"
    QQ_WS_TOKEN = "107"

    #AI model
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "deepseek_api_key")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL_NAME: str = "deepseek-v4-pro"

    VISION_API_KEY: str =os.getenv("VISION_API_KEY", "sk-mrfapqodqzhdmjqxtxigkuujoimwxbjzvzgdhivrojcjiwdd")
    VISION_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VISION_MODEL_NAME: str = "Qwen/Qwen3-VL-8B-Instruct"

    CONTAINER_BASE_DIR = "/usr/src/app/napcat/files" 
    HOST_BASE_DIR = os.path.expanduser("~/Project/107/files")


settings = Settings()