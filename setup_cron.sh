#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="/usr/bin/python3"
RESET_SCRIPT="$SCRIPT_DIR/backend/weekly_reset.py"
LOG_FILE="/var/log/weekly_reset.log"

sudo touch $LOG_FILE
sudo chmod 666 $LOG_FILE

CRON_JOB="5 0 * * 1 $PYTHON_PATH $RESET_SCRIPT >> $LOG_FILE 2>&1"

if crontab -l 2>/dev/null | grep -q "$RESET_SCRIPT"; then
    echo "Cron job already exists for weekly reset"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron job added successfully:"
    echo "$CRON_JOB"
fi

echo "Weekly reset cron job setup complete!"
echo "The script will run every Monday at 12:05 AM"
echo "Logs will be written to: $LOG_FILE"
