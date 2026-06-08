# AI 工具集 — 设计文档

> 版本：1.0 | 最后更新：2026-05-22

---

## 一、项目概述

AI 工具集是一个基于 Flask 的轻量级 Web 管理面板，提供以下核心能力：

- **文件管理** — 全文件系统浏览、上传、下载、删除
- **IEC104 模拟器管理** — 本地/远程部署、升级、启停控制、版本管理
- **用户认证** — 基于 Session + SQLite 的登录/注册/注销

### 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Flask 3.0.3（Python 3.8.10） |
| 数据库 | SQLite3 |
| 前端 | Jinja2 模板 + 原生 CSS（暗色主题） |
| 进程管理 | systemd（egc-server.service） |
| 远程操作 | sshpass + scp + ssh（远程部署） |

### 设计原则

- **Blueprint 模式** — 每个工具是一个独立 Blueprint，可插拔扩展
- **无外部依赖** — 仅使用 Flask + Python 标准库（pip 不可用）
- **暗色主题** — 一致的暗色 UI，匹配 IEC 模拟器风格
- **全文件系统访问** — 文件管理器不受限于项目目录

---

## 二、项目结构

```
/root/EGC/
├── run.py                       # Flask 入口
├── start-server.sh              # 手动启动脚本
├── app/
│   ├── __init__.py              # App Factory + Blueprint 注册
│   ├── models.py                # SQLite 用户模型
│   ├── auth.py                  # 认证 Blueprint
│   ├── dashboard.py             # 仪表盘 Blueprint
│   ├── file_manager.py          # 文件管理 Blueprint
│   ├── simulator_manager.py     # IEC104 模拟器管理 Blueprint
│   └── templates/
│       ├── base.html            # 布局模板（侧边栏 + 顶栏 + Toast）
│       ├── login.html           # 登录页
│       ├── register.html        # 注册页
│       ├── dashboard.html       # 仪表盘
│       ├── file_manager.html    # 文件管理
│       └── simulator_manager.html # 模拟器管理
├── data/
│   ├── users.db                 # SQLite 用户数据
│   └── sim-deployments.json     # 远程服务器记录
├── docs/
│   └── design-document.md       # 本设计文档
└── 其他项目文件...
```

---

## 三、App Factory（app/__init__.py）

**职责**：创建 Flask 实例，初始化数据库，注册所有 Blueprint。

```python
def create_app():
    app = Flask(__name__)
    app.secret_key = ...
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
    # ...
    # 注册 Blueprint：
    #   /login, /register, /logout         → auth_bp
    #   /files, /api/files, /api/upload... → fm_bp
    #   /dashboard                          → dashboard_bp
    #   /simulator, /api/simulator/*        → sm_bp
```

---

## 四、数据模型

### 4.1 用户数据库（SQLite）

**文件**：`data/users.db`

**表结构**：

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL  -- SHA-256 哈希
);
```

**认证方式**：Session 式。
- 登录成功写 `session['user'] = username`
- 所有页面/API 入口通过 `require_auth()` 守卫
- 默认账号：`admin / admin123`

### 4.2 远程服务器记录（JSON）

**文件**：`data/sim-deployments.json`

```json
[
  {
    "id": "dep-abc123",
    "host": "192.168.1.100",
    "port": 22,
    "user": "root",
    "password": "******",
    "version": "v2.5.2-dev-17",
    "status": "running",
    "created_at": "2026-05-22T12:00:00",
    "last_seen": "2026-05-22T12:30:00"
  }
]
```

---

## 五、路由总表

### 5.1 认证（auth_bp）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/login` | 登录页 |
| GET/POST | `/register` | 注册页 |
| GET | `/logout` | 注销 |
| GET | `/` | 根路径（重定向到仪表盘或登录） |

### 5.2 仪表盘（dashboard_bp）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/dashboard` | 仪表盘主页（系统状态 + 工具卡片） |

**数据来源**：`os` 模块实时读取 — 磁盘用量、运行时间、文件计数

### 5.3 文件管理（fm_bp）

| 方法 | 路径 | 参数 | 说明 |
|---|---|---|---|
| GET | `/files` | `?path=/xxx` | 文件管理页面 |
| GET | `/api/files` | `?path=/xxx` | 列出目录内容（JSON） |
| POST | `/api/upload` | `path` + `files` | 上传文件 |
| GET | `/api/download` | `?path=/xxx/file` | 下载文件 |
| POST | `/api/delete` | `{"path": "..."}` | 删除文件/空目录 |
| GET | `/serve/<path>` | — | 直接提供 HTML 文件 |

**路径解析逻辑**：

```
用户输入 path → resolve_path() → os.path.normpath()
                                 → 必须以 / 开头
                                 → 不存在则回退到 /
```

