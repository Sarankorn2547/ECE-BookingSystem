#!/bin/bash
set -e

# Pass current environment variables to cron (cron doesn't inherit them)
printenv | grep -v "no_proxy\|_=" >> /etc/environment

# Write the crontab: run send_reminders every day at 07:00 Bangkok time
echo "0 7 * * * root cd /app && python manage.py send_reminders >> /var/log/cron.log 2>&1" \
    > /etc/cron.d/ece-reminders
chmod 0644 /etc/cron.d/ece-reminders
crontab /etc/cron.d/ece-reminders

echo "[cron] ECE reminder cron started — runs daily at 07:00 (Asia/Bangkok)"

# Keep container alive by running cron in foreground
exec cron -f
