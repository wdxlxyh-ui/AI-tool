# Edge-EMS 部署工具集成方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 edge-ems-deploy-tool 集成到 EGC 工具管理器，提供 Web UI 进行配置管理、环境检查、Azure Blob 文件浏览和 Edge-EMS 组件部署。

**Architecture:** 新增一个 Flask Blueprint（`ems_deploy`），遵循现有 `simulator_manager.py` 的模式：后端用 threading + 内存任务字典实现异步部署进度追踪，前端用 Jinja2 模板 + vanilla JS 轮询 `/api/ems-deploy/deploy-status/<task_id>` 获取实时日志。部署逻辑调用 `main.py` CLI（通过 subprocess），Blob 操作复用 `blob_tool.py` 的 `AzureBlobClient` 类。

**Tech Stack:** Flask Blueprint, SQLite (JSON 文件存储配置), threading, subprocess, Jinja2, vanilla JS

---

## 关键问题：`main.py` 缺失

压缩包中没有 `main.py`（核心部署脚本），只有：
- `blob_tool.py` — Azure Blob 操作（可用）
- `check_environment.py` — 环境检查（可用）
- `.env.example` — 配置模板（可用）
- `scripts/*.sh` — 辅助脚本（可用）

**策略：** 后端 API 完整实现，但部署操作会检测 `main.py` 是否存在。若存在则调用 CLI 执行部署；若不存在则返回提示信息，其他功能（配置管理、环境检查、Blob 浏览、历史记录）正常工作。后续补充 `main.py` 后无需改代码即可启用部署功能。

---

## 文件结构

```
app/
├── __init__.py                  # [修改] 注册 ems_deploy_bp
├── ems_deploy.py                # [新建] 后端 Blueprint（核心）
├── ems_deploy_assets/           # [已复制] 工具资产文件
│   ├── blob_tool.py
│   ├── check_environment.py
│   ├── .env.example
│   └── scripts/
│       ├── check-before-deploy.sh
│       ├── verify-after-deploy.sh
│       └── rollback.sh
├── templates/
│   ├── base.html                # [修改] 侧边栏添加导航项
│   ├── dashboard.html           # [修改] 工具卡片
│   └── ems_deploy.html          # [新建] 前端页面
├── dashboard.py                 # [修改] tool_count + 1
data/
└── ems-deploy-config.json       # [运行时生成] 配置持久化
└── ems-deploy-history.json      # [运行时生成] 部署历史
```

---

## 现有代码模式参考（实现时必须严格遵循）

| 模式 | 来源 | 说明 |
|------|------|------|
| Blueprint 命名 | `sm_bp = Blueprint('simulator', __name__)` | `ed_bp = Blueprint('ems_deploy', __name__)` |
| 认证检查 | `if not require_auth(): return jsonify(...)` | 每个 route 都要检查 |
| 数据持久化 | JSON 文件 `load_servers()` / `save_servers()` | 配置和历史用 JSON 文件 |
| 异步任务 | `_deploy_tasks` dict + `_task_lock` + `_task_log()` | 复制同样的进度追踪模式 |
| 命令执行 | `sp.run(cmd, shell=True, ...)` + `_run_cmd()` | 用 subprocess 调用 |
| 前端轮询 | `setInterval` 轮询 `/api/.../deploy-status/<id>` | 同样的实时日志模式 |
| 导航集成 | `base.html` 侧边栏 + `dashboard.html` 工具卡片 | 添加新工具入口 |
| 页面模板 | `{% extends "base.html" %}` + `{% set active_page %}` | 复用 CSS 变量和组件 |

---

## API 设计

### 配置管理
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/ems-deploy/config` | 获取当前配置（密码脱敏） |
| POST | `/api/ems-deploy/config` | 保存配置 |
| POST | `/api/ems-deploy/check-env` | 执行环境检查 |

### Azure Blob
| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/ems-deploy/blob-check` | 检查 Blob 文件是否存在 |
| POST | `/api/ems-deploy/blob-list` | 列出 Blob 目录内容 |

### 部署操作
| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/ems-deploy/deploy` | 启动部署任务 |
| GET | `/api/ems-deploy/deploy-status/<task_id>` | 查询部署进度 |

### 部署历史
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/ems-deploy/history` | 获取历史记录 |
| DELETE | `/api/ems-deploy/history/<id>` | 删除历史记录 |

