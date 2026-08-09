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


settings = Settings()