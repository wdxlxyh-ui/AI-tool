#!/usr/bin/env python3
"""
Edge-EMS 程序包部署自动化工具
Azure Blob → 本地镜像 → 目标服务器 → 解压 → 权限修复

用法示例:
  # 仅下载到本地镜像（测试用）
  python main.py --branch develop_2605 --server HPUY --component all --tar-only

  # 完整部署
  python main.py --branch develop_2605 --server HPUY --component all

  # 部署特定组件
  python main.py --branch develop_2605 --server HPUY --component edge-ems

  # 使用本地已有文件（跳过下载）
  python main.py --branch develop_2605 --server HPUY --component edge-ems --no-download

依赖: pip install requests
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# ==================== 配置区域（按需修改）====================

# Azure Blob 基础路径
BLOB_ACCOUNT = "edgeadls2"
BLOB_CONTAINER = "edge"
BLOB_BASE = "edgeftpfile/edge-ems"
BLOB_BASE_HMI_FE = "edgeftpfile/edge-ems-hmi-fe"

# 本地镜像目录
LOCAL_MIRROR = Path("/mnt/d/Blob")

# 日志目录
LOG_DIR = Path("/tmp/edge-ems-deploy-logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 服务器凭据（按需修改 IP 地址）
SERVER_CREDENTIALS = {
    "HPUY": {
        "user": "admin",
        "password": "EdgeLoggerSys@1024",
        "ssh_host": "xxx.xxx.xxx.xxx",   # ← 修改为实际 IP
        "ssh_port": 9991,
    },
    "EE": {
        "user": "root",
        "password": "En&vi0n!#%",
        "ssh_host": "xxx.xxx.xxx.xxx",   # ← 修改为实际 IP
        "ssh_port": 9991,
    }
}

# 组件定义
COMPONENTS = {
    "edge-ems": {
        "blob_subdir": "{server_type}/{branch}",       # Blob 子目录
        "package_name": "edge-ems.tar.gz",              # 包文件名
        "is_zip": False,
        "remote_dirs": {
            "HPUY": "/root/EMS/edge-ems/",
            "EE":   "/home/envuser/energy-os/edge-ems/",
        },
        "has_config_xml": True,     # 需要恢复 config.xml
        "needs_restart": True,
    },
    "edge-ems-hmi": {
        "blob_subdir": "{server_type}/{branch}",
        "package_name": "edge-ems-hmi.tar.gz",
        "is_zip": False,
        "remote_dirs": {
            "HPUY": "/root/EMS/edge-ems-hmi/",
            "EE":   "/home/envuser/energy-os/edge-ems-hmi/",
        },
        "has_config_xml": False,
        "needs_restart": True,
    },
    "edge-ems-hmi-fe": {
        # HMI-FE 的 Blob 路径特殊：HPUY 用 logger/，EE 用 x86_64/
        "blob_subdir_hpuY": "logger/{branch}",
        "blob_subdir_ee":   "x86_64/{branch}",
        "blob_subdir_arm":  "arm64/{branch}",
        "package_name": "edge-ems-hmi-fe.zip",          # 注意：是 zip 不是 tar.gz
        "is_zip": True,
        "remote_dirs": {
            "HPUY": "/root/EMS/edge-ems-hmi/edge-ems-hmi-fe/",
            "EE":   "/home/envuser/energy-os/edge-ems-hmi/edge-ems-hmi-fe/",
        },
        "has_config_xml": False,
        "needs_restart": False,    # 前端静态文件，无需重启
    },
}


# ==================== 工具函数 ====================

class Logger:
    """简单日志器"""
    def __init__(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"deploy_{ts}.log"

    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line, file=sys.stderr)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def header(self, title):
        self.log("")
        self.log("=" * 60)
        self.log(f"  {title}")
        self.log("=" * 60)


logger = Logger()


def run_cmd(cmd, timeout=300):
    """执行本地命令，返回 (returncode, stdout, stderr)"""
    logger.log(f"  $ {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0 and result.stderr:
        logger.log(f"  stderr: {result.stderr.strip()}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ssh_run(cred, cmd, timeout=120):
    """通过 SSH 在远程服务器执行命令"""
    ssh_cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
        f"-p {cred['ssh_port']} {cred['user']}@{cred['ssh_host']} "
        f"{shlex_quote(cmd)}"
    )
    return run_cmd(ssh_cmd, timeout=timeout)


def ssh_upload(cred, local_path, remote_path):
    """通过 SCP 上传文件"""
    scp_cmd = (
        f"scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
        f"-P {cred['ssh_port']} "
        f"{shlex_quote(str(local_path))} "
        f"{cred['user']}@{cred['ssh_host']}:{shlex_quote(remote_path)}"
    )
    return run_cmd(scp_cmd, timeout=600)


def shlex_quote(s):
    """简单 shell 转义"""
    import shlex
    return shlex.quote(str(s))


# ==================== 核心流程 ====================

def get_sas_token():
    """获取 Azure Blob SAS 令牌"""
    # 优先从环境变量获取
    token = os.environ.get("AZURE_BLOB_SAS_TOKEN")
    if token:
        return token

    # 尝试从 .env 文件加载
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("AZURE_BLOB_SAS_TOKEN="):
                token = line.split("=", 1)[1].strip().strip("'\"")
                if token:
                    os.environ["AZURE_BLOB_SAS_TOKEN"] = token
                    return token

    return None


def build_blob_url(blob_path, sas_token):
    """构建完整的 Blob 下载 URL"""
    return f"https://{BLOB_ACCOUNT}.blob.core.chinacloudapi.cn/{BLOB_CONTAINER}/{blob_path}?{sas_token}"


def build_local_path(blob_path):
    """构建本地镜像路径"""
    return LOCAL_MIRROR / blob_path


def get_blob_path_for_component(component_name, server_type, branch, hmi_fe_arch="x86_64"):
    """根据组件名构建 Blob 文件路径"""
    comp = COMPONENTS[component_name]

    if component_name == "edge-ems-hmi-fe":
        # HMI-FE 路径特殊
        if server_type == "HPUY":
            subdir = comp["blob_subdir_hpuY"].format(branch=branch)
        elif hmi_fe_arch == "arm64":
            subdir = comp["blob_subdir_arm"].format(branch=branch)
        else:
            subdir = comp["blob_subdir_ee"].format(branch=branch)
        return f"{BLOB_BASE_HMI_FE}/{subdir}/{comp['package_name']}"
    else:
        subdir = comp["blob_subdir"].format(server_type=server_type, branch=branch)
        return f"{BLOB_BASE}/{subdir}/{comp['package_name']}"


def step_download(blob_path, sas_token):
    """步骤1: 从 Azure Blob 下载到本地镜像"""
    logger.header(f"步骤1: 下载程序包")

    local_path = build_local_path(blob_path)

    # 检查本地是否已有
    if local_path.exists() and local_path.stat().st_size > 0:
        size_mb = local_path.stat().st_size / 1024 / 1024
        logger.log(f"本地文件已存在: {local_path} ({size_mb:.1f} MB)")
        return local_path

    # 确保目录存在
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # 下载
    blob_url = build_blob_url(blob_path, sas_token)
    logger.log(f"下载 URL: {blob_url[:100]}...")
    logger.log(f"保存到: {local_path}")

    rc, stdout, stderr = run_cmd(f'curl -L -o "{local_path}" "{blob_url}"', timeout=600)

    if not local_path.exists() or local_path.stat().st_size == 0:
        logger.log(f"下载失败！请检查 SAS 令牌和 Blob 路径", "ERROR")
        sys.exit(1)

    size_mb = local_path.stat().st_size / 1024 / 1024
    logger.log(f"下载成功: {local_path} ({size_mb:.1f} MB)")
    return local_path


def step_upload(component_name, local_path, server_type):
    """步骤2: 上传到服务器"""
    logger.header(f"步骤2: 上传 {component_name}")

    comp = COMPONENTS[component_name]
    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    package_name = comp["package_name"]

    logger.log(f"服务器: {cred['user']}@{cred['ssh_host']}:{cred['ssh_port']}")
    logger.log(f"远程目录: {remote_dir}")

    if server_type == "HPUY":
        # HPUY: admin 无法直接写 /root/，先传到 /home/admin/，再 sudo mv
        staging_path = f"/home/admin/{package_name}"
        ssh_upload(cred, local_path, staging_path)
        ssh_run(cred, f"echo '{cred['password']}' | sudo -S mv {staging_path} {remote_dir}{package_name}")
    else:
        # EE: root 可以直接写，但最终文件属于 envuser
        ssh_upload(cred, local_path, f"{remote_dir}{package_name}")

    logger.log(f"上传成功")


def step_extract(component_name, server_type):
    """步骤3: 解压"""
    logger.header(f"步骤3: 解压 {component_name}")

    comp = COMPONENTS[component_name]
    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    package_name = comp["package_name"]
    password = cred["password"]

    if server_type == "HPUY":
        sudo_prefix = f"echo '{password}' | sudo -S bash -c '"
        sudo_suffix = "'"
    else:
        sudo_prefix = "bash -c '"
        sudo_suffix = "'"

    # 解压命令
    if comp["is_zip"]:
        extract_cmd = f"cd {remote_dir} && unzip -o {package_name}"
    else:
        extract_cmd = f"cd {remote_dir} && tar -zxvf {package_name}"

    full_cmd = f"{sudo_prefix}{extract_cmd}{sudo_suffix}"
    rc, stdout, stderr = ssh_run(cred, f"{sudo_prefix}{extract_cmd}{sudo_suffix}")

    # 打印解压输出（最后几行）
    if stdout:
        for line in stdout.splitlines()[-5:]:
            logger.log(f"  {line}")

    logger.log(f"解压完成")


def step_restore_config(component_name, server_type):
    """步骤4: 恢复 config.xml（仅 edge-ems 需要）"""
    comp = COMPONENTS[component_name]
    if not comp["has_config_xml"]:
        return

    logger.header(f"步骤4: 恢复 config.xml")

    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    password = cred["password"]

    # 先检查根目录 config.xml 是否存在
    check_cmd = f"test -f {remote_dir}config.xml && echo EXISTS || echo MISSING"
    rc, stdout, stderr = ssh_run(cred, check_cmd)

    if "EXISTS" in stdout:
        if server_type == "HPUY":
            copy_cmd = f"echo '{password}' | sudo -S bash -c 'cp {remote_dir}config.xml {remote_dir}bin/config.xml'"
        else:
            copy_cmd = f"cp {remote_dir}config.xml {remote_dir}bin/config.xml"

        ssh_run(cred, copy_cmd)
        logger.log(f"已将 {remote_dir}config.xml 恢复到 bin/config.xml")
    else:
        logger.log(f"根目录无 config.xml，跳过恢复（tarball 可能已包含正确配置）")


def step_fix_ownership(component_name, server_type):
    """步骤5: 修复文件权限"""
    logger.header(f"步骤5: 修复文件权限")

    comp = COMPONENTS[component_name]
    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    password = cred["password"]

    if server_type == "HPUY":
        ssh_run(cred, f"echo '{password}' | sudo -S chown -R root:root {remote_dir}")
        logger.log(f"已设置权限: root:root")
    else:
        ssh_run(cred, f"chown -R envuser:envuser {remote_dir}")
        logger.log(f"已设置权限: envuser:envuser")


def step_restart(component_name, server_type):
    """步骤6: 重启服务（可选）"""
    comp = COMPONENTS[component_name]
    if not comp["needs_restart"]:
        logger.log(f"{component_name} 无需重启（静态文件）")
        return

    logger.header(f"步骤6: 重启 {component_name}")

    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    password = cred["password"]

    if server_type == "HPUY":
        ssh_run(cred, f"echo '{password}' | sudo -S bash -c 'cd {remote_dir}bin/ && bash start.sh'")
    else:
        ssh_run(cred, f"su - envuser -c 'cd {remote_dir}bin/ && bash start.sh'")

    logger.log(f"重启命令已执行")
    logger.log(f"注意: start.sh 的 exit code -1 是正常现象，请以进程状态为准")


def step_verify(component_name, server_type):
    """步骤7: 验证部署结果"""
    logger.header(f"步骤7: 验证 {component_name}")

    comp = COMPONENTS[component_name]
    cred = SERVER_CREDENTIALS[server_type]
    remote_dir = comp["remote_dirs"][server_type]
    password = cred["password"]

    # 检查 VERSION 文件
    version_file = f"{remote_dir}bin/VERSION"
    rc, stdout, stderr = ssh_run(cred, f"cat {version_file} 2>/dev/null")
    if stdout:
        logger.log(f"版本: {stdout.strip()}")
    else:
        logger.log(f"VERSION 文件不存在或无法读取")

    # 检查进程
    if comp["needs_restart"]:
        if server_type == "HPUY":
            rc, stdout, stderr = ssh_run(cred, f"echo '{password}' | sudo -S ps aux | grep {component_name} | grep -v grep")
        else:
            rc, stdout, stderr = ssh_run(cred, f"ps aux | grep {component_name} | grep -v grep")

        if stdout:
            logger.log(f"进程运行中")
        else:
            logger.log(f"未检测到进程（可能正在启动中）", "WARN")


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(
        description="Edge-EMS 程序包部署自动化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--branch", required=True,
                        help="分支名称，如 develop_2605")
    parser.add_argument("--server", required=True, choices=["HPUY", "EE"],
                        help="目标服务器类型")
    parser.add_argument("--component", required=True,
                        choices=["all", "edge-ems", "edge-ems-hmi", "edge-ems-hmi-fe"],
                        help="组件名称或 all")
    parser.add_argument("--hmi-fe-arch", choices=["x86_64", "arm64"], default="x86_64",
                        help="HMI-FE 架构（默认 x86_64）")
    parser.add_argument("--tar-only", action="store_true",
                        help="仅下载到本地镜像，不上传服务器")
    parser.add_argument("--no-download", action="store_true",
                        help="跳过下载，使用本地已有文件")
    parser.add_argument("--no-restart", action="store_true",
                        help="部署后不重启服务")

    args = parser.parse_args()

    # 确定要部署的组件列表
    if args.component == "all":
        deploy_list = ["edge-ems", "edge-ems-hmi"]
    else:
        deploy_list = [args.component]

    logger.header("Edge-EMS 部署工具")
    logger.log(f"分支: {args.branch}")
    logger.log(f"服务器: {args.server}")
    logger.log(f"组件: {deploy_list}")
    logger.log(f"HMI-FE 架构: {args.hmi_fe_arch}")
    logger.log(f"日志文件: {logger.log_file}")

    # 获取 SAS 令牌
    sas_token = get_sas_token()
    if not sas_token:
        logger.log("AZURE_BLOB_SAS_TOKEN 未设置！请在 .env 文件或环境变量中配置", "ERROR")
        sys.exit(1)

    # ========== 执行部署 ==========
    for comp_name in deploy_list:
        logger.header(f"处理组件: {comp_name}")

        # 构建 Blob 路径
        blob_path = get_blob_path_for_component(
            comp_name, args.server, args.branch, args.hmi_fe_arch
        )
        local_path = build_local_path(blob_path)

        # 步骤1: 下载或检查本地文件
        if args.no_download:
            if not local_path.exists():
                logger.log(f"本地文件不存在: {local_path}", "ERROR")
                logger.log(f"请先下载或去掉 --no-download 参数", "ERROR")
                sys.exit(1)
            logger.log(f"使用本地文件: {local_path}")
        else:
            if local_path.exists() and local_path.stat().st_size > 0:
                size_mb = local_path.stat().st_size / 1024 / 1024
                logger.log(f"本地文件已存在，跳过下载: {local_path} ({size_mb:.1f} MB)")
            else:
                local_path = step_download(blob_path, sas_token)

        # tar-only 模式到此结束
        if args.tar_only:
            logger.log(f"✅ --tar-only 模式，已下载到: {local_path}")
            continue

        # 步骤2: 上传
        step_upload(comp_name, local_path, args.server)

        # 步骤3: 解压
        step_extract(comp_name, args.server)

        # 步骤4: 恢复 config.xml
        step_restore_config(comp_name, args.server)

        # 步骤5: 修复权限
        step_fix_ownership(comp_name, args.server)

        # 步骤6: 重启（可选）
        if not args.no_restart:
            step_restart(comp_name, args.server)

        # 步骤7: 验证
        step_verify(comp_name, args.server)

        logger.log(f"✅ 组件 {comp_name} 部署完成")

    # ========== 汇总 ==========
    logger.header("部署完成")
    logger.log(f"所有组件已处理: {deploy_list}")
    logger.log(f"日志文件: {logger.log_file}")
    logger.log("")
    logger.log("后续操作:")
    logger.log(f"  查看日志: cat {logger.log_file}")
    cred = SERVER_CREDENTIALS[args.server]
    logger.log(f"  连接服务器: ssh -p {cred['ssh_port']} {cred['user']}@{cred['ssh_host']}")


if __name__ == "__main__":
    main()