### 页面路由
| Method | Path | 说明 |
|--------|------|------|
| GET | `/ems-deploy` | 渲染主页面 |

---

## 页面布局设计（ems_deploy.html）

```
┌──────────────────────────────────────────────────┐
│ 环境状态                                          │
│ [SAS Token: ✓已配置] [HPUY: ✓已配置] [EE: ✓已配置] │
│ [环境检查] [配置]                                   │
├──────────────────────────────────────────────────┤
│ 部署配置                                          │
│ 分支: [develop_2605 ▼]  服务器: [HPUY/EE]         │
│ 组件: ☑ edge-ems  ☑ edge-ems-hmi  ☐ edge-ems-hmi-fe│
│ HMI-FE架构: [x86_64 ▼]   模式: ○完整 ○仅下载      │
│                              [开始部署]            │
├──────────────────────────────────────────────────┤
│ 部署进度（可折叠，部署时展开）                       │
│ ┌──────────────────────────────────────────────┐ │
│ │ [10:30:01] 🚀 开始部署 edge-ems → HPUY       │ │
│ │ [10:30:02] 📦 检查 Azure Blob 文件...         │ │
│ │ [10:30:05] ✅ 文件存在 (234.5MB)              │ │
│ │ ...                                          │ │
│ └──────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│ 部署历史                                          │
│ 时间 | 分支 | 服务器 | 组件 | 状态 | 操作          │
│ ───────────────────────────────────────────────── │
│ 10:30 | develop_2605 | HPUY | all | ✅成功 | [重试]│
│ 09:15 | develop_23   | EE   | hmi | ❌失败 | [重试]│
└──────────────────────────────────────────────────┘
```

---

## 配置数据模型（ems-deploy-config.json）

```json
{
  "sas_token": "sv=2021-06-08...",
  "blob_mirror_dir": "/mnt/d/Blob",
  "servers": {
    "HPUY": {
      "ssh_user": "admin",
      "ssh_password": "encrypted_or_plain",
      "ssh_host": "192.168.1.100",
      "ssh_port": 9991,
      "remote_base_dir": "/root/EMS/"
    },
    "EE": {
      "ssh_user": "root",
      "ssh_password": "encrypted_or_plain",
      "ssh_host": "10.0.0.100",
      "ssh_port": 9991,
      "remote_base_dir": "/home/envuser/energy-os/"
    }
  },
  "default_branch": "develop_2605",
  "branches": ["develop_23", "develop_24", "develop_25", "develop_2605"],
  "components": {
    "edge-ems": { "needs_config_xml_restore": true },
    "edge-ems-hmi": { "needs_config_xml_restore": false },
    "edge-ems-hmi-fe": { "needs_config_xml_restore": false, "archs": ["x86_64", "arm64"] }
  }
}
```

## 历史数据模型（ems-deploy-history.json）

```json
[
  {
    "id": "dep-abc12345",
    "timestamp": "2026-06-09T10:30:00",
    "branch": "develop_2605",
    "server": "HPUY",
    "component": "all",
    "hmi_fe_arch": "x86_64",
    "tar_only": false,
    "status": "completed",
    "log_file": "/tmp/edge-ems-deploy-logs/deploy_main_12345.log",
    "duration_seconds": 120
  }
]
```

---

## 实施任务

### Task 1: 创建后端 Blueprint — app/ems_deploy.py

**Files:**
- Create: `app/ems_deploy.py`

**功能模块：**

1. **配置管理** — `load_config()` / `save_config()` — 读写 `data/ems-deploy-config.json`
   - 初始化时如果文件不存在，从 `.env.example` 的结构创建默认配置
   - `GET /api/ems-deploy/config` — 返回配置，密码字段只显示前4位+`****`
   - `POST /api/ems-deploy/config` — 接收并保存配置，合并写入

2. **环境检查** — `POST /api/ems-deploy/check-env`
   - 导入 `check_environment.py` 的函数或直接调用 `python3 check_environment.py`
   - 返回检查结果 JSON

3. **Blob 操作** — `POST /api/ems-deploy/blob-check` 和 `POST /api/ems-deploy/blob-list`
   - 导入 `blob_tool.py` 的 `AzureBlobClient` 类
   - `blob-check`: 根据分支+服务器+组件构造 Blob 路径，检查文件是否存在
   - `blob-list`: 列出指定前缀下的文件列表

