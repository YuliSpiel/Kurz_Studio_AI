# Celery Worker Setup Guide

## ⚠️ CRITICAL: Worker Pool Configuration

**The Celery worker MUST use a parallel pool (gevent or prefork) for the asset generation pipeline to work correctly.**

### Why This Matters

AutoShorts uses Celery's `chord` pattern to execute asset generation tasks in parallel:
```python
# This requires parallel execution!
chord(
    group(
        designer_task.s(run_id, json_path, spec),   # Image generation
        composer_task.s(run_id, json_path, spec),   # Music generation
        voice_task.s(run_id, json_path, spec),      # TTS generation
    )
)(director_task.s(run_id, json_path))  # Video composition callback
```

If you use `--pool=solo`, all tasks execute **sequentially**, not in parallel:
- ❌ Total time: ~27 seconds (3 tasks × 9s each)
- ✅ Total time: ~9 seconds (3 tasks in parallel)

---

## Recommended Configuration

### Option 1: Gevent Pool (Recommended for macOS)

**Advantages:**
- Best for I/O-bound tasks (API calls, file operations)
- Stable on macOS
- Lower memory footprint
- Excellent for concurrent API requests

**Installation:**
```bash
cd backend
pip install gevent
```

**Start Worker:**
```bash
cd backend
./start_worker.sh
```

Or manually:
```bash
cd backend
python -m celery -A app.celery_app worker \
    --loglevel=info \
    --pool=gevent \
    --concurrency=10
```

### Option 2: Prefork Pool (Alternative)

**Advantages:**
- Best for CPU-bound tasks
- More process isolation

**Start Worker:**
```bash
cd backend
python -m celery -A app.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=4
```

**Note:** May have issues on macOS. Use gevent if you encounter problems.

---

## ❌ What NOT to Use

### Solo Pool (Debugging Only)

**NEVER use `--pool=solo` in production or normal development!**

```bash
# ❌ DO NOT USE THIS (except for debugging)
python -m celery -A app.celery_app worker --pool=solo
```

**When to use solo:**
- Only for debugging single tasks
- Testing task logic in isolation
- Never for the full pipeline with chords

---

## Verification

### Check Worker Configuration

When you start the worker, you should see:
```
[config]
.> pool:         gevent (greenlets=10)
```

If you see `pool: solo`, **STOP and restart with the correct configuration!**

### Test Parallel Execution

Create a test run and check the logs:
```
[designer] Starting...  (timestamp: 0s)
[composer] Starting...  (timestamp: 0s)
[voice] Starting...     (timestamp: 0s)
```

If tasks start at the same timestamp, they're running in parallel. ✅

If they start sequentially (0s, 9s, 18s), you're using solo pool. ❌

---

## Troubleshooting

### "Pool type 'gevent' not available"
```bash
pip install gevent
```

### Tasks still running sequentially
1. Check worker logs for pool type
2. Restart worker with correct pool
3. Verify concurrency > 1

### macOS "fork safety" warnings
- Use gevent instead of prefork
- These warnings are expected with prefork on macOS

---

## Production Deployment

For production, use a process manager:

### Option 1: systemd (Linux)
```ini
[Unit]
Description=AutoShorts Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
WorkingDirectory=/app/backend
ExecStart=/app/backend/start_worker.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 2: supervisord
```ini
[program:autoshorts-worker]
command=/app/backend/start_worker.sh
directory=/app/backend
user=www-data
autostart=true
autorestart=true
```

---

## Quick Reference

| Pool Type | Use Case | Command |
|-----------|----------|---------|
| `gevent` | **Recommended** (I/O-bound, macOS) | `./start_worker.sh` |
| `prefork` | CPU-bound tasks | `celery -A app.celery_app worker --pool=prefork --concurrency=4` |
| `solo` | **Debugging only** | `celery -A app.celery_app worker --pool=solo` |

---

## Related Documentation

- [WORKFLOW.md](./WORKFLOW.md) - Pipeline architecture
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [Celery Documentation](https://docs.celeryq.dev/en/stable/userguide/workers.html#concurrency)
