import os
import base64
import mimetypes
import httpx
from openai import AsyncOpenAI

from config.settings import settings
from tools.tool_manager import tool_manager # 依然保留

# 1. 声明给主模型看的 Schema
READ_FILE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取并识别指定本地路径或网络 URL 的文件/图片内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path_or_url": {
                    "type": "string",
                    "description": "文件的绝对路径或网络下载 URL（如图片链接、文档链接）"
                }
            },
            "required": ["file_path_or_url"]
        }
    }
}


vision_client = AsyncOpenAI(
    api_key=settings.VISION_API_KEY,
    base_url=settings.VISION_BASE_URL,
)

# 2. 纯粹的执行函数：接收地址 -> 返回结果字符串
@tool_manager.register(READ_FILE_TOOL_SCHEMA)
async def execute_read_file(file_path_or_url: str) -> str:
    file_path = file_path_or_url
    is_temp_file = False
    detected_mime_type = None  # 记录从网络 Header 中获取到的真实 MIME 类型

    try:
        # -------------------------------------------------------------
        # 步骤 A：如果是网络 URL，下载并获取真实的 Content-Type
        # -------------------------------------------------------------
        if file_path_or_url.startswith(("http://", "https://")):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                    resp = await client.get(file_path_or_url, timeout=20.0)
                    resp.raise_for_status()
                    
                    # 从 HTTP 响应头中读取 Content-Type（解决 QQ 图片 URL 没有后缀的问题）
                    detected_mime_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                    
                    os.makedirs("./downloads", exist_ok=True)
                    filename = f"temp_{os.getpid()}_" + (file_path_or_url.split("/")[-1].split("?")[0] or "file.bin")
                    file_path = os.path.join("./downloads", filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    
                    is_temp_file = True
                    print(f"[读取成功] 网络文件已缓存")
                    
            except Exception as e:
                return f"[读取失败] 网络文件下载失败: {str(e)}"

        if not os.path.exists(file_path):
            return f"[读取失败] 文件不存在: {file_path}"

        ext = os.path.splitext(file_path)[1].lower()

        # 如果 Header 没拿到，退化使用本地文件后缀探测
        if not detected_mime_type:
            detected_mime_type = mimetypes.guess_type(file_path)[0] or ""

        # -------------------------------------------------------------
        # 步骤 B：只要 Content-Type 或后缀表明是图片，就走看图 API
        # -------------------------------------------------------------
        is_image_by_ext = ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]
        is_image_by_mime = detected_mime_type.startswith("image/")

        if is_image_by_ext or is_image_by_mime:
            try:
                with open(file_path, "rb") as img_file:
                    base64_img = base64.b64encode(img_file.read()).decode("utf-8")
                
                # 如果获得的 mime 泛指，兜底给 image/jpeg
                final_mime = detected_mime_type if detected_mime_type.startswith("image/") else "image/jpeg"
                model_name = settings.VISION_MODEL_NAME

# getattr(settings, "VISION_MODEL_NAME", "Qwen/Qwen3-VL-8B-Instruct")

                print(f"[类型识别完成] 准备提交大模型:[Name]{model_name} [Url]{settings.VISION_BASE_URL}")
                resp = await vision_client.chat.completions.create(
                    model=model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请详细分析并提取这张图片里的所有文字和关键信息："},
                            {"type": "image_url", "image_url": {"url": f"data:{final_mime};base64,{base64_img}"}}
                        ]
                    }]
                )
                print(f"=== 图片识别分析结果 ===\n{resp.choices[0].message.content}")
                return f"=== 图片识别分析结果 ===\n{resp.choices[0].message.content}"
            except Exception as e:
                print(f"[识别失败] 视觉模型处理失败: {str(e)}")
                return f"[识别失败] 视觉模型处理失败: {str(e)}"

        # -------------------------------------------------------------
        # 步骤 C：文本读取（必须限制最大读取字符数，防止文本爆 Token）
        # -------------------------------------------------------------
        try:
            # 安全保护：如果既不是图片，也不是常见文本格式，拒绝读取二进制
            valid_text_exts = [".txt", ".md", ".py", ".json", ".log", ".csv", ".xml", ".html", ".js", ".c", ".cpp"]
            if ext and ext not in valid_text_exts and not detected_mime_type.startswith("text/"):
                return f"[读取失败] 不支持读取非文本/非图片类型的二进制文件 ({ext or detected_mime_type})"

            MAX_CHARS = 20000  # 限制最多读取 20000 字符（约 5000~8000 Token）
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(MAX_CHARS)
                
                # 如果文件超出最大限制，增加截断提示
                if len(content) >= MAX_CHARS:
                    content += f"\n\n[警告：文件内容过长，已被截断，仅显示前 {MAX_CHARS} 个字符]"
            return content
        except Exception as e:
            return f"[读取失败] 文件读取异常: {str(e)}"

    finally:
        if is_temp_file and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[Warning] 临时文件清理失败: {file_path}, 错误: {e}")