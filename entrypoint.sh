#!/bin/bash

# DPDNS Renewal Container Entrypoint Script

echo "Starting DPDNS renewal script..."

# Detect which script to use
if [ -f "/app/dpdns_renew_drission.py" ]; then
    SCRIPT="/app/dpdns_renew_drission.py"
else
    echo "Error: Renewal script not found"
    exit 1
fi

# Run script with xvfb-run
xvfb-run -a --server-args="-screen 0 1920x1080x24 -ac +extension GLX +render -noreset" python3 "$SCRIPT"

# Save exit code
EXIT_CODE=$?

# If AUTO_MODE is set, keep container running (for cron jobs)
if [ "$AUTO_MODE" = "true" ] && [ "$EXIT_CODE" -eq 0 ]; then
    echo "Renewal completed, container keeps running (use crontab for scheduled tasks)"
    # Keep container running
    tail -f /dev/null
else
    # Exit directly
    exit $EXIT_CODE
fi
