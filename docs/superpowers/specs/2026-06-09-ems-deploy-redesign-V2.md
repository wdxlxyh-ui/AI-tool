# Edge-EMS 部署工具 — 重新设计方案

> 按组件拆分、下载与上传分离、交互优化

## 变更摘要

| 旧设计 | 新设计 |
|--------|--------|
| 单页面，component 下拉选择 | 3 个 Tab 子页面，各组件独立 |
| "开始部署"一步到底 | 分步：下载(Blob→本地) → 部署(本地→远程)，两步可选 |
| HMI-FE 有架构下拉框 | 去掉架构选择，服务器类型自动决定路径 (HPUY=logger, EE=app_portal) |
| 环境检查区块 | 删除，后端静默检查 |
| SAS Token 纯文本输入 | 连接配置面板：状态指示 + 分段输入 + 测试连接 |
| 单个历史表格 | 每个组件 Tab 各自的历史记录 |

## 架构

### Blob 路径模板（已确认）

```
edge-ems:        edgeftpfile/edge-ems/{branch}/{server_dir}/edge-ems.tar.gz
edge-ems-hmi:    edgeftpfile/edge-ems-hmi/{branch}/{server_dir}/edge-ems-hmi.tar.gz
edge-ems-hmi-fe: edgeftpfile/edge-ems-hmi-fe/{branch}/{server_dir}/edge-ems-hmi-fe.zip
                   HPUY → server_dir = HPUY/logger
                   EE   → server_dir = EE/app_portal
```

### 服务器部署路径

```
HPUY:
  edge-ems:       /root/EMS/edge-ems/
  edge-ems-hmi:   /root/EMS/edge-ems-hmi/
  edge-ems-hmi-fe: /root/EMS/edge-ems-hmi/edge-ems-hmi-fe/ 

EE:
  edge-ems:       /home/envuser/energy-os/edge-ems/
  edge-ems-hmi:   /home/envuser/energy-os/edge-ems-hmi/
  edge-ems-hmi-fe: /home/envuser/energy-os/edge-ems-hmi/edge-ems-hmi-fe/ 
```

把对应的压缩包放在上述路径解压

### 页面结构

一个导航入口 → 3 个 Tab

```
/ems-deploy  (主页面)
  ├── Tab: edge-ems        默认激活
  ├── Tab: edge-ems-hmi
  └── Tab: edge-ems-hmi-fe
```

### 单个组件 Tab 布局

```
┌─────────────────────────────────────────────────────┐
│  [⚙ 连接配置]                    配置状态: ●已连接  │
├─────────────────────────────────────────────────────┤
│  分支: [develop_2605 ▼]     服务器: [HPUY] [EE]    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  步骤 1: 从 Azure Blob 下载到本地                    │
│  ┌─────────────────────────────────────────────┐   │
│  │ Blob: edgeftpfile/.../develop_2605/.../xxx   │   │
│  │ 本地: /root/Blob/.../xxx                    │   │
│  │ 状态: ✅ 已存在 (234.5 MB) 2026-06-08        │   │
│  │                                [从 Blob 下载] │   │
│  └─────────────────────────────────────────────┘   │
│                      ↓                              │
│  步骤 2: 部署到远程服务器                            │
│  ┌─────────────────────────────────────────────┐   │
│  │ 目标: admin@192.168.1.100:22               │   │
│  │ 远程: /root/EMS/edge-ems/                │   │
│  │                                [部署到服务器]  │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌── 执行日志 ──────────────────────────────────┐   │
│  │ [10:30:01] 🚀 开始下载...                     │   │
│  │ [10:30:05] ✅ 下载完成 (234.5 MB)             │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  部署历史                                           │
│  时间 | 分支 | 服务器 | 操作 | 状态 | 耗时          │
└─────────────────────────────────────────────────────┘
```

### 连接配置面板（Modal）

```
┌─────────────────────────────────────────┐
│ 连接配置                          [×]   │
├─────────────────────────────────────────┤
│                                         │
│ Azure Blob 连接                         │
│ ┌─────────────────────────────────────┐ │
│ │ 账户: edgeadls2  (固定)             │ │
│ │ 容器: edge        (固定)             │ │ │
│ │ SAS Token:                         │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ sv=2021-06-08&ss=b&srt=sco&... │ │ │
│ │ │                                 │ │ │
│ │ └─────────────────────────────────┘ │ │
│ │ 从 Azure Portal → Storage Account  │ │
│ │ → edgeadls2 → Shared access        │ │
│ │ signature 生成                      │ │
│ │                         [测试连接]   │ │
│ │ 连接状态: ✅ 可连接                  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 本地镜像目录                            │
│ [/root/Blob/..../                    ]       │
│                                         │
│ HPUY 服务器                             │
│ Host [192.168.1.100] Port [22]       │
│ User [admin         ] PW   [••••••••]  │
│ 远程目录 [/root/EMS/                   ] │
│                                         │
│ EE 服务器                               │
│ Host [10.0.0.100  ] Port [22]       │
│ User [root         ] PW   [••••••••]  │
│ 远程目录 [/home/envuser/energy-os/    ] │
│                                         │
│              [取消] [保存配置]           │
└─────────────────────────────────────────┘
```

