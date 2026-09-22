# AI 工具集 (EGC)

Flask 轻量级 AI 工具管理平台，集成文件管理、SFTP 传输、AI 模型代理网关、AI 编程助手等服务控制于一体。

## 功能概览

| 模块 | 说明 |
|------|------|
| 仪表盘 | 系统资源监控（CPU/内存/磁盘），服务状态一览，快捷启停 |
| 文件管理 | 全文件系统浏览、上传、下载、删除，支持拖拽 |
| SFTP 传输 | 远程文件管理，双栏对照操作，保存服务器连接记录 |
| Kiro Gateway | AI 模型代理网关，支持 Claude、GLM、MiniMax、Qwen 等 13+ 模型 |
| Edge-EMS 部署 | 边缘能源管理系统一键部署工具 |
| 限电管理 | 限电策略配置、测试执行、日志查看 |
| OpenCode-Web | AI 编程助手 Web 界面启停控制 |
| Hermes Web UI | Hermes AI Agent Web 界面启停控制 |

## 技术栈

- **后端**: Python 3.8+ / Flask 3.0.3 / SQLite
- **前端**: Jinja2 模板 / 原生 CSS / JavaScript（无框架依赖）
- **部署**: systemd 守护进程
- **依赖**: Flask、httpx（Kiro Gateway）
- **扩展**: Azure Blob Storage（Edge-EMS 部署）、Paramiko（SFTP 传输）

## 快速开始

```bash
# 安装依赖
pip3 install flask httpx

# 启动（前台）
python3 run.py --port 8080

# 启动（systemd 守护）
bash start-server.sh
systemctl enable egc-server
systemctl start egc-server
```

访问 `http://服务器IP:8080`，默认账号 `admin / admin123`。

## Kiro Gateway 使用指南

Kiro Gateway 是一个 AI 模型代理网关，将多种 AI 模型统一为 OpenAI 兼容接口。

### 支持模型（13+）

| 模型 ID | 说明 |
|---------|------|
| auto-kiro | 自动选择最佳模型 |
| claude-sonnet-4.5 | Claude Sonnet 4.5（推荐编码任务）|
| claude-sonnet-4.6 | Claude Sonnet 最新版 |
| claude-opus-4.7 | Claude Opus 最强性能 |
| claude-haiku-4.5 | Claude Haiku 快速响应 |
| glm-5 | 智谱 GLM-5 |
| qwen3-coder-next | 通义千问编码专用 |
| minimax-m2.5 | MiniMax MoE 模型 |
| deepseek-3.2 | DeepSeek 推理模型 |

### 使用方式

**OpenAI SDK:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://服务器IP:8000/v1",
    api_key="kiro-gateway-2026-secret"
)

response = client.chat.completions.create(
    model="claude-sonnet-4.5",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)
```

**Claude Code:**
```bash
export ANTHROPIC_BASE_URL=http://服务器IP:8000
export ANTHROPIC_API_KEY=kiro-gateway-2026-secret

claude --model claude-sonnet-4.5
```

**cURL:**
```bash
curl http://服务器IP:8000/v1/chat/completions \
  -H "Authorization: Bearer kiro-gateway-2026-secret" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4.5","messages":[{"role":"user","content":"Hello"}]}'
```

### 管理界面

访问 `http://服务器IP:8080/kiro-gateway/` 进行：
- 服务启停控制
- API Key 查看
- 模型列表浏览
- 连接测试
- 日志查看

## 项目结构

```
EGC/
├── run.py                        # 入口
├── start-server.sh               # 启动脚本
├── app/
│   ├── __init__.py               # Flask app factory
│   ├── auth.py                   # 登录认证
│   ├── dashboard.py              # 仪表盘 + 服务控制 API
│   ├── file_manager.py           # 文件管理
│   ├── sftp_manager.py           # SFTP 远程传输
│   ├── kiro_gateway.py           # Kiro Gateway 管理
│   ├── ems_deploy.py             # Edge-EMS 部署
│   ├── curtailment.py            # 限电管理模块
│   ├── models.py                 # SQLite 用户模型
│   ├── templates/                # Jinja2 模板
│   │   ├── base.html             # 基础模板
│   │   ├── dashboard.html        # 仪表盘页面
│   │   ├── sftp.html             # SFTP 传输页面
│   │   ├── kiro_gateway.html     # Kiro Gateway 管理页面
│   │   ├── ems_deploy.html       # Edge-EMS 部署页面
│   │   └── curtailment_manager.html # 限电管理页面
│   └── static/                   # 静态资源
├── data/                         # 运行时数据（自动生成）
│   ├── users.db                  # 用户数据库
│   └── sftp-servers.json         # SFTP 服务器记录
└── docs/                         # 文档
```

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SECRET_KEY` | 内置开发密钥 | Flask session 加密密钥 |
| `EGC_BASE_DIR` | 项目根目录 | 工作目录 |

## License

Private
