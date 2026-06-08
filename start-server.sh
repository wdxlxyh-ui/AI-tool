#!/bin/bash
PORT=${1:-8080}
DIR=${2:-/root/EGC}
echo "=================================="
echo "  AI 工具集服务器 (Flask)"
echo "=================================="
echo ""
echo "工作目录: $DIR"
echo "本机地址:  http://localhost:$PORT"
echo ""
# 获取本机IP
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$IP" ]; then
  echo "局域网访问: http://$IP:$PORT"
fi
echo ""
echo "登录账号: admin / admin123"
echo ""
echo "systemctl 管理:"
echo "  systemctl status egc-server   # 查看状态"
echo "  systemctl restart egc-server  # 重启服务"
echo "  systemctl stop egc-server     # 停止服务"
echo ""
echo "日志: tail -f /var/log/egc-server.log"
echo "=================================="
echo ""
cd "$DIR" && exec python3 run.py --port "$PORT"