### 用户操作流程

**场景 A: develop 分支更新了，要部署到 HPUY**
1. 选择 edge-ems Tab → 选 develop_2605 → 选 HPUY
2. 点击 [从 Blob 下载] → 等待下载完成
3. 点击 [部署到服务器] → 等待部署完成

**场景 B: 包没更新，部署到一个新的 EE 服务器**
1. 选择 edge-ems Tab → 选 develop_2605 → 选 EE
2. 看到 "✅ 本地已存在 (234.5 MB)"
3. 直接点 [部署到服务器] → 跳过下载，直接部署

**场景 C: 只想下载到本地，不上传**
1. 点击 [从 Blob 下载] → 完成后不点第二步

## 后端 API

### 配置
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/ems-deploy/config` | 获取配置（密码脱敏） |
| POST | `/api/ems-deploy/config` | 保存配置 |
| POST | `/api/ems-deploy/test-blob` | 测试 Blob 连接 |

### Blob 操作
| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/ems-deploy/blob-info` | 检查组件 Blob 文件信息 |
| POST | `/api/ems-deploy/blob-download` | 下载 Blob 文件到本地 |

### 部署操作
| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/ems-deploy/deploy` | 从本地上传到远程服务器并解压 |

### 进度与历史
| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/ems-deploy/task-status/<task_id>` | 查询任务进度 |
| GET | `/api/ems-deploy/history/<component>` | 组件历史记录 |
| DELETE | `/api/ems-deploy/history/<component>/<id>` | 删除历史 |

### 页面
| Method | Path | 说明 |
|--------|------|------|
| GET | `/ems-deploy` | 主页面（含3个Tab） |

## 文件结构

```
app/
├── __init__.py              # 修改: 注册 ed_bp
├── ems_deploy.py            # 重写: 新API结构
├── ems_deploy_assets/       # 保留: blob_tool.py 等
├── templates/
│   ├── base.html            # 修改: 侧边栏
│   ├── dashboard.html       # 修改: 工具卡片
│   └── ems_deploy.html      # 重写: 新UI + 3 Tab
├── dashboard.py             # 修改: tool_count
data/
└── ems-deploy-config.json   # 运行时: 配置
└── ems-deploy-history.json  # 运行时: 历史
```

## 数据模型

### 配置 (ems-deploy-config.json)
```json
{
  "sas_token": "sv=2021-06-08...",
  "blob_account": "edgeadls2",
  "blob_container": "edge",
  "blob_mirror_dir": "/mnt/d/Blob",
  "servers": {
    "HPUY": {
      "ssh_user": "admin",
      "ssh_password": "...",
      "ssh_host": "192.168.1.100",
      "ssh_port": 9991,
      "deploy_dirs": {
        "edge-ems": "/root/EMS/",
        "edge-ems-hmi": "/root/EMS/",
        "edge-ems-hmi-fe": "/root/EMS/"
      }
    },
    "EE": {
      "ssh_user": "root",
      "ssh_password": "...",
      "ssh_host": "10.0.0.100",
      "ssh_port": 9991,
      "deploy_dirs": {
        "edge-ems": "/home/envuser/energy-os/",
        "edge-ems-hmi": "/home/envuser/energy-os/",
        "edge-ems-hmi-fe": "/home/envuser/energy-os/"
      }
    }
  }
}
```

### 历史 (ems-deploy-history.json)
```json
{
  "edge-ems": [
    {
      "id": "ems-abc123",
      "timestamp": "2026-06-09T10:30:00",
      "branch": "develop_2605",
      "server": "HPUY",
      "action": "download",
      "status": "completed",
      "duration_seconds": 45,
      "file_size": 234567890
    },
    {
      "id": "ems-def456",
      "timestamp": "2026-06-09T10:35:00",
      "branch": "develop_2605",
      "server": "HPUY",
      "action": "deploy",
      "status": "completed",
      "duration_seconds": 120
    }
  ],
  "edge-ems-hmi": [],
  "edge-ems-hmi-fe": []
}
```
