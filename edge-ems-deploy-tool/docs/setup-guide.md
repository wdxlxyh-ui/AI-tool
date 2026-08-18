# 详细安装配置指南

## 前置条件

### 操作系统要求

- **推荐**：Ubuntu 20.04 或更高版本
- **备用**：Debian 10+、CentOS 7+、WSL2
- **最小要求**：Linux 内核 5.0+

### 依赖包检查

#### 1. Python 3.8+

```bash
# 检查 Python 版本
python3 --version

# 如果版本过低，使用包管理器升级
sudo apt update
sudo apt install python3.10 python3-pip
```

#### 2. curl

通常 Linux 系统已内置：

```bash
# 检查 curl
curl --version

# Ubuntu/Debian 安装
sudo apt install curl

# CentOS/RHEL 安装
sudo yum install curl
```

#### 3. pip（Python 包管理器）

```bash
# 升级 pip
pip3 install --upgrade pip
```

## 详细安装步骤

### 方式一：标准安装（推荐）

**适用于：Ubuntu/Debian 系统**

```bash
# 1. 创建项目目录
cd ~
git clone <your-repo-url> edge-ems-deploy-tool

# 2. 进入项目目录
cd edge-ems-deploy-tool

# 3. 创建虚拟环境（推荐）
python3 -m venv venv

# 4. 激活虚拟环境
source venv/bin/activate

# 5. 安装依赖包
pip install -r requirements.txt

# 6. 复制配置文件
cp .env.example .env

# 7. 配置 .env 文件
vim .env

# 8. 生成项目文件中的完整 SAS 令牌（下一章说明）
vim .env
```

### 方式二：无需虚拟环境（快速测试）

```bash
# 1. 克隆或下载项目
cd ~
git clone <your-repo-url> edge-ems-deploy-tool
cd edge-ems-deploy-tool

# 2. 直接安装依赖
pip install -r requirements.txt

# 3. 复制配置文件
cp .env.example .env

# 4. 配置 .env 文件
vim .env
```

### 方式三：WSL2 安装

**适用于：Windows 用户运行 WSL2**

```bash
# 1. 在 WSL2 终端中安装
# Ubuntu/Debian 版本
sudo apt update
sudo apt install python3.10 python3-pip curl git

# 2. 创建项目目录
cd /mnt/d/          # 或其他你想存放项目的盘符
git clone <your-repo-url> edge-ems-deploy-tool

# 3. 进入项目目录
cd edge-ems-deploy-tool

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 配置 .env
cp .env.example .env
vim .env
```

## Azure Blob SAS 令牌配置（关键步骤）

这部分需要你手动操作 Azure Portal，获取 SAS 令牌。

### 步骤 1：登录 Azure Portal

1. 打开浏览器访问：https://portal.azure.com
2. 登录你的 Azure 账号

### 步骤 2：打开 Blob 容器

1. 顶部搜索框输入：`Storage Account`
2. 点击进入你的存储账户（edgeadls2）
3. 左侧菜单点击 **"Containers"**
4. 进入名为 `edge` 的容器
5. 点击容器进入

### 步骤 3：生成 SAS 令牌

1. 点击容器上方的 **"Settings"**
2. 选择 **"Shared access signature"**
3. 勾选权限：
   - ✅ Read
   - ✅ List
4. 设置过期时间：1 年
5. 点击 **"Generate SAS token and connection string"**

### 步骤 4：填写 .env 文件

打开 .env 文件，找到 `AZURE_BLOB_SAS_TOKEN` 这一行，填入刚才生成的 SAS Token：

```bash
# 格式说明：
# ← 确保前面没有 "sv=" 或 "?"
# ← 完整复制所有查询参数
# ← 不要有换行
AZURE_BLOB_SAS_TOKEN=sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

**验证 SAS Token 格式：**

```bash
# 使用 blob_tool.py 测试
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"
```

应该看到：

```
✅ 文件存在
   大小: 234.56 MB
   Content-Type: application/x-gzip
   最后修改: Fri, 09 Jun 2026 01:57:00 GMT