4. **部署执行** — `POST /api/ems-deploy/deploy`
   - 参数: branch, server, component, hmi_fe_arch, tar_only
   - 检查 `main.py` 是否存在于 `app/ems_deploy_assets/main.py`，不存在则返回错误提示
   - 存在则启动 threading.Thread 执行 `_deploy_thread()`
   - `_deploy_thread()` 调用 `python3 main.py --branch X --server Y --component Z ...`
   - 使用 `_task_log()` 记录每步进度（复用 simulator_manager 模式）

5. **进度查询** — `GET /api/ems-deploy/deploy-status/<task_id>`
   - 返回 `{ status, logs: [{time, msg}] }`

6. **历史记录** — `load_history()` / `save_history()` — 读写 `data/ems-deploy-history.json`
   - `GET /api/ems-deploy/history` — 返回列表
   - `DELETE /api/ems-deploy/history/<id>` — 删除单条

7. **页面路由** — `GET /ems-deploy` → `render_template('ems_deploy.html')`

**代码结构：**

```python
"""Edge-EMS Deploy Manager — configuration, Blob operations, deployment."""
import os, json, time, threading, subprocess as sp
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for,
                   request, jsonify, current_app

ed_bp = Blueprint('ems_deploy', __name__)

# 路径常量
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'ems_deploy_assets')
MAIN_SCRIPT = os.path.join(ASSETS_DIR, 'main.py')
CONFIG_FILE = '/root/EGC/data/ems-deploy-config.json'
HISTORY_FILE = '/root/EGC/data/ems-deploy-history.json'

# 组件定义
COMPONENTS = {
    'edge-ems': {'blob_path': 'edgeftpfile/edge-ems/{branch}/{server}/edge-ems.tar.gz', ...},
    'edge-ems-hmi': {...},
    'edge-ems-hmi-fe': {...},
}

# 线程安全的任务进度存储（复用 simulator_manager 模式）
_deploy_tasks = {}
_task_lock = threading.Lock()

def _task_log(task_id, msg, status='running'): ...
def _run_cmd(cmd, task_id, timeout=30): ...
def load_config(): ...
def save_config(config): ...
def load_history(): ...
def save_history(history): ...

# 所有路由...
```

- [ ] **Step 1:** 创建 `app/ems_deploy.py`，实现配置管理（load/save config）和页面路由
- [ ] **Step 2:** 实现 Blob 操作 API（blob-check, blob-list）
- [ ] **Step 3:** 实现环境检查 API
- [ ] **Step 4:** 实现部署执行逻辑（_deploy_thread + deploy API + deploy-status API）
- [ ] **Step 5:** 实现历史记录 API
- [ ] **Step 6:** 语法检查，确保无误

---

### Task 2: 注册 Blueprint — app/__init__.py

**Files:**
- Modify: `app/__init__.py:17-29`

在 `create_app()` 中添加：
```python
from .ems_deploy import ed_bp
app.register_blueprint(ed_bp)
```

- [ ] **Step 1:** 添加 import 和 register_blueprint 调用
- [ ] **Step 2:** 验证 app 可以启动

---

### Task 3: 添加侧边栏导航 — app/templates/base.html

**Files:**
- Modify: `app/templates/base.html:186-194`

在 "工具" nav-section 中，`simulator` 之后、`sftp` 之前添加：
```html
<a class="nav-item {% if active_page == 'ems_deploy' %}active{% endif %}" href="{{ url_for('ems_deploy.index') }}">
  <span class="icon">⬡</span><span>Edge-EMS 部署</span>
</a>
```

- [ ] **Step 1:** 添加导航项

---

### Task 4: 添加仪表盘工具卡片 — app/templates/dashboard.html

**Files:**
- Modify: `app/templates/dashboard.html:67-70`

在模拟器管理卡片之后添加 Edge-EMS 部署卡片：
```html
<a class="tool-card" href="{{ url_for('ems_deploy.index') }}">
  <div class="icon" style="background:rgba(83,155,245,.1);color:#539bf5;">⬡</div>
  <h3>Edge-EMS 部署</h3>
  <p>Edge-EMS 组件自动化部署。支持 HPUY/EE 服务器，多分支多组件配置。</p>
  <div class="footer"><span class="dot on"></span> 已集成</div>
</a>
```

- [ ] **Step 1:** 添加工具卡片

