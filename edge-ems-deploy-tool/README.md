# Edge-EMS 程序包部署工具

自动化部署 Edge-EMS 组件（edge-ems / edge-ems-hmi / edge-ems-hmi-fe）到目标服务器的完整解决方案。

## 功能特性

### 核心功能
- ✅ **一键部署**：支持 HPUY / EE 两类服务器
- ✅ **多组件支持**：edge-ems / edge-ems-hmi / edge-ems-hmi-fe
- ✅ **自动识别架构**：HMI-FE 支持 x86_64 / arm64
- ✅ **完整流程**：Azure Blob → 本地镜像 → 目标服务器 → 解压 → 权限修复
- ✅ **测试模式**：仅下载到本地镜像，不上传到服务器
- ✅ **详细日志**：记录每个步骤的操作和结果

### 安全特性
- 🔒 随机日志文件命名（避免日志泄露）
- 🔒 环境变量隔离（SAS 令牌存储在 .env）
- 🔒 权限修复（HPUY: root:root, EE: envuser:envuser）
- 🔒 config.xml 恢复（自动检查并复制生产配置）

## 目录结构

```
edge-ems-deploy-tool/
├── main.py                 # 主部署脚本
├── blob_tool.py            # Azure Blob 工具
├── requirements.txt        # Python 依赖
├── .env.example            # 环境配置示例
├── README.md               # 说明文档
├── docs/
│   ├── azure-blob-setup.md    # Azure Blob SAS 令牌获取
│   ├── setup-guide.md         # 详细安装配置指南
│   └── troubleshooting.md     # 常见问题排查
└── scripts/
    ├── check-before-deploy.sh   # 部署前检查脚本
    ├── verify-after-deploy.sh  # 部署后验证脚本
    └── rollback.sh              # 快速回滚脚本
```

## 快速开始

### 1. 环境准备

#### 1.1 安装依赖

```bash
# 创建虚拟环境（可选）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 win_activate 如果是 Windows

# 安装 Python 依赖
pip install -r requirements.txt
```

#### 1.2 配置环境变量

```bash
# 复制配置示例文件
cp .env.example .env

# 编辑 .env 文件，填写实际配置
vim .env
```

`.env` 文件配置说明：

```bash
# Azure Blob SAS 令牌（必填）
AZURE_BLOB_SAS_TOKEN=your-sas-token-here

# 本地镜像目录
BLOB_MIRROR_DIR=/mnt/d/Blob

# 服务器凭据
HPUY_SSH_HOST=xxx.xxx.xxx.xxx
HPUY_SSH_PASSWORD=YourPassword

EE_SSH_HOST=yyy.yyy.yyy.yyy
EE_SSH_PASSWORD=YourPassword
```

#### 1.3 准备本地镜像目录

```bash
# 确保本地镜像目录存在
mkdir -p /mnt/d/Blob

# 验证目录权限
ls -la /mnt/d/Blob
```

### 2. 环境验证

运行环境检查脚本：

```bash
python main.py --check-env
```

或手动检查：

```bash
python main.py --help
```

### 3. 方式一：完整部署（推荐）

```bash
# 部署所有组件到 HPUY 服务器
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all

# 部署所有组件到 EE 服务器
python main.py \
    --branch develop_2605 \
    --server EE \
    --component all
```

部署流程：
1. 从 Azure Blob 下载程序包到本地镜像
2. 上传到目标服务器
3. 自动解压
4. 恢复 config.xml（如果需要）
5. 修复文件权限
6. 记录详细日志

### 4. 方式二：仅下载到本地镜像（测试用）

```bash
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all \
    --tar-only
```

输出示例：
```
✅ 部署阶段完成（仅下载到本地镜像）
✅ 得到本地文件: /mnt/d/Blob/edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz
💡 提示: 使用 --server 和 --component 参数上传到服务器
```

### 5. 方式三：部署特定组件

