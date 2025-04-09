#!/bin/sh
set -e  # Exit on error

# Run the setup script
python /app/setup.py

# Start the API
exec uvicorn chat_api:app --reload --host 0.0.0.0 --port 8005 