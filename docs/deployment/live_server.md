# Live Prediction Server Deployment Guide

Deploy the MLB Live Prediction WebSocket server for production use.

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Optional: `websockets` package (`uv add websockets`)
- Trained models in `data/models/` or database registry

## Local Testing

### 1. Start the Server

```bash
# Quick test with auto-reload
cd /home/cbwinslow/workspace/retrosheet
baseball live server --host localhost --port 8765 --interval 10
```

### 2. Verify with Dashboard

```bash
# Terminal 2
cd dashboard
python3 -m http.server 8080

# Open http://localhost:8080 in browser
# Click Connect to ws://localhost:8765
```

### 3. Run E2E Tests

```bash
# Quick tests (5 seconds)
uv run python scripts/test_live_pipeline.py --quick

# Full tests including WebSocket integration (30 seconds)
uv run python scripts/test_live_pipeline.py
```

## Production Deployment

### Option 1: Systemd Service (Recommended)

Create `/etc/systemd/system/mlb-live-server.service`:

```ini
[Unit]
Description=MLB Live Prediction Server
After=network.target postgresql.service

[Service]
Type=simple
User=mlb
Group=mlb
WorkingDirectory=/opt/retrosheet
Environment=PYTHONPATH=/opt/retrosheet
Environment=PGHOST=localhost
Environment=PGPORT=5432
Environment=PGDATABASE=retrosheet
Environment=PGUSER=mlb
Environment=PGPASSWORD=secret
ExecStart=/opt/retrosheet/.venv/bin/python -m mlb_predict.streaming.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable mlb-live-server
sudo systemctl start mlb-live-server
sudo systemctl status mlb-live-server
```

### Option 2: Docker

Create `Dockerfile.live`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PGHOST=${PGHOST}
ENV PGPORT=${PGPORT}
ENV PGDATABASE=${PGDATABASE}
ENV PGUSER=${PGUSER}
ENV PGPASSWORD=${PGPASSWORD}

EXPOSE 8765

CMD ["python", "-m", "mlb_predict.streaming.server"]
```

Build and run:

```bash
docker build -f Dockerfile.live -t mlb-live-server .
docker run -p 8765:8765 \
  -e PGHOST=host.docker.internal \
  -e PGPASSWORD=secret \
  mlb-live-server
```

### Option 3: Process Manager (PM2)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
pm2 ecosystem
```

Edit `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'mlb-live-server',
    script: 'python',
    args: '-m mlb_predict.streaming.server',
    cwd: '/opt/retrosheet',
    env: {
      PYTHONPATH: '/opt/retrosheet',
      PGHOST: 'localhost',
      PGDATABASE: 'retrosheet',
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
  }],
};
```

Start:

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Nginx Reverse Proxy (WebSocket Support)

For public-facing deployments, use Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name cloudcurio.cc www.cloudcurio.cc predictions.cloudcurio.cc;

    location / {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeouts
        proxy_read_timeout 86400;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/mlb-live /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d cloudcurio.cc -d www.cloudcurio.cc -d predictions.cloudcurio.cc

# Auto-renewal is configured automatically
```

## Monitoring

### Health Check Endpoint

Add to your monitoring system:

```bash
# Check if server is responding
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Host: localhost:8765" \
  -H "Origin: http://localhost:8765" \
  http://localhost:8765
```

Or use WebSocket client:

```python
import asyncio
from mlb_predict.streaming import PredictionStreamClient

async def health_check():
    client = PredictionStreamClient("ws://localhost:8765")
    try:
        await asyncio.wait_for(client.connect(), timeout=5.0)
        print("✅ Server healthy")
        await client.disconnect()
        return True
    except:
        print("❌ Server unhealthy")
        return False

asyncio.run(health_check())
```

### Prometheus Metrics (Future)

The server exposes metrics via `get_stats()`:

```python
{
    "connected_clients": 42,
    "active_subscriptions": 15,
    "games_being_tracked": [12345, 12346],
    "pipeline_metrics": {
        "predictions_made": 1250,
        "cache_hit_rate": 0.85,
        "avg_latency_ms": 8.5,
    },
}
```

## Performance Tuning

### Database Connection Pool

Increase pool size for high traffic:

```python
# In mlb_predict/pipeline/model_manager.py
self.db_pool = SimpleConnectionPool(
    minconn=5,      # Increase from 1
    maxconn=50,     # Increase from 10
    **self._database_kwargs(),
)
```

### Polling Intervals

Adjust based on game status:

```python
# Current implementation
POLL_INTERVALS = {
    'Preview': 300,   # 5 min before game
    'Warmup': 60,     # 1 min before game
    'Live': 10,       # 10 sec during game
    'Delayed': 60,    # 1 min if delayed
    'End': 300,       # 5 min after game
}
```

### Caching Strategy

- Feature cache TTL: 5 seconds (default)
- Prediction cache TTL: 5 seconds (default)
- LRU eviction: 1000 games max

## Troubleshooting

### High Memory Usage

Check for memory leaks:

```bash
# Monitor RSS
ps aux | grep python | grep -v grep

# Check cache sizes
python3 << 'EOF'
from mlb_predict.pipeline import LivePredictionPipeline
p = LivePredictionPipeline()
print(p.get_metrics())
EOF
```

### Connection Errors

```bash
# Check open file limits
ulimit -n

# Increase if needed
ulimit -n 65535
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Verify connection
check_postgres_connection --db retrosheet
```

## Security Considerations

1. **Firewall**: Only expose port 80/443 to internet
2. **Authentication**: Add API key validation for production
3. **Rate Limiting**: Implement per-client rate limits
4. **CORS**: Configure allowed origins
5. **Input Validation**: Validate all game_pk inputs

## Scaling

### Horizontal Scaling

For multiple servers behind load balancer:

1. Use Redis for shared state (future enhancement)
2. Sticky sessions for WebSocket connections
3. Separate read replicas for database queries

### Vertical Scaling

- 2 CPU cores: ~100 concurrent connections
- 4 CPU cores: ~250 concurrent connections
- 8 CPU cores: ~500 concurrent connections

## Backup and Recovery

### Database

Regular PostgreSQL backups:

```bash
pg_dump retrosheet > retrosheet_$(date +%Y%m%d).sql
gzip retrosheet_$(date +%Y%m%d).sql
```

### Models

Backup trained models:

```bash
tar czf models_$(date +%Y%m%d).tar.gz data/models/
```

## Related

- `mlb_predict/streaming/server.py` - Server implementation
- `dashboard/README.md` - Dashboard setup
- `docs/agents/live_agent.md` - Architecture documentation
