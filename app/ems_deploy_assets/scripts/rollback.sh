#!/bin/bash
# 快速回滚脚本
# 备份当前位置 → 上传新文件 → 替换

set -e

SERVER=$1
BRANCH=$2
COMPONENT=$3

if [ -z "$SERVER" ] || [ -z "$BRANCH" ] || [ -z "$COMPONENT" ]; then
    echo "❌ 错误：缺少必要参数"
    echo "用法: rollback.sh <server> <branch> <component>"
    echo ""
    echo "示例："
    echo "  rollback.sh HPUY develop_2605 edge-ems"
    exit 1
fi

echo "========================================="
echo "  Edge-EMS 快速回滚"
echo "========================================="
echo ""
echo "配置："
echo "  服务器类型: $SERVER"
echo "  分支: $BRANCH"
echo "  组件: $COMPONENT"
echo ""

# 获取凭据
SSH_USER="${SERVER_CREDENTIALS_${SERVER}_SSH_USER}"
SSH_PASSWORD="${SERVER_CREDENTIALS_${SERVER}_SSH_PASSWORD}"
SSH_HOST="${SERVER_CREDENTIALS_${SERVER}_SSH_HOST}"
SSH_PORT="${SERVER_CREDENTIALS_${SERVER}_SSH_PORT}"

# 检查目标组件是否支持回滚
SUPPORTED_COMPONENTS=("edge-ems" "edge-ems-hmi")

if [[ ! " ${SUPPORTED_COMPONENTS[*]} " =~ " ${COMPONENT} " ]]; then
    echo "❌ 错误：组件 $COMPONENT 不支持回滚"
    echo "支持回滚的组件: ${SUPPORTED_COMPONENTS[*]}"
    exit 1
fi

# 检查凭据
if [ -z "$SSH_HOST" ] || [ -z "$SSH_PASSWORD" ]; then
    echo "❌ 错误：服务器 $SERVER 凭据未配置"
    echo "请检查 .env 文件"
    exit 1
fi

echo "⚠️ 安全警告："
echo "  此操作将上传新的程序包并覆盖当前位置"
echo "  建议操作前先确认新包已正确解压"
echo "  方式1: python main.py --tar-only 先下载测试"
echo "  方式2: 手动解压并检查解压结果"
echo ""
read -p "是否继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 已取消回滚"
    exit 1
fi

echo ""
echo "📦 备份当前位置..."

# 构建备份文件名
BACKUP_FILE="edge-ems-backup-${BRANCH}-${COMPONENT}-$(date +%Y%m%d-%H%M%S).tar.gz"

# 获取远程目录
if [ "$SERVER" = "HPUY" ]; then
    REMOTE_DIR="/root/EMS/$COMPONENT"
else
    REMOTE_DIR="/home/envuser/energy-os/$COMPONENT"
fi

# 使用 SSH 在服务器上打包
if [ "$SERVER" = "HPUY" ]; then
    SSH_CMD="echo '$SSH_PASSWORD' | sudo -S bash -c"
    BACKUP_CMD="$SSH_CMD 'cd $(dirname $REMOTE_DIR) && tar -czf /tmp/$BACKUP_FILE $(basename $REMOTE_DIR)'"
else
    SSH_CMD="ssh -p $SSH_PORT"
    BACKUP_CMD="$SSH_CMD $SSH_USER@$SSH_HOST 'cd $(dirname $REMOTE_DIR) && tar -czf $REMOTE_DIR/../$BACKUP_FILE $(basename $REMOTE_DIR)'"
fi

# 执行备份
if bash -c "$BACKUP_CMD" 2>/dev/null; then
    echo "✅ 备份已生成: $BACKUP_FILE"
    echo "   备份位置: $REMOTE_DIR/../$BACKUP_FILE"

    # 如果成功，询问是否下载备份文件
    read -p "是否下载备份文件到本地？(y/n): " download_backup

    if [ "$download_backup" = "y" ]; then
        LOCAL_BACKUP_PATH=$(pwd)/$BACKUP_FILE
        
        if [ "$SERVER" = "HPUY" ]; then
            # HPUY 使用 SFTP 下载
            scp -P $SSH_PORT $SSH_USER@$SSH_HOST:$REMOTE_DIR/../$BACKUP_FILE "$LOCAL_BACKUP_PATH"
        else
            # EE 使用 SSH scp
            scp -P $SSH_PORT $SSH_USER@$SSH_HOST:$REMOTE_DIR/../$BACKUP_FILE "$LOCAL_BACKUP_PATH"
        fi

        if [ $? -eq 0 ]; then
            echo "✅ 备份文件已下载: $LOCAL_BACKUP_PATH"
        else
            echo "❌ 备份文件下载失败"
        fi
    fi
