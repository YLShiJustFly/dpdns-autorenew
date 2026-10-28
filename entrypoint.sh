#!/bin/bash
set -uo pipefail

echo "[entrypoint] start $(date '+%F %T')"

if [ -f /app/dpdns_renew.py ]; then
    SCRIPT=/app/dpdns_renew.py
else
    echo "[entrypoint] 错误：找不到 /app/dpdns_renew.py"
    exit 1
fi

xvfb-run -a --server-args="-screen 0 1920x1080x24 -ac +extension GLX +render -noreset" \
    python3 "$SCRIPT"
EXIT_CODE=$?

echo "[entrypoint] exit=$EXIT_CODE"

# AUTO_MODE=true 时保持容器存活，交给外部 cron / docker 调度决定何时再跑
if [ "${AUTO_MODE:-false}" = "true" ]; then
    echo "[entrypoint] AUTO_MODE=true，容器保持运行"
    tail -f /dev/null
fi

exit $EXIT_CODE
