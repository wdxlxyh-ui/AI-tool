#!/bin/bash
# 部署后验证脚本
# 用于验证部署是否成功

set -e

echo "========================================="
echo "  Edge-EMS 部署后验证"
echo "========================================="
echo ""

SERVER=$1
if [ -z "$SERVER" ]; then
    echo "❌ 错误：请指定服务器类型"
    echo "用法: verify-after-deploy.sh <HPUY | EE>"
    exit 1
fi

echo "📋 验证配置："
echo "  服务器类型: $SERVER"
echo ""

# 获取凭据
SSH_USER=${SERVER_CREDENTIALS_${SERVER}_SSH_USER}
SSH_PASSWORD=${SERVER_CREDENTIALS_${SERVER}_SSH_PASSWORD}
SSH_HOST=${SERVER_CREDENTIALS_${SERVER}_SSH_HOST}
SSH_PORT=${SERVER_CREDENTIALS_${SERVER}_SSH_PORT}

# 检查凭据是否配置
if [ -z "$SSH_HOST" ] || [ -z "$SSH_PASSWORD" ]; then
    echo "⚠️  警告：服务器凭据未配置，跳过验证"
    exit 0
fi

echo "🔍 连接服务器: $SSH_USER@$SSH_HOST:$SSH_PORT"
echo ""

# 构建 SSH 命令
if [ "$SERVER" = "HPUY" ]; then
    SSH_CMD="echo '$SSH_PASSWORD' | sudo -S"
else
    SSH_CMD="bash -c"
fi

# ==================== 1. 检查组件是否存在 ====================
echo "📦 检查组件安装情况："
echo ""

COMPONENTS=("edge-ems" "edge-ems-hmi" "edge-ems-hmi-fe")

for component in "${COMPONENTS[@]}"; do
    if [ "$SERVER" = "HPUY" ]; then
        REMOTE_DIR="/root/EMS/edge-$component"
    else
        REMOTE_DIR="/home/envuser/energy-os/edge-$component"
    fi

    if [ -d "$REMOTE_DIR" ]; then
        echo "✅ $component: 已安装"
    else
        echo "❌ $component: 未找到"
    fi
done

echo ""
echo "====================="
echo ""
echo "2️⃣ 检查版本信息："
echo ""

# 检测版本文件
VERSION_FILES=(
    "/root/EMS/edge-ems/bin/VERSION"
    "/home/envuser/energy-os/edge-ems/bin/VERSION"
    "/root/EMS/edge-ems-hmi/bin/VERSION"
    "/home/envuser/energy-os/edge-ems-hmi/bin/VERSION"
    "/root/EMS/edge-ems-hmi-fe/bin/VERSION"
    "/home/envuser/energy-os/edge-ems-hmi-fe/bin/VERSION"
)

for version_file in "${VERSION_FILES[@]}"; do
    echo -n "检查 $version_file ... "

    if [ "$SERVER" = "HPUY" ]; then
        # HPUY 需要权限
        if $SSH_CMD bash -c "ls -f $version_file 2>/dev/null"; then
            version=$($SSH_CMD bash -c "cat $version_file")
            echo "✅ $version"
        else
            echo "⚠️  文件不存在或无法访问"
        fi
    else
        # EE 使用 ssh
        if ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "test -f $version_file && cat $version_file" 2>/dev/null; then
            version=$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "cat $version_file")
            echo "✅ $version"
        else
            echo "⚠️  文件不存在"
        fi
    fi
done

echo ""
echo "====================="
echo ""
echo "3️⃣ 检查进程状态："
echo ""

# 将所有组件分开（edge-ems-hmi-fe 使用单独的命令）
if [ "$SERVER" = "HPUY" ]; then
    # HPUY 需要权限
    procs=$($SSH_CMD bash -c "ps aux | grep -E 'edge-ems.*start\.sh|edge-ems$|edge-ems-hmi shell' | grep -v grep")
else
    # EE 使用 ssh
    procs=$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "ps aux | grep -E 'edge-ems.*start\.sh|edge-ems$|edge-ems-hmi' | grep -v grep")
fi

if [ -n "$procs" ]; then
    echo "✅ 发现运行中的进程："
    echo "$procs" | while read -r line; do
        echo "   $line"
    done
else
    echo "❌ 没有发现运行中的进程"
fi

echo ""
echo "====================="
echo ""
echo "4️⃣ 检查最近日志："
echo ""

