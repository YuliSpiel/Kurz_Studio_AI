#!/bin/bash
# Celery Worker Startup Script
# This script starts the Celery worker with the correct configuration for parallel task execution.
#
# IMPORTANT: DO NOT use --pool=solo as it disables parallel execution!
# The chord pattern for asset generation (designer, composer, voice) requires parallel execution.

set -e

echo "🚀 Starting Celery worker with gevent pool for parallel task execution..."
echo "📋 Configuration:"
echo "   - Pool: gevent (enables parallel chord execution)"
echo "   - Concurrency: 10 (simultaneous tasks)"
echo "   - Log level: info"
echo ""

cd "$(dirname "$0")"

# Start Celery worker with gevent pool
python -m celery -A app.celery_app worker \
    --loglevel=info \
    --pool=gevent \
    --concurrency=10

# Alternative configurations (commented out):
#
# For CPU-intensive tasks (prefork pool):
# python -m celery -A app.celery_app worker --loglevel=info --pool=prefork --concurrency=4
#
# For debugging (solo pool - NOT for production):
# python -m celery -A app.celery_app worker --loglevel=info --pool=solo
