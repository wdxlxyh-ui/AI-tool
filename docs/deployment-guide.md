# 部署指南

## 目录

- [环境要求](#环境要求)
- [本机部署](#本机部署)
- [打包迁移到其他服务器](#打包迁移到其他服务器)
- [systemd 服务管理](#systemd-服务管理)
- [模拟器远程部署](#模拟器远程部署)
- [常见问题](#常见问题)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux（Ubuntu 18.04+ / CentOS 7+ / Debian 10+） |
| Python | 3.8 或更高 |
| PyPI 包 | 仅 Flask（`pip3 install flask`） |
| 数据库 | 无需安装，SQLite 文件自动创建 |
| 端口 | 默认 8080（可配置） |

无 Redis、MySQL、Nginx 等外部依赖。

---

## 本机部署

```bash
# 1. 进入项目目录
cd /root/EGC

# 2. 安装依赖
pip3 install flask

# 3. 启动
python3 run.py --port 8080
```

启动后访问 `http://localhost:8080`，使用 `admin / admin123` 登录。

### 命令行参数

```
python3 run.py --help

可选参数:
  --host HOST      监听地址（默认 0.0.0.0）
  --port PORT      监听端口（默认 8080）
  --debug          调试模式
```

---

## 打包迁移到其他服务器

项目自带 `egc-deploy.sh` 脚本，支持一键打包和远程部署。

### 步骤一：源服务器打包

```bash
cd /root/EGC
bash egc-deploy.sh pack
```

生成两个文件：

| 文件 | 说明 |
|------|------|
| `egc-bundle.tar.gz` | 项目完整打包（约 60MB，排除 .git/pycache） |
| `egc-deploy.sh` | 部署脚本 |

### 步骤二：传输到目标服务器

```bash
scp egc-bundle.tar.gz egc-deploy.sh root@目标IP:/root/
```

### 步骤三：目标服务器部署

```bash
ssh root@目标IP
cd /root
bash egc-deploy.sh deploy egc-bundle.tar.gz
```

脚本自动完成：
1. 解压项目文件
2. 检测 Python 环境
3. 安装 Flask（pip 或系统包管理器）
4. 注册 systemd 服务
5. 启动并验证

### 快速启动模式（不装 systemd）

适用于临时调试：

```bash
bash egc-deploy.sh quick
```

前台直接运行，Ctrl+C 停止。

---

## systemd 服务管理

部署后通过 systemd 管理服务：

```bash
systemctl start egc-server       # 启动
systemctl stop egc-server        # 停止
systemctl restart egc-server     # 重启
systemctl status egc-server      # 状态
systemctl enable egc-server      # 开机自启
systemctl disable egc-server     # 取消自启
```

日志位置：`/var/log/egc-server.log`

```bash
tail -f /var/log/egc-server.log  # 实时日志
```

---

## 模拟器远程部署

通过模拟器管理页面可将 GridSim 部署到远程服务器。

### 前提条件

1. **SSH 免密登录**已配置（源服务器到目标服务器）

```bash
# 源服务器执行
ssh-copy-id root@目标IP
```

2. 目标服务器有 `tar`、`bash`

### 部署流程

1. 在仪表盘进入「模拟器管理」
2. 选择构建包（`gridsim-vX.Y.Z-linux-amd64.tar.gz`）
3. 填写远程服务器 IP、端口、用户名
4. 点击部署

### 升级时备份/还原机制

升级部署时自动执行：

```
① 停止服务
② 备份 config/ → backups/config-pre-upgrade-{时间戳}/
③ 清理旧文件（保留 backups/）
④ 解压新版本
⑤ 从最新备份还原 config/
⑥ 启动服务
```

备份目录结构：

```
/home/envuser/IEC/gridsim/backups/
├── config-pre-upgrade-20260614-100000/
│   ├── instances.json       # 模拟器实例配置
│   ├── users.json           # 用户配置
│   ├── proxy-store.json     # 代理存储
│   ├── auto_changes/        # 自动变化策略
│   └── manifest.json        # 备份元信息
└── config-pre-upgrade-20260614-120000/
    └── ...
```

---

## 常见问题

### pip 坏了无法安装 Flask

```bash
# 用系统包管理器代替
apt install python3-flask      # Ubuntu/Debian
yum install python3-flask      # CentOS
```

### 端口被占用

```bash
# 查看占用
ss -tlnp | grep 8080

# 换端口启动
python3 run.py --port 9090
```

### 服务无法启动

```bash
# 查看详细错误
journalctl -u egc-server --no-pager -n 30

# 常见原因：
# 1. Flask 未安装 → pip3 install flask
# 2. 端口冲突 → 换端口
# 3. 权限问题 → 确保以 root 或有权限的用户运行
```

### 远程部署 instances.json 丢失

已在 `b1c7135` 修复。根因是 SSH 命令用了双引号导致本地 shell 提前展开 `$` 变量，还原命令实际未执行。确保使用最新版本代码。

### 数据迁移

所有运行时数据在 `data/` 目录：

```bash
# 备份
cp -r /root/EGC/data /backup/egc-data

# 恢复
cp -r /backup/egc-data/* /root/EGC/data/
systemctl restart egc-server
```