else
    echo "❌ 备份失败"
    echo "   可能原因："
    echo "   1. 权限不足"
    echo "   2. 目录为空"
    echo "   3. SSH 连接失败"
    exit 1
fi

echo ""
echo "📤 准备上传新程序包..."

# 获取本地文件路径
if [ "$COMPONENT" = "edge-ems-hmi-fe" ]; then
    # HMI-FE 有架构参数
    if [ "$SERVER" = "HPUY" ]; then
        BLOB_BASE_HMI_FE="edgeftpfile/edge-ems-hmi-fe/HPUY/logger"
    else
        BLOB_BASE_HMI_FE="edgeftpfile/edge-ems-hmi-fe/x86_64"
    fi
    LOCAL_FILE="$BLOB_MIRROR_DIR/$BLOB_BASE_HMI_FE/$BRANCH/edge-ems-hmi-fe.zip"
else
    BLOB_BASE="${BLOB_BASE:-edgeftpfile/edge-ems}"
    LOCAL_FILE="$BLOB_MIRROR_DIR/$BLOB_BASE/$BRANCH/$SERVER/$COMPONENT.tar.gz"
fi

if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ 本地文件不存在: $LOCAL_FILE"
    echo "   请先下载程序包"
    
    # 提供快速下载命令
    echo ""
    echo "💡 使用以下命令下载："
    echo "   python main.py --branch $BRANCH --server $SERVER --component $COMPONENT"
    exit 1
fi

echo "✅ 找到本地文件: $LOCAL_FILE"
FILESIZE=$(du -h "$LOCAL_FILE" | awk '{print $1}')
echo "   文件大小: $FILESIZE"

echo ""
echo "🔄 开始部署流程（备份完成后）..."

# 使用主脚本进行部署
echo "🔍 运行部署检查..."
bash scripts/check-before-deploy.sh

echo ""
echo "🚀 开始部署..."
python main.py \
    --branch "$BRANCH" \
    --server "$SERVER" \
    --component "$COMPONENT"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "  回滚完成！"
    echo "========================================="
    echo ""
    echo "✅ 新版本已部署到服务器"
    echo "💾 备份文件: $BACKUP_FILE"
    echo "📝 日志文件: /tmp/edge-ems-deploy-logs/deploy_*.log"
    echo ""
    echo "💡 验证新版本："
    echo "   ssh $SSH_USER@$SSH_HOST:$SSH_PORT"
    echo "   echo '...命令查看版本和进程状态"
    
    # 询问是否进行验证
    read -p "是否立即运行验证脚本？(y/n): " verify

    if [ "$verify" = "y" ]; then
        bash scripts/verify-after-deploy.sh "$SERVER"
    fi
else
    echo ""
    echo "❌ 部署失败"
    echo ""
    echo "💡 回滚恢复步骤："
    echo "   1. 连接到服务器"
    echo "   2. 使用备份文件恢复原版本"
    
    if [ "$SERVER" = "HPUY" ]; then
        echo "   ssh $SSH_USER@$SSH_HOST:$SSH_PORT"
        echo "   sudo bash -c 'cd /root/EMS/$COMPONENT && tar -xzf /tmp/$BACKUP_FILE --strip-components=1'"
    else
        echo "   ssh $SSH_USER@$SSH_HOST:$SSH_PORT"
        echo "   bash -c 'cd /home/envuser/energy-os/$COMPONENT && tar -xzf $BLOB_MIRROR_DIR/$BACKUP_FILE --strip-components=1'"
    fi
    
    echo ""
    echo "⚠️  警告：备份前未回滚到旧版本"
    echo "   请立即手动恢复到之前的版本"
    exit 1
fi

echo ""
echo "========================================="
echo ""
echo "🎉 操作完成！(按 Ctrl+C 退出，验证后手动关闭)"
wait
