# AI 工具集 (EGC)

Flask 轻量级 AI 工具管理平台，集成模拟器部署、文件管理、SFTP 传输、AI 编程助手等服务控制于一体。

## 功能概览

| 模块 | 说明 |
|------|------|
| 仪表盘 | 系统资源监控（CPU/内存/磁盘），服务状态一览，快捷启停 |
| 文件管理 | 全文件系统浏览、上传、下载、删除，支持拖拽 |
| 模拟器管理 | GridSim 打包、本机/远程部署、升级备份还原、服务启停 |
| SFTP 传输 | 远程文件管理，双栏对照操作，保存服务器连接记录 |
| OpenCode-Web | AI 编程助手 Web 界面启停控制 |
| Hermes Web UI | Hermes AI Agent Web 界面启停控制 |
| Edge-EMS 部署 | 边缘能源管理系统一键部署工具 |

## 技术栈

- **后端**: Python 3.8+ / Flask 3.0.3 / SQLite
- **前端**: Jinja2 模板 / 原生 CSS（无框架依赖）
- **部署**: systemd 守护进程
- **依赖**: 仅 Flask（其余均为 Python 标准库）

## 快速开始

```bash
# 安装
pip3 install flask

# 启动（前台）
python3 run.py --port 8080

# 启动（systemd 守护）
bash start-server.sh
systemctl enable egc-server
systemctl start egc-server
```

访问 `http://服务器IP:8080`，默认账号 `admin / admin123`。

## 项目结构

```
EGC/
├── run.py                    # 入口
├── start-server.sh           # 启动脚本
├── egc-deploy.sh             # 打包 & 部署脚本
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── auth.py               # 登录认证
│   ├── dashboard.py          # 仪表盘 + 服务控制 API
│   ├── file_manager.py       # 文件管理
│   ├── simulator_manager.py  # 模拟器部署管理
│   ├── sftp_manager.py       # SFTP 远程传输
│   ├── ems_deploy.py         # Edge-EMS 部署
│   ├── models.py             # SQLite 用户模型
│   ├── templates/            # Jinja2 模板
│   └── static/               # 静态资源
├── data/                     # 运行时数据（自动生成）
│   ├── users.db              # 用户数据库
│   ├── sim-deployments.json  # 部署记录
│   └── sftp-servers.json     # SFTP 服务器记录
└── docs/                     # 文档
```

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SECRET_KEY` | 内置开发密钥 | Flask session 加密密钥 |
| `EGC_BASE_DIR` | 项目根目录 | 工作目录 |

## 一键打包部署

```bash
# 源服务器打包
bash egc-deploy.sh pack

# 目标服务器部署
bash egc-deploy.sh deploy egc-bundle.tar.gz
```

详见 [部署指南](docs/deployment-guide.md)。

## License

Private
