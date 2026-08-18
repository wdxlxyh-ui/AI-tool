#!/bin/bash
log_path="filetest.log"
log_with_date() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] - $message" >> "$log_path"
}


# 检查日志文件是否存在
if [ -f "$log_path" ]; then
    log_with_date "开始测试"
else
    log_with_date "创建日志文件并开始测试"
fi


while true; do
    # 确保update_file.sh脚本存在且可执行
    if [ -x "updatefile.sh" ]; then
        bash updatefile.sh
    else
        log_with_date "更新脚本update_file.sh不存在或无法执行"
        break
    fi
    sleep 1800
done

