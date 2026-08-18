# AI 工具集 (EGC)

Flask 轻量级 AI 工具管理平台，集成模拟器部署、文件管理、SFTP 传输、AI 编程助手等服务控制于一体。

## 功能概览

| 模块 | 说明 |
|------|------|
| 仪表盘 | 系统资源监控（CPU/内存/磁盘），服务状态一览，快捷启停 |
| 文件管理 | 全文件系统浏览、上传、下载、删除，支持拖拽 |
| 模拟器管理 | GridSim 打包、本机/远程部署、升级备份还原、服务启停 |
| 限电管理 | 限电策略配置、测试执行、日志查看 |
| SFTP 传输 | 远程文件管理，双栏对照操作，保存服务器连接记录 |
| OpenCode-Web | AI 编程助手 Web 界面启停控制 |
| Hermes Web UI | Hermes AI Agent Web 界面启停控制 |
| Edge-EMS 部署 | 边缘能源管理系统一键部署工具 |
| 工作报表 | 工作日志记录与查看 |

## 技术栈

- **后端**: Python 3.8+ / Flask 3.0.3 / SQLite
- **前端**: Jinja2 模板 / 原生 CSS / JavaScript（无框架依赖）
- **部署**: systemd 守护进程
- **依赖**: 仅 Flask（其余均为 Python 标准库）
- **扩展**: Azure Blob Storage（Edge-EMS 部署）、Paramiko（SFTP 传输）

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
├── run.py                        # 入口
├── start-server.sh               # 启动脚本
├── egc-deploy.sh                 # 打包 & 部署脚本
├── AIDC-Demo0707.html            # AIDC 仪表板演示文件
├── aidc-dashboard.html           # AIDC 仪表板
├── app/
│   ├── __init__.py               # Flask app factory
│   ├── auth.py                   # 登录认证
│   ├── dashboard.py              # 仪表盘 + 服务控制 API
│   ├── file_manager.py           # 文件管理
│   ├── simulator_manager.py      # 模拟器部署管理
│   ├── curtailment.py            # 限电管理模块
│   ├── sftp_manager.py           # SFTP 远程传输
│   ├── ems_deploy.py             # Edge-EMS 部署
│   ├── work_reports.py           # 工作报表模块
│   ├── models.py                 # SQLite 用户模型
│   ├── templates/                # Jinja2 模板
│   │   ├── base.html             # 基础模板
│   │   ├── dashboard.html        # 仪表盘页面
│   │   ├── simulator_manager.html # 模拟器管理页面
│   │   ├── curtailment_manager.html # 限电管理页面
│   │   ├── sftp.html             # SFTP 传输页面
│   │   ├── ems_deploy.html       # Edge-EMS 部署页面
│   │   └── work_reports.html     # 工作报表页面
│   ├── ems_deploy_assets/        # Edge-EMS 部署资源
│   │   ├── scripts/              # 部署脚本
│   │   ├── blob_tool.py          # Azure Blob 工具
│   │   └── main.py               # 主部署程序
│   └── static/                   # 静态资源
├── edge-ems-deploy-tool/         # Edge-EMS 部署工具（独立版本）
├── CurtailmentTest/              # 限电测试脚本
├── data/                         # 运行时数据（自动生成）
│   ├── users.db                  # 用户数据库
│   ├── sim-deployments.json      # 部署记录
│   └── sftp-servers.json         # SFTP 服务器记录
└── docs/                         # 文档
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

## 限电管理

IEC104 限电管理器，用于生成和管理限电策略二进制文件：

- **自动生成**: 后台线程每 30 分钟自动生成限电策略文件
- **文件管理**: 查看、删除已生成的限电文件
- **策略配置**: 支持自定义限电值和计划时间
- **自动清理**: 仅保留最新的 4 个文件

**配置参数:**
- 文件存储路径: `/data2/sftp/fep/Curtailment`
- 文件前缀: `203_0000_01000300000000006500010011_`
- 保留文件数: 4

**使用方式:**
- Web 界面: 登录后访问 `/curtailment`
- API 接口: `/api/curtailment/control` (启动/停止生成器)
- 手动生成: `/api/curtailment/generate` (支持自定义参数)

**限电测试脚本:**
```bash
cd CurtailmentTest

# 启动限电测试
bash start_file.sh

# 更新限电文件
bash updatefile.sh
```

## Edge-EMS 部署工具

独立部署工具，支持边缘能源管理系统的快速部署：

**核心功能:**
- 一键部署: 支持 HPUY / EE 两类服务器
- 多组件支持: edge-ems / edge-ems-hmi / edge-ems-hmi-fe
- 自动识别架构: HMI-FE 支持 x86_64 / arm64
- 完整流程: Azure Blob → 本地镜像 → 目标服务器 → 解压 → 权限修复

**快速部署:**
```bash
cd edge-ems-deploy-tool

# 1. 配置环境变量
cp .env.example .env
vim .env

# 2. 检查环境
python3 check_environment.py

# 3. 执行部署
python3 main.py --branch develop_2605 --server HPUY --component all
```

**部署选项:**
- 完整部署: `python3 main.py --branch develop_2605 --server HPUY --component all`
- 仅下载: `python3 main.py --branch develop_2605 --server HPUY --component all --tar-only`
- 特定组件: `python3 main.py --branch develop_2605 --server HPUY --component edge-ems`

详见 [部署指南](docs/deployment-guide.md) 和 [Edge-EMS 用户手册](edge-ems-deploy-tool/USER_MANUAL.md)。

## License

Private