```

## 服务器凭据配置

### HPUY 服务器配置

如果你的 HPUY 服务器信息如下：

- SSH 地址：`192.168.1.100`
- SSH 端口：`9991`
- 用户名：`admin`
- 密码：`EdgeLoggerSys@1024`
- 远程目录：`/root/EMS/`

在 .env 文件中配置：

```bash
# HPUY 服务器凭据
HPUY_SSH_USER=admin
HPUY_SSH_PASSWORD=EdgeLoggerSys@1024
HPUY_SSH_HOST=192.168.1.100
HPUY_SSH_PORT=9991
```

### EE 服务器配置

如果你的 EE 服务器信息如下：

- SSH 地址：`10.0.0.100`
- SSH 端口：`9991`
- 用户名：`root`
- 密码：`En&vi0n!#%`
- 远程目录：`/home/envuser/energy-os/`

在 .env 文件中配置：

```bash
# EE 服务器凭据
EE_SSH_USER=root
EE_SSH_PASSWORD=En&vi0n!#%
EE_SSH_HOST=10.0.0.100
EE_SSH_PORT=9991
```

## 本地镜像目录配置

### 默认配置

项目默认使用：`/mnt/d/Blob`

这个路径是在 WSL 中访问 Windows 的 D 盘，路径映射关系：

```
Windows: D:\Blob\ → Linux: /mnt/d/Blob\
Windows: C:\Users\xxx\Desktop\ → Linux: /mnt/c/Users/xxx/Desktop\
```

### 如何修改为其他目录

如果需要使用其他目录，编辑 .env 文件：

```bash
# 修改本地镜像目录
BLOB_MIRROR_DIR=/home/yuhangtian/BlobMirror

# 创建目录并设置权限
mkdir -p /home/yuhangtian/BlobMirror
```

### Windows 下使用本地目录

在 Windows 本机上直接使用（无需 WSL）：

```bash
# 在 PowerShell 中运行
cd D:\\BlobMirror
mkdir -p .\\0007_prepare_blob_mirrors\\edge-ems

# 上传 SAS Token
$env:AZURE_BLOB_SAS_TOKEN = "sv=2021-06-08&ss=b&srt=sco&sp=rwl&..."

# 使用 Python 直接下载（需安装 Azure SDK）
pip install azure-storage-blob
python upload_blob_to_mirror.py "your-blob-path"
```

## 数字签名配置（可选）

如果需要添加数字签名验证文件完整性：

### 1. 生成加密密钥对

```bash
# 生成私钥
openssl genpkey -algorithm RSA -out deploy_private.pem -pkeyopt rsa_keygen_bits:4096

# 生成公钥
openssl pkey -pubout -in deploy_private.pem -out deploy_public.pem

# 显示私钥（仅保存时）
cat deploy_private.pem
```

### 2. 配置 .env 文件

```bash
# 启用签名验证
ENABLE_SIGNATURE_VERIFICATION=true

# 保存公钥（base64 编码）
SIGNING_PUBLIC_KEY=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...（公钥内容）
```

### 3. 修改 main.py 验证逻辑

```python
# 在 download_to_local 函数中添加签名验证
if ENABLE_SIGNATURE_VERIFICATION:
    download_url_with_sig = f"{blob_url}.${signature_suffix}"
    result = subprocess.run(
        ["curl", "-L", "-o", str(local_path), download_url_with_sig],
        check=True,
        capture_output=True
    )
    # 验证签名

```

**注意：** 此功能为可选增强，默认部署工具不需要。

## 环境验证

### 运行完整性检查

```bash
# 检查所有依赖
python check_environment.py
```

检查项：
- ✅ Python 版本 >= 3.8
- ✅ pip 已安装
- ✅ curl 已安装
- ✅ requests 库已安装
- ✅ AZURE_BLOB_SAS_TOKEN 已设置
- ✅ 本地镜像目录存在

