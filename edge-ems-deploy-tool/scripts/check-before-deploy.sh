#!/bin/bash
# 部署前检查脚本
# 用于确保所有依赖和环境配置都就绪

set -e  # 遇到错误立即退出

echo "========================================="
echo "  Edge-EMS 部署前检查"
echo "========================================="
echo ""

IS_FAILED=0
ERROR_LOG=""

check_command() {
    local cmd=$1
    local desc=$2

    echo -n "🔍 检查 $desc ... "

    if command -v $cmd &> /dev/null; then
        echo "✅ 已安装"
        return 0
    else
        echo "❌ 未安装"
        ERROR_LOG="$ERROR_LOG\n\n❌ 错误：$cmd 未安装\n"
        IS_FAILED=1
        return 1
    fi
}

check_python_version() {
    echo -n "🔍 检查 Python 版本 ... "

    python_ver=$(python3 --version 2>&1 | awk '{print $2}')
    python_major=$(echo $python_ver | cut -d. -f1)
    python_minor=$(echo $python_ver | cut -d. -f2)

    if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 8 ]; then
        echo "✅ $python_ver"
        return 0
    else
        echo "❌ 需要 Python 3.8+，当前: $python_ver"
        ERROR_LOG="$ERROR_LOG\n\n❌ 错误：Python 版本过低\n"
        IS_FAILED=1
        return 1
    fi
}

check_sas_token() {
    echo -n "🔍 检查 Azure SAS Token ... "

    if [ -z "$AZURE_BLOB_SAS_TOKEN" ]; then
        echo "❌ 未设置"
        ERROR_LOG="$ERROR_LOG\n\n❌ 错误：AZURE_BLOB_SAS_TOKEN 环境变量未设置\n"
        IS_FAILED=1
        return 1
    else
        # 检查 SAS Token 是否包含必要参数
        if [[ ! $AZURE_BLOB_SAS_TOKEN =~ sv= ]]; then
            echo "⚠️  格式可能不正确（缺少 'sv='）"
            echo "   请检查 .env 文件"
            # 不算失败，只是警告
            return 1
        else
            echo "✅ 已设置"
            return 0
        fi
    fi
}

check_local_mirror() {
    local mirror_dir=${BLOB_MIRROR_DIR:-/mnt/d/Blob}

    echo -n "🔍 检查本地镜像目录 ($mirror_dir) ... "

    if [ -d "$mirror_dir" ]; then
        local dir_size=$(du -sh $mirror_dir 2>/dev/null | awk '{print $1}')
        echo "✅ 目录已存在 (${dir_size})"
        return 0
    else
        echo "❌ 目录不存在"
        ERROR_LOG="$ERROR_LOG\n\n❌ 错误：本地镜像目录不存在 $mirror_dir\n"
        error_msg="$ERROR_LOG"
        IS_FAILED=1
        return 1
    fi
}

check_blob_file() {
    local blob_path=$1
    echo -n "🔍 检查 Blob 文件 ($blob_path) ... "

    if python3 -c "import sys; sys.path.insert(0, '.'); from blob_tool import AzureBlobClient; client = AzureBlobClient(); result = client.check_file_exists_with_head('edge', '$blob_path', '$AZURE_BLOB_SAS_TOKEN'); print('EXISTS' if result['exists'] else 'NOT_FOUND')" 2>/dev/null | grep -q EXISTS; then
        echo "✅ 文件存在"
        return 0
    else
        echo "⚠️  文件不存在或无法访问"
        echo "   请检查 Blob 路径和 SAS Token 权限"
        return 1
    fi
}

check_ssh_connection() {
    local server=$1
    local ssh_host=${SERVER_CREDENTIALS_${server}_SSH_HOST:-"未配置"}
    local ssh_port=${SERVER_CREDENTIALS_${server}_SSH_PORT:-"未配置"}
    local ssh_user=${SERVER_CREDENTIALS_${server}_SSH_USER:-"未配置"}

    echo -n "🔍 检查 $server SSH 连接 ... "

    # 如果凭据完全未配置，跳过
    if [ "$ssh_host" = "未配置" ] || [ "$ssh_port" = "未配置" ]; then
        echo "⚠️  跳过（未配置服务器地址）"
        return 0
    fi

    # 测试 SSH 连接（10秒超时）
    if timeout 10 bash -c "echo > /dev/null" 2>/dev/null; then
        if timeout 10 ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $ssh_port $ssh_user@$ssh_host "echo 'SSH连接成功'" 2>/dev/null; then
            echo "✅ 连接正常"
            return 0
        else
            echo "⚠️  连接失败"
            echo "   请检查 IP 地址、端口和密码"
            return 1
        fi
    else
        echo "❌ SSH 不可用"
        ERROR_LOG="$ERROR_LOG\n\n❌ 信息：SSH 命令不可用，无法测试服务器连接\n"
        return 2
    fi
}

# ==================== 执行检查 ====================

echo "📦 检查系统依赖..."
echo ""

# 基本命令检查
check_command "python3" "Python 3"
check_command "curl" "curl"
check_command "ssh" "SSH client"

echo ""
echo "🐍 检查 Python 环境..."
python_check=$(check_python_version)

echo ""
echo "🔑 检查安全认证..."
sas_check=$(check_sas_token)

echo ""
echo "📁 检查本地镜像..."
mirror_check=$(check_local_mirror)

echo ""
echo "☁️  检查 Blob 文件..."
blob_files=(
    "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"
    "edgeftpfile/edge-ems/develop_2605/EE/edge-ems.tar.gz"
)

for file in "${blob_files[@]}"; do
    check_blob_file "$file"
done

echo ""
echo "🖥️  检查服务器连接..."
# 只检查已配置的服务器
for server in HPUY EE; do
    # 跳过未配置的服务器
    if [ "${SERVER_CREDENTIALS_${server}_SSH_HOST:-}" = "" ]; then
        continue
    fi
    check_ssh_connection "$server"
done

# ==================== 检查结果汇总 ====================

echo ""
echo "========================================="
echo "  检查结果汇总"
echo "========================================="
echo ""

if [ $IS_FAILED -eq 0 ]; then
    echo "✅ 所有检查通过！"
    echo ""
    echo "💡 可以开始部署了"
    echo ""
    echo "示例命令："
    echo "  python main.py --branch develop_2605 --server HPUY --component all"
    echo ""
    exit 0
else
    echo "❌ 检查发现以下问题："
    echo ""

    # 输出错误日志
    if [ -n "$error_msg" ]; then
        echo -e "$error_msg"
    else
        echo "- 环境配置不完整"
        echo "- 缺少必要依赖或工具"
        echo "- Blob 文件不存在或无法访问"
        echo "- 服务器连接失败"
    fi

    echo ""
    echo "💡 请根据上述提示解决问题"
    echo "💡 参考 docs/troubleshooting.md 了解详细解决方案"
    echo ""

    # 尝试修复某些常见问题
    if [ "$mirror_check" = "1" ]; then
        echo "🔧 尝试创建本地镜像目录..."
        local mirror_dir=${BLOB_MIRROR_DIR:-/mnt/d/Blob}
        mkdir -p "$mirror_dir" && chmod +x "$mirror_dir" && echo "✅ 目录已创建" || echo "❌ 创建失败"
    fi

    exit 1
fi