---

### Task 5: 更新工具计数 — app/dashboard.py

**Files:**
- Modify: `app/dashboard.py:57`

将 `stats['tool_count'] = 6` 改为 `stats['tool_count'] = 7`

- [ ] **Step 1:** 更新计数

---

### Task 6: 创建前端模板 — app/templates/ems_deploy.html

**Files:**
- Create: `app/templates/ems_deploy.html`

**页面结构（4个区块）：**

#### 区块1: 环境状态栏
- 3个 stat-card 显示 SAS Token、HPUY 凭据、EE 凭据的配置状态
- 按钮: [环境检查] [配置]
- 点击"配置"打开 modal 弹窗，包含所有配置项的表单

#### 区块2: 部署配置
- 分支选择（dropdown，可自定义输入）
- 服务器类型（radio: HPUY / EE）
- 组件选择（checkbox: edge-ems / edge-ems-hmi / edge-ems-hmi-fe / 全部）
- HMI-FE 架构（conditional dropdown: x86_64 / arm64）
- 部署模式（radio: 完整部署 / 仅下载到本地）
- [检查Blob文件] 按钮 — 调用 blob-check API
- [开始部署] 按钮

#### 区块3: 部署进度（terminal 样式，默认折叠）
- 复用 `base.html` 中 `.terminal` 的样式
- 实时日志输出（轮询 deploy-status API）
- 完成后显示耗时和状态

#### 区块4: 部署历史（data-table）
- 列: 时间、分支、服务器、组件、模式、状态、耗时、操作
- 状态 badge: ✅成功(绿) / ❌失败(红) / ⚠️警告(黄)
- 操作: [重试] [删除]
- 空状态显示"暂无部署记录"

#### 配置 Modal
- SAS Token 输入框（password type）
- Blob 镜像目录输入框
- HPUY 服务器配置（host, port, user, password, remote_dir）
- EE 服务器配置（host, port, user, password, remote_dir）
- 保存/取消按钮

**JS 逻辑：**
- `loadConfig()` — 加载配置并更新 UI 状态
- `saveConfig()` — 保存配置
- `checkEnv()` — 环境检查
- `checkBlob()` — 检查 Blob 文件
- `startDeploy()` — 启动部署
- `pollProgress(taskId)` — 轮询进度
- `loadHistory()` — 加载历史记录
- `retryDeploy(id)` — 从历史记录重试
- `deleteHistory(id)` — 删除历史

- [ ] **Step 1:** 创建 HTML 骨架，继承 base.html
- [ ] **Step 2:** 实现区块1 环境状态栏
- [ ] **Step 3:** 实现区块2 部署配置表单
- [ ] **Step 4:** 实现区块3 部署进度终端
- [ ] **Step 5:** 实现区块4 部署历史表格
- [ ] **Step 6:** 实现配置 Modal 弹窗
- [ ] **Step 7:** 实现 JS 逻辑（所有 API 调用和交互）

---

### Task 7: 端到端验证

- [ ] **Step 1:** 启动 Flask app (`python run.py`)
- [ ] **Step 2:** 访问 `/ems-deploy`，确认页面正常渲染
- [ ] **Step 3:** 测试配置保存/加载
- [ ] **Step 4:** 测试环境检查
- [ ] **Step 5:** 确认仪表盘和侧边栏导航正常

---

## 风险和注意事项

1. **main.py 缺失** — 部署功能会提示"核心脚本 main.py 未找到"，其他功能正常
2. **密码安全** — 配置中的密码以明文存储在 JSON 文件中（与现有 sftp_manager、simulator_manager 模式一致）
3. **线程安全** — 复用 simulator_manager 的 `_task_lock` 模式
4. **依赖** — `blob_tool.py` 需要 `requests` 库，需确认已在 requirements.txt 中（当前只有 flask + werkzeug）
5. **requirements.txt** — 需要添加 `requests>=2.31.0`

---

## 自检清单

- [x] 每个 Task 都有明确的文件路径
- [x] API 设计覆盖所有用户场景
- [x] 前端布局与现有工具一致
- [x] 复用现有代码模式（Blueprint, threading, JSON storage, terminal polling）
- [x] 处理 main.py 缺失的情况
- [x] 导航集成（侧边栏 + 仪表盘）
- [x] 无 placeholder — 所有步骤都有具体实现说明