### 测试连接

```bash
# 测试 Azure Blob 连接
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"

# 或列出所有可用分支
python blob_tool.py \
    --list "edgeftpfile/edge-ems/"
```

### 测试服务器连接

```bash
# 测试 HPUY 服务器连接
python test_ssh_connection.py --server HPUY

# 测试 EE 服务器连接
python test_ssh_connection.py --server EE
```

## 配置自动加载

### 方法一：source .env 文件

每次使用前加载环境变量：

```bash
source .env
python main.py --branch develop_2605 --server HPUY --component all
```

### 方法二：在 .bashrc 中添加

```bash
# 编辑 ~/.bashrc
vim ~/.bashrc

# 在文件末尾添加
echo 'source /path/to/edge-ems-deploy-tool/.env' >> ~/.bashrc

# 重新加载配置
source ~/.bashrc
```

### 方法三：使用 direnv（推荐）

```bash
# 安装 direnv
pip install direnv

# 在项目目录创建 .envrc
echo "source .env" > .envrc

# 初始化
direnv allow
```

## 验证安装成功

### 1. 检查帮助信息

```bash
python main.py --help
```

应该看到完整的帮助文档和示例。

### 2. 测试下载（不上传）

```bash
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all \
    --tar-only
```

如果看到：

```
✅ 部署阶段完成（仅下载到本地镜像）
✅ 得到本地文件: /mnt/d/Blob/edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz
```

说明安装成功！

### 3. 测试配置文件加载

```bash
python test_config.py
```

应该看到：

```
✅ AZURE_BLOB_SAS_TOKEN: 已设置
✅ HPUY_SSH_HOST: xxx.xxx.xxx.xxx
✅ Local mirror: /mnt/d/Blob
```

## 常见安装问题

### Q1: MissingModuleNotFoundError: No module named 'requests'

**解决：**
```bash
pip install requests>=2.31.0
```

### Q2: Permission denied: '/mnt/d/Blob'

**解决：**
```bash
# 添加执行权限
chmod +x ./*.py

# 创建目录
sudo mkdir -p /mnt/d/Blob
sudo chown $USER:$USER /mnt/d/Blob
```

### Q3: Cannot parse datetime

**解决：**
```bash
# 更新本地时间时区
sudo timedatectl set-timezone Asia/Shanghai

# 检查系统时间
date
```

### Q4: curl: (22) The requested URL returned error: 404

**解决：**
- 检查 Blob 路径是否正确
- 使用 blob_tool.py 测试路径是否存在
- 检查 SAM Token 权限（需要 Read 和 List）

### Q5: SSH Connection timed out

**解决：**
```bash
# 检查服务器 IP 和端口
python test_ssh_connection.py --server HPUY

# 如果需要，添加 SSH 重试逻辑
vim main.py  # 在代码中添加 retries 参数
```

## 性能优化建议

### 1. 本地带宽优化

```bash
# 使用 zstd 压缩（如果服务器支持）
# 修改 download_to_local 函数，使用 curl -z

# 使用 rsync 增量同步（如果是第二次部署）
rsync -avz --progress blob_mirror/ user@server:/remote/path/
```

### 2. 并行下载

```bash
# 安装 aria2c
apt install aria2  # Ubuntu
yum install aria2  # CentOS

# 修改 main.py 使用 aria2 并行下载
```

### 3. CDN 加速

如果 Azure Blob 访问较慢，可以：
- 使用 Azure CDN 加速
- 在本地镜像服务器上缓存文件
- 指定国内节点下载

## 下一步

安装完成后，请参考：

1. **[README.md](README.md)** - 了解更多功能和使用方法
2. **[azure-blob-setup.md](azure-blob-setup.md)** - 如果需要重新配置 SAS 令牌
3. **[troubleshooting.md](troubleshooting.md)** - 解决部署过程中的问题

祝部署顺利！🚀
