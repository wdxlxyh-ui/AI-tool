#!/bin/bash
PORT=${1:-8080}
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=================================="
echo "  AI 工具集服务器 (Flask)"
echo "=================================="
echo ""
echo "工作目录: $DIR"
echo "本机地址:  http://localhost:$PORT"
echo ""
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$IP" ]; then
  echo "局域网访问: http://$IP:$PORT"
fi
echo ""
echo "登录账号: admin / admin123"
echo ""
echo "启动命令: cd $DIR && python3 run.py --port $PORT"
echo "=================================="
echo ""
cd "$DIR" && exec python3 run.py --port "$PORT"
