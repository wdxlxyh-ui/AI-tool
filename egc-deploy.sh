#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  EGC AI Tool Collection — 一键打包 & 部署脚本
#  用法:
#    源服务器（打包）:
#      bash egc-deploy.sh pack          → 生成 egc-bundle.tar.gz
#
#    目标服务器（部署）:
#      把 egc-bundle.tar.gz 传到目标服务器，然后:
#      bash egc-deploy.sh deploy egc-bundle.tar.gz
#
#    或直接快速启动（不装 systemd）:
#      bash egc-deploy.sh quick         → 前台直接运行
# ============================================================

PACKAGE="egc-bundle.tar.gz"
PROJECT="EGC"
VERSION="1.0"

# ── 颜色 ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*" >&2; exit 1; }

# ──────── 打包 ────────
do_pack() {
    local src_dir; src_dir="$(cd "$(dirname "$0")" && pwd)"
    local out_dir="${2:-.}"

    info "源目录: $src_dir"
    info "打包中..."

    # 排除不需要带到目标服务器的文件
    tar czf "$out_dir/$PACKAGE" \
        -C "$(dirname "$src_dir")" \
        --exclude="$PROJECT/.git" \
        --exclude="$PROJECT/.sisyphus" \
        --exclude="$PROJECT/__pycache__" \
        --exclude="$PROJECT/**/__pycache__" \
        --exclude="$PROJECT/*.tar.gz" \
        --exclude="$PROJECT/node_modules" \
        "$PROJECT"

    # 把脚本自己加进去
    if [ -f "$src_dir/egc-deploy.sh" ]; then
        cp "$src_dir/egc-deploy.sh" "$out_dir/egc-deploy.sh"
    fi

    info "生成完毕: $(ls -lh "$out_dir/$PACKAGE" | awk '{print $5}') $out_dir/$PACKAGE"
    info "部署方式:"
    info "  1. 把 $PACKAGE 和 egc-deploy.sh 传到目标服务器"
    info "  2. 目标服务器上运行: bash egc-deploy.sh deploy $PACKAGE"
}

# ──────── 部署 ────────
do_deploy() {
    local tarball="$1"

    [ -f "$tarball" ] || err "找不到打包文件: $tarball"
    [ -n "${SUDO_USER:-}" ] && warn "当前通过 sudo 执行，服务将以 root 用户运行"

    local deploy_dir; deploy_dir="$(pwd)/$PROJECT"
    local port="${PORT:-8080}"

    info "=================================="
    info "  EGC AI Tool Collection 部署"
    info "=================================="

    # 1. 解压
    info "[1/5] 解压项目文件 → $deploy_dir"
    mkdir -p "$deploy_dir"
    tar xzf "$tarball" -C "$(dirname "$deploy_dir")"
    info "      大小: $(du -sh "$deploy_dir" | awk '{print $1}')"

    # 2. 检测 Python
    info "[2/5] 检测 Python 环境"
    local python_cmd=""
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            python_cmd="$cmd"
            break
        fi
    done
    [ -z "$python_cmd" ] && err "未安装 Python 3，请先安装: apt install python3"

    local pyver; pyver=$($python_cmd --version 2>&1)
    info "      $pyver"

    # 3. 安装 Flask
    info "[3/5] 安装 Flask"
    if $python_cmd -c "import flask" 2>/dev/null; then
        local fver; fver=$($python_cmd -c "import flask; print(f'Flask {flask.__version__}')" 2>/dev/null || echo "已安装")
        info "      $fver（跳过安装）"
    else
        info "      正在安装..."
        # 优先用 pip，失败则 fallback 到系统包
        if command -v pip3 &>/dev/null; then
            pip3 install flask -q
        elif command -v pip &>/dev/null; then
            pip install flask -q
        else
            # 试试系统包管理器
            if command -v apt-get &>/dev/null; then
                apt-get update -qq && apt-get install -y -qq python3-flask
            elif command -v yum &>/dev/null; then
                yum install -y -q python3-flask
            else
                err "无法安装 Flask，请手动执行: pip3 install flask"
            fi
        fi
        info "      Flask 安装完成"
    fi

    # 4. 配置 systemd 服务
    info "[4/5] 注册系统服务"
    local service_file="/etc/systemd/system/egc-server.service"
    cat > "$service_file" << UNIT
[Unit]
Description=EGC AI Tool Collection Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$deploy_dir
ExecStart=/usr/bin/$python_cmd $deploy_dir/run.py --port $port
Restart=always
RestartSec=5
StandardOutput=append:/var/log/egc-server.log
StandardError=append:/var/log/egc-server.log

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    systemctl enable egc-server
    info "      服务已注册: egc-server"

    # 5. 启动
    info "[5/5] 启动服务"
    systemctl restart egc-server
    sleep 2

    # 验证
    if systemctl is-active --quiet egc-server; then
        local ip; ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        info "=================================="
        info "  部署成功！"
        info "  本机:     http://localhost:$port"
        [ -n "$ip" ] && info "  局域网:   http://$ip:$port"
        info "  账号:     admin / admin123"
        info "=================================="
        info "  管理命令:"
        info "    systemctl status  egc-server    # 查看状态"
        info "    systemctl restart egc-server    # 重启"
        info "    systemctl stop    egc-server    # 停止"
        info "    tail -f /var/log/egc-server.log # 查看日志"
    else
        err "服务启动失败，请检查: journalctl -u egc-server --no-pager -n 30"
    fi
}

# ──────── 快速启动（不装 systemd）────────
do_quick() {
    local port="${PORT:-8080}"
    info "快速启动模式 (Ctrl+C 停止)"
    info "URL: http://localhost:$port"
    cd "$(dirname "$0")" && python3 run.py --port "$port"
}

# ──────── 入口 ────────
case "${1:-}" in
    pack)
        do_pack "$@"
        ;;
    deploy)
        [ -n "${2:-}" ] || err "用法: bash $0 deploy <tar.gz 文件>"
        do_deploy "$2"
        ;;
    quick)
        do_quick
        ;;
    *)
        echo "EGC Deploy Tool v$VERSION"
        echo ""
        echo "用法:"
        echo "  bash $0 pack                在当前目录生成部署包"
        echo "  bash $0 deploy <包名>       在目标服务器部署"
        echo "  bash $0 quick               前台快速启动（调试用）"
        echo ""
        echo "示例:"
        echo "  # 源服务器:"
        echo "  bash egc-deploy.sh pack"
        echo ""
        echo "  # 把 egc-bundle.tar.gz + egc-deploy.sh 传到目标服务器"
        echo "  # 目标服务器:"
        echo "  bash egc-deploy.sh deploy egc-bundle.tar.gz"
        ;;
esac
