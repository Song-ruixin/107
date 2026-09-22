# 1. 使用官方轻量级 Python 3.10 镜像作为基础
FROM python:3.10-slim

# 设置环境变量：禁止 Python 生成 .pyc 文件，并让日志输出实时打印（不被缓存）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 2. 设置容器内部的工作目录
WORKDIR /app

# 3. 先复制依赖文件并安装（利用 Docker 缓存层，只要 requirements.txt 没变就无需重新下载依赖）
COPY requirements.txt .

# 使用清华镜像源加速安装，并清理 pip 缓存以缩小镜像体积
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制当前项目下的所有代码到容器内
COPY . .

# 5. 容器启动时默认运行主程序
CMD ["python", "main.py"]   