```bash
# 仅部署 edge-ems
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems

# 仅部署 edge-ems-hmi-fe (x86_64 架构)
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems-hmi-fe \
    --hmi-fe-arch x86_64

# 仅部署 edge-ems-hmi-fe (arm64 架构)
python main.py \
    --branch develop_2605 \
    --server EE \
    --component edge-ems-hmi-fe \
    --hmi-fe-arch arm64
```

### 6. 方式四：使用本地已有文件（跳过下载）

```bash
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems \
    --no-download
```

### 7. 方式五：验证部署结果

使用验证脚本：

```bash
bash scripts/verify-after-deploy.sh --server HPUY
```

或手动验证：

```bash
# 连接服务器
ssh admin@<HPUY_IP> -p 9991

# 检查版本
echo "EdgeLoggerSys@1024" | sudo -S cat /root/EMS/edge-ems/bin/VERSION

# 检查进程
echo "EdgeLoggerSys@1024" | sudo -S ps aux | grep edge-ems

# 检查日志（无错误）
echo "EdgeLoggerSys@1024" | sudo -S tail -n 50 /root/EMS/edge-ems/logs/adapter.log
```

## 命令参数说明

### 主命令

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--branch` | ✅ | 分支名称 | `develop_2605` |
| `--server` | ✅ | 服务器类型 | `HPUY` / `EE` |
| `--component` | ✅ | 组件名称或 all | `all` / `edge-ems` / `edge-ems-hmi` / `edge-ems-hmi-fe` |

### 可选参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--hmi-fe-arch` | HMI-FE 架构类型 | `x86_64` / `arm64` |
| `--tar-only` | 仅下载到本地镜像，不上传 | `--tar-only` |
| `--no-download` | 跳过下载，使用本地已有文件 | `--no-download` |
| `--skip-upload` | 下载后跳过上传到服务器 | `--skip-upload` |

## 配置说明

### Azure Blob SAS 令牌配置

**获取 SAS 令牌教程：**

1. 登录 Azure Portal：https://portal.azure.com
2. 搜索 "Storage Account"
3. 找到 `edgeadls2`
4. 进入 "Containers" → "edge"
5. 点击 "Settings" → "Shared access signature"
6. 设置权限：
   - ✅ Read
   - ✅ List
7. 选择过期时间（推荐 1 年）
8. 点击 "Generate SAS token and connection string"
9. 复制 "SAS token" 部分

**复制到 .env 文件：**

```bash
AZURE_BLOB_SAS_TOKEN=sv=2021-06-08...（后面的字符串）
```

### 服务器凭据配置

**HPUY 服务器（示例）：**

```bash
HPUY_SSH_USER=admin
HPUY_SSH_PASSWORD=EdgeLoggerSys@1024
HPUY_SSH_HOST=192.168.1.100
HPUY_SSH_PORT=9991
HPUY_REMOTE_BASE_DIR=/root/EMS/
```

**EE 服务器（示例）：**

```bash
EE_SSH_USER=root
EE_SSH_PASSWORD=En&vi0n!#%
EE_SSH_HOST=10.0.0.100
EE_SSH_PORT=9991
EE_REMOTE_BASE_DIR=/home/envuser/energy-os/
```

## 常见问题排查

### 1. 下载失败：找不到本地下⽂件

**原因：** 本地镜像目录不存在或路径配置错误

**解决：**
```bash
# 检查本地镜像目录
ls -la /mnt/d/Blob

# 如果不存在，创建目录
mkdir -p /mnt/d/Blob

# 或修改 .env 中的 BLOB_MIRROR_DIR
```

### 2. 下载失败：AZURE_BLOB_SAS_TOKEN 未设置

**原因：** 环境变量未配置