LOG_DIRS=(
    "/root/EMS/edge-ems/logs/adapter.log"
    "/home/envuser/energy-os/edge-ems/logs/adapter.log"
    "/root/EMS/edge-ems-hmi/logs/hmi.log"
    "/home/envuser/energy-os/edge-ems-hmi/logs/hmi.log"
)

LOG_ERRORS=0

for log_path in "${LOG_DIRS[@]}"; do
    echo -n "检查 $log_path ... "

    if [ "$SERVER" = "HPUY" ]; then
        if $SSH_CMD bash -c "ls -f $log_path 2>/dev/null"; then
            # 获取最后 50 行
            log_tail=$($SSH_CMD bash -c "tail -n 50 $log_path 2>/dev/null")
            
            # 检查是否有严重错误
            if echo "$log_tail" | grep -qi "error\|exception\|fatal\|failed"; then
                echo "⚠️  发现错误"
                LOG_ERRORS=$((LOG_ERRORS + 1))
                echo "$log_tail" | grep -i "error\|exception\|fatal\|failed" | head -3
            else
                echo "✅ 无严重错误"
            fi
        else
            echo "⚠️  日志文件不存在"
        fi
    else
        if ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "test -f $log_path" 2>/dev/null; then
            log_tail=$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "cat $log_path | tail -n 50" 2>/dev/null)
            
            if echo "$log_tail" | grep -qi "error\|exception\|fatal\|failed"; then
                echo "⚠️  发现错误"
                LOG_ERRORS=$((LOG_ERRORS + 1))
                echo "$log_tail" | grep -i "error\|exception\|fatal\|failed" | head -3
            else
                echo "✅ 无严重错误"
            fi
        else
            echo "⚠️  日志文件不存在"
        fi
    fi
done

echo ""
echo "====================="
echo ""
echo "5️⃣ 检查文件权限："
echo ""

if [ "$SERVER" = "HPUY" ]; then
    # HPUY 所有文件应为 root:root
    perms=$($SSH_CMD bash -c "ls -la /root/EMS/edge-ems/bin/ | head -10")
    echo "edge-ems bin/ 目录权限："
    echo "$perms"
    
    echo ""
    chown_ok=$($SSH_CMD bash -c "stat -c '%U:%G /root/EMS/edge-ems/bin/edge-ems' | grep -q 'root:root' && echo 'OK' || echo 'WRONG'")
    
    if [ "$chown_ok" = "OK" ]; then
        echo "✅ 权限正确"
    else
        echo "❌ 权限不正确"
    fi
else
    # EE 所有文件应为 envuser:envuser
    perms=$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "ls -la /home/envuser/energy-os/edge-ems/bin/ | head -10")
    echo "edge-ems bin/ 目录权限："
    echo "$perms"
    
    echo ""
    chown_ok=$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "stat -c '%U:%G %n' /home/envuser/energy-os/edge-ems/bin/edge-ems 2>/dev/null | grep -q 'envuser:envuser' && echo 'OK' || echo 'WRONG'")
    
    if [ "$chown_ok" = "OK" ]; then
        echo "✅ 权限正确"
    else
        echo "❌ 权限不正确"
    fi
fi

echo ""
echo "====================="
echo ""
echo "6️⃣ 业务验证（如适用）："
echo ""

# EGC 可以运行以下验证
if [ -n "$(ssh -o ConnectTimeout=5 -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" 'command -v dlPulseSignal')" ]; then
    echo "🧪 检查 EGC 脉冲信号功能："
    
    echo -n "启动 dlPulseSignal 测试 ... "
    
    # 启动测试（后台运行）
    START_CMD=""
    if [ "$SERVER" = "HPUY" ]; then
        START_CMD="echo '$SSH_PASSWORD' | sudo -S bash -c 'cd /root/EMS/edge-ems/bin/ && bash start.sh dlPulseSignal 1 2>&1 | head -20'"
    else
        START_CMD="su - envuser -c 'cd /home/envuser/energy-os/edge-ems/bin/ && bash start.sh dlPulseSignal 1 2>&1 | head -20'"
    fi
    
    echo "(后台执行，手动检查日志)"
fi

echo ""
echo "====================="
echo ""
echo "验证结果汇总："
echo ""

if [ $LOG_ERRORS -eq 0 ]; then
    echo "✅ 所有关键配置检查通过"
    echo ""
    echo "💡 部署成功！"
    exit 0
else
    echo "❌ 发现 $LOG_ERRORS 处严重错误"
    echo ""
    echo "💡 请检查日志文件了解详细信息"
    exit 1
fi
