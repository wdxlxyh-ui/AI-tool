#!/usr/bin/env python3
"""
环境检查工具
用于验证项目的运行环境
"""
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"❌ Python 版本过低: {version.major}.{version.minor}.{version.micro}")
            print("   需要 Python 3.8+")
            return False
    except Exception as e:
        print(f"❌ 无法检测 Python 版本: {e}")
        return False


def check_dependencies():
    """检查依赖包"""
    dependencies = {
        "requests": "HTTP 请求库",
        "paramiko": "SSH 客户端（可选）"
    }

    missing = []
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✅ {package}: {description}")
        except ImportError:
            print(f"❌ {package}: {description} (未安装)")
            missing.append(package)

    return missing


def check_environment_variables():
    """检查环境变量"""
    requirements = ["AZURE_BLOB_SAS_TOKEN"]
    missing = []

    import os
    for env_var in requirements:
        value = os.environ.get(env_var)
        if value:
            # 隐藏部分值
            masked = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {env_var}: {masked}")
        else:
            print(f"⚠️  {env_var}: 未设置")
            missing.append(env_var)

    return missing


def check_local_directory(mirror_dir="/mnt/d/Blob"):
    """检查本地镜像目录"""
    try:
        mirror_path = Path(mirror_dir)
        mirror_path.mkdir(parents=True, exist_ok=True)

        dir_size = mirror_path.stat().st_size if mirror_path.exists() else 0
        dir_size_mb = dir_size / (1024 * 1024) if dir_size > 0 else 0

        print(f"✅ 本地镜像目录: {mirror_dir}")
        print(f"   大小: {dir_size_mb:.2f} MB")
        return True
    except Exception as e:
        print(f"⚠️  本地镜像目录检查失败: {e}")


def check_ssh_tools():
    """检查 SSH 工具"""
    try:
        # 检查 ssh 命令
        result = subprocess.run(["ssh", "-V"], capture_output=True, text=True)
        print(f"✅ SSH 客户端: 已安装")
        return True
    except FileNotFoundError:
        print(f"❌ SSH 客户端: 未安装")
        return False


def main():
    print("=" * 70)
    print("  Edge-EMS 部署工具 - 环境检查")
    print("=" * 70)
    print()

    all_pass = True

    # 1. Python 版本检查
    print("🔍 检查 Python 环境:")
    print("-" * 70)
    if not check_python_version():
        all_pass = False
    print()

    # 2. 依赖包检查
    print("🔍 检查依赖包:")
    print("-" * 70)
    missing_deps = check_dependencies()
    if missing_deps:
        all_pass = False
        print()
        print("💡 安装缺失包:")
        print(f"   pip install {' '.join(missing_deps)}")
    print()

    # 3. SSH 工具检查
    print("🔍 检查 SSH 工具:")
    print("-" * 70)
    if not check_ssh_tools():
        all_pass = False
    print()

    # 4. 环境变量检查
    print("🔍 检查环境变量:")
    print("-" * 70)
    missing_vars = check_environment_variables()
    print()

    # 5. 本地目录检查
    print("🔍 检查本地环境:")
    print("-" * 70)
    check_local_directory("/mnt/d/Blob")
    print()

    # 汇总结果
    print("=" * 70)
    print("  检查结果汇总")
    print("=" * 70)
    print()

    if all_pass:
        print("✅ 所有检查通过！环境可以启动部署。")
        print()
        print("💡 下一步操作:")
        print("   1. 配置 .env 文件（如需要）")
        print("   2. 运行部署: python main.py --branch develop_2605 --server HPUY --component all")
        return 0
    else:
        print("❌ 检查发现以下问题，请先解决后再部署：")
        print()
        if missing_deps:
            print("📦 依赖包问题:")
            print(f"   - 缺失: {', '.join(missing_deps)}")
            print("   - 解决: pip install " + " ".join(missing_deps))
        print()
        if missing_vars:
            print("🔐 环境变量问题:")
            print(f"   - 缺失: {', '.join(missing_vars)}")
            print("   - 解决: export " + "=".join(missing_vars))
            print("   - 或在 .env 文件中配置")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