**解决：**
```bash
# 方法一：临时设置
export AZURE_BLOB_SAS_TOKEN=your-sas-token

# 方法二：永久设置（写入 .bashrc 或 .zshrc）
echo "export AZURE_BLOB_SAS_TOKEN=your-sas-token" >> ~/.bashrc
source ~/.bashrc

# 方法三：使用 .env 文件（推荐）
cp .env.example .env
vim .env
# 填写实际的 SAS 令牌
```

### 3. 上传失败：SSH 连接失败

**原因：** SSH 地址、端口或凭据错误

**解决：**
```bash
# 测试 SSH 连接
ssh admin@<HPUY_IP> -p 9991

# 如果需要密码跳板机
# 请在 .env 中配置跳板机信息
```

### 4. 解压失败：权限不足

**原因：** HPUY 服务器需要 sudo 权限

**解决：** 工具已自动处理 sudo 权限，确认 .env 中密码正确即可

### 5. config.xml 恢复失败

**原因：** root 目录不存在 config.xml

**解决：** 工具已自动检查文件存在性，不存在时跳过复制

### 6. HMI-FE 上传失败

**原因：** 文件格式为 ZIP 而非 TAR.GZ

**解决：** 工具已自动识别 ZIP 格式，使用 unzip 命令解压

## 日志查看

### 自动生成日志位置

```bash
/tmp/edge-ems-deploy-logs/deploy_<script_name>_<pid>.log
```

### 查看最新日志

```bash
# 找到最新日志文件
ls -lt /tmp/edge-ems-deploy-logs/*.log | head -1

# 查看日志内容
tail -f /tmp/edge-ems-deploy-logs/xxx.log

# 搜索错误信息
grep "❌" /tmp/edge-ems-deploy-logs/*.log

# 统计成功/失败次数
grep "✅ 成功" /tmp/edge-ems-deploy-logs/*.log | wc -l
grep "❌ 失败" /tmp/edge-ems-deploy-logs/*.log | wc -l
```

## 开发者说明

### 代码结构

- `main.py`：主部署入口，包含主要逻辑
- `blob_tool.py`：Azure Blob 操作工具
- `requirements.txt`：Python 依赖包
- `.env.example`：环境配置模板

### 核心流程

1. **环境验证**：检查 Python 版本、依赖包、SAS 令牌
2. **文件检查/下载**：从 Azure Blob 下载到本地镜像
3. **服务器连接**：建立 SSH 连接
4. **文件上传**：使用 curl 上传文件到服务器
5. **解压操作**：根据文件类型（TAR.GZ / ZIP）解压
6. **config.xml 恢复**：检查并复制生产配置（如果存在）
7. **权限修复**：修复文件所有者权限
8. **日志记录**：记录所有操作和结果

### 扩展建议

**添加新组件：**

1. 在 `COMPONENTS` 字典中添加配置
2. 指定 Blob 路径、远程目录、文件类型
3. 确认是否需要恢复 config.xml

**添加新服务器类型：**

1. 在 `SERVER_CREDENTIALS` 字典中添加凭据
2. 指定远程目录路径和权限策略
3. 测试部署流程

## 安全建议

1. **不要提交 .env 文件到 Git**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **定期更新 SAS 令牌**
   - SAS 令牌有有效期限
   - 过期后需要重新获取

3. **控制好服务器访问权限**
   - 使用最小权限原则
   - 定期更换SSH密码

4. **备份重要配置**
   ```bash
   # 上传前备份当前位置
   tar -czf edge-ems-backup-$(date +%Y%m%d).tar.gz /root/EMS/edge-ems/bin
   ```

## 许可证

本项目仅供内部使用。

## 联系方式

如遇到问题，请联系维护团队。

## 更新日志

### v1.0.0 (2026-06-09)
- ✅ 初始版本
- ✅ 支持完整部署流程
- ✅ 支持 tar-only 模式
- ✅ 支持多组件部署
- ✅ 支持多架构 HMI-FE
- ✅ 完整的日志记录
- ✅ 自动权限修复
- ✅ config.xml 恢复
