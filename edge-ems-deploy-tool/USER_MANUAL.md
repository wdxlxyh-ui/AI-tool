# Edge-EMS 部署工具 - 使用手册

## 📦 快速目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [详细安装步骤](#详细安装步骤)
- [命令行使用](#命令行使用)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [故障排查](#故障排查)

---

## 🚀 快速开始

### 最小配置步骤

```bash
# 1. 解压部署工具
tar -xzf edge-ems-deploy-tool.tar.gz
cd edge-ems-deploy-tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 .env 文件（重点！）
cp .env.example .env
vim .env
# 填写实际的 Azure SAS 令牌和服务器密码

# 4. 运行环境检查
python check_environment.py

# 5. 测试下载（不上传）
python main.py --branch develop_2605 --server HPUY --component all --tar-only

# 6. 完整部署
python main.py --branch develop_2605 --server HPUY --component all
```

---

## 🔧 环境要求

### 操作系统

- **推荐**：Ubuntu 20.04+ / Debian 10+ / CentOS 7+
- **WSL2**：Windows 10+ 和 Linux 子系统
- **Python 版本**：3.8+（必须）

### 依赖包

| 包名 | 版本 | 用途 |
|------|------|------|
| requests | >= 2.31.0 | HTTP 请求 |
| curl | - | 文件下载 |
| ssh | - | SSH 连接 |

### 检查项目是否就绪

```bash
# 检查所有依赖
python check_environment.py

# 如果看到 ✅ 所有检查通过，说明环境可以启动部署
```

---

## 📋 详细安装步骤

### 步骤 1：安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 win_activate（Windows）

# 安装依赖
pip install -r requirements.txt
```

### 步骤 2：配置 Azure Blob SAS 令牌

#### 2.1 登录 Azure Portal

1. 打开浏览器：https://portal.azure.com
2. 搜索 "Storage Account"
3. 找到 `edgeadls2`
4. 进入容器：Containers → Edge → `edge` 容器

#### 2.2 生成 SAS 令牌

1. 点击容器旁边的 **"Settings"**
2. 选择 **"Shared access signature"**
3. 勾选权限：
   - ✅ Read（读取）
   - ✅ List（列出）
4. 设置过期时间：1 年
5. 点击 **"Generate SAS token and connection string"**
6. 复制 **"SAS token"** 部分

#### 2.3 配置到 .env 文件

```bash
# 复制示例配置
cp .env.example .env

# 编辑
vim .env
```

填入 SAS 令牌：

```bash
# 不要在前面加 "sv=" 或 "?"
AZURE_BLOB_SAS_TOKEN=sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

### 步骤 3：配置服务器凭据

打开 `.env` 文件，配置以下内容：

#### HPUY 服务器

```bash
HPUY_SSH_USER=admin
HPUY_SSH_PASSWORD=EdgeLoggerSys@1024
HPUY_SSH_HOST=192.168.1.100
HPUY_SSH_PORT=9991
```

#### EE 服务器

```bash
EE_SSH_USER=root
EE_SSH_PASSWORD=En&vi0n!#%
EE_SSH_HOST=10.0.0.100
EE_SSH_PORT=9991
```

### 步骤 4：验证配置

```bash
# 检查 Azure Blob 连接
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"

# 应该看到：✅ 文件存在
```

---

## 👨‍💻 命令行使用

### 基本语法

```bash
python main.py \
    --branch <分支名> \
    --server <服务器类型> \
    --component <组件名>
```

### 完整参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--branch` | ✅ | 分支名称 | `develop_2605` |
| `--server` | ✅ | 服务器类型 | `HPUY` / `EE` |
| `--component` | ✅ | 组件名称 | `all` / `edge-ems` / `edge-ems-hmi` / `edge-ems-hmi-fe` |
| `--hmi-fe-arch` | - | HMI-FE 架构 | `x86_64` / `arm64` |
| `--tar-only` | - | 仅下载到本地 | `--tar-only` |
| `--no-download` | - | 跳过下载 | `--no-download` |
| `--skip-upload` | - | 跳过上传 | `--skip-upload` |

### 常用命令

#### 1. 完整部署（推荐）

```bash
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all
```

#### 2. 仅下载（测试用）

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
💡 提示: 使用 --server 参数上传到服务器
```

#### 3. 部署特定组件

```bash
# 仅部署 edge-ems
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems

# 仅部署 edge-ems-hmi-fe (x86_64)
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems-hmi-fe \
    --hmi-fe-arch x86_64

# 仅部署 edge-ems-hmi-fe (arm64)
python main.py \
    --branch develop_2605 \
    --server EE \
    --component edge-ems-hmi-fe \
    --hmi-fe-arch arm64
```

#### 4. 使用本地文件（跳过下载）

```bash
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component edge-ems \
    --no-download
```

---

## ⚙️ 配置说明

### 核心配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `BLOB_MIRROR_DIR` | 本地镜像目录 | `/mnt/d/Blob` |
| `HPUY_SSH_HOST` | HPUY 服务器 IP | `192.168.1.100` |
| `HPUY_SSH_PASSWORD` | HPUY 服务器密码 | `EdgeLoggerSys@1024` |
| `EE_SSH_HOST` | EE 服务器 IP | `10.0.0.100` |
| `EE_SSH_PASSWORD` | EE 服务器密码 | `En&vi0n!#%` |

### 多环境配置

可以在不同场景使用不同的配置：

### 场景 1：生产环境部署

```bash
# .env
AZURE_BLOB_SAS_TOKEN=production-sas-token
HPUY_SSH_PASSWORD=production-password
```

### 场景 2：测试环境部署

```bash
# .env
AZURE_BLOB_SAS_TOKEN=test-sas-token
HPUY_SSH_PASSWORD=test-password
```

---

## ❓ 常见问题

### Q1: 下载失败 - 找不到本地下⽂件

**错误信息**：
```
❌ 本地文件不存在: /mnt/d/Blob/edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz
```

**解决**：
```bash
# 检查目录是否存在
ls -la /mnt/d/Blob

# 创建目录
mkdir -p /mnt/d/Blob

# 或修改 .env 中的 BLOB_MIRROR_DIR
BLOB_MIRROR_DIR=/home/yuhangtian/BlobMirror
```

### Q2: 下载失败 - AZURE_BLOB_SAS_TOKEN 未设置

**错误信息**：
```
❌ AZURE_BLOB_SAS_TOKEN 未设置
   请运行: export AZURE_BLOB_SAS_TOKEN='your-sas-token'
```

**解决**：
```bash
# 方法一：临时设置
export AZURE_BLOB_SAS_TOKEN=your-sas-token
python main.py --branch develop_2605 --server HPUY --component all

# 方法二：永久设置（推荐）
echo "export AZURE_BLOB_SAS_TOKEN=your-sas-token" >> ~/.bashrc
source ~/.bashrc

# 方法三：使用 .env 文件
cp .env.example .env
vim .env
# 填写实际的 SAS 令牌
```

### Q3: 上传失败 - SSH 连接超时

**错误信息**：
```
❌ SSH 连接失败
```

**解决**：
```bash
# 测试 SSH 连接
ssh admin@<HPUY_IP> -p 9991

# 如果需要跳板机，请配置跳板机信息
```

### Q4: 解压失败 - 权限不足

**错误信息**：
```
❌ 权限不足
```

**解决**：
- 工具已自动处理 sudo 权限
- 确认 .env 中密码正确即可
- 无需手动操作

### Q5: HMI-FE 上传失败

**原因**：文件格式为 ZIP 而非 TAR.GZ

**解决**：工具已自动识别并使用 unzip 命令即可，无需手动操作

---

## 🔍 故障排查

### 检查清单

1. ✅ 检查 Python 版本 >= 3.8
2. ✅ 安装依赖包：`pip install requests`
3. ✅ 设置 AZURE_BLOB_SAS_TOKEN
4. ✅ 检查服务器凭据配置
5. ✅ 测试 Azure Blob 连接
6. ✅ 测试 SSH 连接
7. ✅ 检查本地镜像目录权限

### 日志查看

```bash
# 查找最新日志文件
ls -lt /tmp/edge-ems-deploy-logs/*.log | head -1

# 查看日志内容
tail -f /tmp/edge-ems-deploy-logs/xxx.log

# 搜索错误
grep "❌" /tmp/edge-ems-deploy-logs/*.log

# 统计成功/失败次数
grep "✅ 成功" /tmp/edge-ems-deploy-logs/*.log | wc -l
grep "❌ 失败" /tmp/edge-ems-deploy-logs/*.log | wc -l
```

### 详细错误诊断

```bash
# 1. 运行环境检查
python check_environment.py

# 2. 测试 Azure Blob 连接
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"

# 3. 测试 SSH 连接
ssh admin@<HPUY_IP> -p 9991
```

---

## 📞 获取帮助

### 文档资源

- [用户使用指南](README.md) - 完整的使用说明
- [Azure Blob 配置教程](docs/azure-blob-setup.md) - SAS 令牌获取详细步骤
- [安装配置指南](docs/setup-guide.md) - 详细安装流程
- [前端开发指南](FRONTEND_GUIDE.md) - 如需集成到平台，参考此文档
- [故障排查](docs/troubleshooting.md) - 常见问题和解决方案

### 运行诊断

```bash
# 快速检查所有内容
python check_environment.py

# 运行部署前检查
bash scripts/check-before-deploy.sh

# 查看详细日志
tail -f /tmp/edge-ems-deploy-logs/*.log
```

---

## ✅ 确认部署成功

### 验证步骤

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

### 配置检查

```bash
# 检查文件权限
echo "EdgeLoggerSys@1024" | sudo -S ls -la /root/EMS/edge-ems/bin/

# 检查 bin/config.xml 是否存在
echo "EdgeLoggerSys@1024" | sudo -S ls /root/EMS/edge-ems/bin/config.xml

# 抽查配置内容
echo "EdgeLoggerSys@1024" | sudo -S grep -c "<controller>" /root/EMS/edge-ems/bin/config.xml
# 应该输出：3 或更多
```

---

## 🎯 高级用法

### 并行部署多个服务器

```bash
# 终端 1：部署 HPUY
python main.py --branch develop_2605 --server HPUY --component all

# 终端 2：部署 EE
python main.py --branch develop_2605 --server EE --component all
```

### 自动化部署流程

```bash
#!/bin/bash
# deploy-all.sh

BRANCH="develop_2605"

echo "部署 HPUY..."
python main.py --branch $BRANCH --server HPUY --component all

echo "部署 EE..."
python main.py --branch $BRANCH --server EE --component all

echo "部署完成"
```

### 部署自述文件

每次部署后创建记录：

```bash
# 创建部署记录
cat >> /tmp/deploy-logs.md << EOF
---
timestamp: $(date "+%Y-%m-%d %H:%M:%S")
branch: $BRANCH
server: HPUY
status: success
components: all
---
EOF
```

---

## 📊 性能优化建议

### 1. 本地带宽优化

```bash
# 使用 zstd 压缩（支持的服务器）
# 修改 download_to_local 函数中的 curl 命令

# 使用 rsync 增量同步（第二次部署）
rsync -avz --progress /mnt/d/Blob/ root@server:/tmp/
```

### 2. CDN 加速

如果 Azure Blob 访问慢：
- 使用 Azure CDN 加速
- 在本地镜像服务器上缓存文件
- 指定国内节点下载

### 3. 并行下载

安装 aria2c 并用于并行下载：

```bash
# Ubuntu/Debian
sudo apt install aria2

# 修改 download_to_local 函数使用 aria2
aria2c -x 16 -s 16 -k 1M --async-dns=true "$blob_url" -o "$local_path"
```

---

## ⚠️ 安全提醒

1. **不要提交 .env 文件到 Git**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **定期更新 SAS 令牌**
   - SAS 令牌有有效期
   - 过期后需要重新获取

3. **控制 SSH 密码权限**
   - 使用最小权限原则
   - 定期更换密码

4. **备份重要配置**
   ```bash
   # 上传前备份当前位置
   tar -czf edge-ems-backup-$(date +%Y%m%d).tar.gz /root/EMS/edge-ems/bin
   ```

---

## 🎉 总结

现在你可以使用 Edge-EMS 部署工具了！

**快速测试：**
```bash
python main.py --branch develop_2605 --server HPUY --component all --tar-only
```

**完整部署：**
```bash
python main.py --branch develop_2605 --server HPUY --component all
```

祝部署顺利！🚀
