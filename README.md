这份用户文档面向小白/离线部署用户，去除了复杂的编译步骤，聚焦于“零环境依赖、一键导入与启动”。本项目基于Linxu操作系统和docker

### 功能
项目最终可以直接在QQ与部署在电脑上的机器人交互，并实现文件查找，发送，图片识别，智能对话等功能。

---

# NapCat + Python Agent 极简部署指南

本项目采用 Docker 容器化技术，将 QQ 协议端（NapCat）与 Python Agent 服务打包交付。宿主机仅需安装 Docker，无需配置 Python、Node.js 等任何开发环境。

<mark> 提示 </mark>：如果没有docker，请使用下列指令安装（保证网络）：

```bash
# 下载并运行官方安装脚本
curl -fsSL https://get.docker.com | bash

# 启动 Docker 并设置开机自启
sudo systemctl enable --now docker

# （可选）将当前用户加入 docker 组，之后无需输入 sudo 即可运行 docker 命令
sudo usermod -aG docker $USER
# 执行后需要重新登录或运行以下命令使其生效：
newgrp docker
```

### 目录结构
解压交付包后，目录结构如下：
```
qq_bot_release/
├── app_images.tar         # 离线镜像包（包含 NapCat 和 Agent 环境）
├── docker-compose.yml     # 容器服务编排配置文件
├── .env                   # 核心环境变量配置文件（API Key、白名单等）
├── files/                 # 共享资料库（存放需让机器人发送的本地文档/图片）
├── data/                  # 运行数据目录（自动持久化保存历史聊天记录与数据库）
└── napcat/
    └── config/            # NapCat 配置文件保存目录
```

### 快速开始
 1. 准备配置文件
   首次运行前必做
   修改 .env 文件，填入你的大模型 API Key 及白名单等配置：

```
# 示例配置项
API_KEY=your_api_key_here
WHITELIST_USERS=12345678,87654321
```

 2. 导入离线镜像
   无需连网下载镜像
   进入项目根目录，在终端（Terminal 或 PowerShell）中执行以下命令导入离线镜像包：
```bash   
docker load -i app_images.tar
```
 3. 启动 NapCat 并完成 QQ 扫码登录
   首次登录需授权
   运行以下命令单独启动 NapCat 服务
```bash
docker compose up -d napcat
```
   查看日志：
```bash
docker compose logs  napcat | grep token
```
   
### WebUI 设置核对步骤：
上述指令应该会有类似如下输出

```bash
napcat  | 09-07 07:12:54 [info] [NapCat] [WebUi] WebUi User Panel Url: http://127.0.0.1:6099/webui?token=e36f886c4bea

```
1. 打开浏览器访问：`http://127.0.0.1:6099/webui?token=e36f886c4bea`（替换为你对应上方输出 WebUi User Panel Url）
2. 使用手机 QQ 扫码完成登录。
3. 进入 **网络配置 (OneBot 11)** -> 点击 **添加 WebSocket Client (客户端)**(如果原本不存在任何选项，如果已经有一个 WebSocket Client (客户端)，则跳过后面步骤)：
* **启用**：开启（红勾）
* **名称**：自定义（如 `qqbot`）
* **URL**：填入 `ws://172.17.0.1:8080` 
* **SSL 证书验证**：**务必关闭（切换为灰色）** 
* 点击右下角 **保存**。
   
 ### 启动全套挂机服务
   开启 24 小时自动化服务
   在终端中按 Ctrl + C 退出当前日志输出，然后运行以下命令启动 Agent 主程序：
```bash 
docker compose up -d
```
   启动后，QQ 机器人即开始工作。

### 运维与日常管理

#### 查看运行日志
```bash
# 查看 Agent 业务日志
docker compose logs -f agent

# 查看 NapCat 协议端日志
docker compose logs -f napcat

停止与重启服务
# 重启所有服务
docker compose restart

# 停止并删除容器（不会丢失 files/ 和 data/ 中的文件）
docker compose down
```

#### 更新/发送本地文件
将需要机器人发送的文档、图片或 PDF 文件直接放入宿主机的 ./files/ 目录下，Agent 即可在程序中实时读取并调用 NapCat 发送给 QQ 目标用户或群聊。