### 5.4 模拟器管理（sm_bp）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/simulator` | 管理页面 |
| GET | `/api/simulator/status` | 本地模拟器状态（含 `host_ip`） |
| GET | `/api/simulator/versions` | 可用版本列表 |
| POST | `/api/simulator/deploy` | 本地部署 |
| POST | `/api/simulator/remote-deploy` | 远程部署 |
| GET | `/api/simulator/deploy-status/<id>` | 部署进度轮询 |
| POST | `/api/simulator/control` | 启动/停止/重启 |
| GET | `/api/simulator/backups` | 配置备份列表 |
| GET | `/api/simulator/remote-servers` | 远程服务器列表 |
| DELETE | `/api/simulator/remote-servers` | 删除远程记录 |
| POST | `/api/simulator/remote-check` | 检测远程服务器连通性 |

**部署流程（本地）**：

```
预检查(包存在/端口/磁盘)
  → 备份 config/
  → 停止服务 (bin/stop.sh)
  → 清理旧文件 (保留 backups/)
  → 解压 tar.gz (--strip-components=1)
  → 恢复配置
  → 启动服务 (bin/start.sh)
  → 验证 (API 200 + 实例数 + Web UI)
```

**远程部署**：通过 SSH/SCP 执行相同流程，密码存储在 `sim-deployments.json`

---

## 六、前端架构

### 6.1 模板继承

```
base.html                    ← 布局骨架（侧边栏 + 顶栏 + 内容区 + Toast）
├── login.html               ← 登录表单
├── register.html            ← 注册表单
├── dashboard.html           ← 统计卡片 + 工具网格 + 系统状态
├── file_manager.html        ← 路径输入 + 文件列表 + 上传区
└── simulator_manager.html   ← 状态卡片 + 版本表 + 部署进度 + 远程管理
```

### 6.2 导航结构

```
📊 仪表盘
📁 文件管理
🔌 模拟器管理
```

### 6.3 全局 UI 组件

- **暗色主题 CSS 变量** — 统一在 `base.html` 的 `:root` 中定义
- **Toast 通知** — `showToast(msg)` / `showNotice(msg)`，2 秒自动消失
- **Flash 消息** — 服务端 flash 消息，3 秒自动消失
- **响应式** — 900px 断点（侧边栏折叠为 icon），640px 断点（内容缩进）

### 6.4 交互模式

| 页面 | 实时更新方式 |
|---|---|
| 仪表盘 | 页面加载时渲染服务端数据 |
| 文件管理 | 页面加载 + 手动刷新 |
| 模拟器管理 | 状态 10s 轮询，远程服务器 30s 轮询，部署进度 800ms 轮询 |

---

## 七、部署

### 7.1 systemd 服务

```
/etc/systemd/system/egc-server.service
```

- Type: `simple`
- ExecStart: `python3 /root/EGC/run.py --port 8080`
- Restart: `on-failure`
- 开机自启：`systemctl enable egc-server.service`

### 7.2 手动启动

```bash
bash /root/EGC/start-server.sh
```

### 7.3 端口

| 端口 | 用途 |
|---|---|
| 8080 | Flask Web 管理面板 |
| 8989 | IEC104 模拟器 HTTP API（部署后） |
| 2404 | IEC104 模拟器协议端口（部署后） |

### 7.4 关键路径

| 路径 | 用途 |
|---|---|
| `/root/EGC/` | 项目根目录 |
| `/root/EGC/data/` | 用户 DB + 远程服务器记录 |
| `/root/IEC-SIM/iec104-sim-master/dist/` | 模拟器安装包源 |
| `/home/envuser/IEC/gridsim/` | 模拟器部署目标目录 |
| `/home/envuser/IEC/gridsim/backups/` | 配置备份目录 |

---

## 八、安全

| 领域 | 措施 |
|---|---|
| 认证 | Session + SHA-256 密码哈希 |
| 路径穿越 | `os.path.normpath` + 必须以 `/` 开头 |
| 文件上传 | `secure_filename` 过滤文件名 |
| API 守卫 | 所有 API 入口 `require_auth()` 检查 |
| 远程密码 | 明文存储在 `sim-deployments.json`（受登录认证保护） |

---

## 九、已知限制

1. **远程密码明文存储** — 当前受 UI 登录保护，无额外加密
2. **单用户** — SQLite 支持多用户，但 UI 未实现权限分级
3. **pip 不可用** — 无法安装新 Python 包，只能使用已安装的库
4. **删除仅支持空目录** — `os.rmdir` 要求目录为空
5. **部署日志内存存储** — `_deploy_tasks` 字典，服务重启后丢失
