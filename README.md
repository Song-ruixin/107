# 星图计划： 中国科学技术大学学生会宣传部Agent

## 介绍

欢迎使用本项目，项目旨在构建一个Linux平台上基于QQ交互的AI智能体，主要负责文件的查找发送，图像/表情包识别，以及智能群聊管理，互动式聊天等功能

---

## 部署方式

### 前置需求
本项目采用 Docker 打包部署，无需任何额外的程序（已经内部集成napcat作为QQ客户端）
<mark> 提示 </mark>：如果没有docker，请使用下列指令安装（需要保证网络）：

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
解压交付包后，请检查应该有如下目录结构：
```
qq_bot_release/
├── app_images.tar         # 离线镜像包（包含 NapCat 和 Agent 环境）
├── docker-compose.yml     # 容器服务编排配置文件
├── READEME.md             # 介绍文档（本文件）
├── .env                   # 核心环境变量配置文件（API Key、白名单等）
├── SYSTEM_PROMPT.txt      # 单独书写智能体的系统提示词
├── files/                 # 共享资料库（存放需让机器人发送的本地文档/图片）
├── data/                  # 运行数据目录（自动持久化保存历史聊天记录与数据库）
└── napcat/
    ├── qq/                # NapCat 配置文件
    └── config/            # NapCat 配置文件
```

### 开始部署

1. 准备配置文件：
   修改 .env 文件，填入你的大模型 API Key 及白名单等配置（详细情况请根据.env文件中注释的引导）：

   <mark> 注意 </mark>： .env文件中等号`=`左右两边都不应该有空格，否则可能导致配置读取失败

   ```
   # 示例配置项
   API_KEY=your_api_key_here
   WHITELIST_USERS=12345678,87654321
   ```

2. 导入离线镜像：
   进入项目根目录，在终端(bash)中执行以下命令导入离线镜像包：

   ```bash   
   docker load -i app_images.tar
   ```
   3. 启动 NapCat ：首次登录需授权，运行以下命令单独启动 NapCat 服务拉起后台QQ（电脑不需要安装桌面QQ程序）
   ```bash
   docker compose up -d napcat
   ```

   查看日志：
   ```bash
   docker compose logs  napcat | grep token
   ```
   
4. 登陆QQ，并核对 WebUI 设置：
   上述指令应该会有类似如下输出

   ```bash
   napcat  | 09-07 07:12:54 [info] [NapCat] [WebUi] WebUi User Panel Url: http://127.0.0.1:6099/webui?token=e36f886c4bea

   ```
   1. 打开浏览器访问：`http://127.0.0.1:6099/webui?token=e36f886c4bea`（替换为你对应上方输出 WebUi User Panel Url）
   2. 使用手机 QQ 扫码完成登录。
   3. 进入 **网络配置 (OneBot 11)** -> 点击 **WebSocket Client (客户端)**(如果如果此处已经存在一个配置，则跳过后面步骤，否则点击添加 **WebSocket Client (客户端)** 并填写下面内容)：
   
   * **启用**：开启（红勾）
   * **名称**：自定义（如 `qqbot`）
   * **URL**：填入 `ws://172.17.0.1:8080` 
   * **SSL 证书验证**：**务必关闭（切换为灰色）** 
   * 点击右下角 **保存**。
   
5. 启动Agent服务本体

   在终端中按 Ctrl + C 退出当前日志输出，然后运行以下命令启动 Agent 主程序：
   ```bash 
   docker compose up -d
   ```
   启动后，QQ 机器人即开始工作。

## 运维与日常管理

### 查看运行日志
```bash
# 查看 Agent 业务日志（此处可以看到agent的日志信息）
docker compose logs -f agent

# 查看 NapCat 协议端日志
docker compose logs -f napcat

停止与重启服务
# 重启所有服务
docker compose restart

# 停止并删除容器（不会丢失 files/ 和 data/ 中的文件）
docker compose down
```

## 使用技巧
### 和机器人说话
私聊情况下机器人会直接回复白名单中的人（如果开启），否则回复所有人。

群聊情况需要@机器人才会回复，目前只支持群聊整体白名单，在群聊内部则会回复所有人（即不能要求只回复群聊的特定用户）
### 文件

将需要机器人发送的文档、图片或 PDF 文件直接放入宿主机的 ./files/ 目录下，Agent 即可在程序中实时读取并调用 NapCat 发送给 QQ 目标用户或群聊。

### 清除对话历史

在qq聊天框中输入"/reset", "/clear", "/new", "重置记忆", "清空记忆"几个关键词的任意一个，均可以重置历史对话，历史对话最多保存五十轮。



