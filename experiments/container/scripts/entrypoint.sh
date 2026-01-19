#!/bin/sh
set -e

/usr/local/bin/generate-certificate /usr/local/apache2
/usr/local/bin/check-low-port

# Start the management API in background
/app/venv/bin/python /app/api/main.py &

# Start Apache in foreground
exec /usr/local/apache2/bin/httpd -DFOREGROUND
