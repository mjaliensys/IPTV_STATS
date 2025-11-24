# Stream Stats API

A FastAPI service that receives streaming events from multiple media servers, tracks active sessions in memory, and aggregates statistics into MySQL for Grafana dashboards.

## Overview

This service acts as a webhook receiver for streaming servers (e.g., Flussonic, Wowza). It processes `play_started` and `play_closed` events, maintains real-time concurrent viewer counts, and stores per-minute aggregated statistics.

**Key Features:**
- Real-time active session tracking (in-memory)
- Per-minute aggregation across multiple dimensions
- Crash recovery via periodic session persistence
- Single-dimension breakdowns: server, channel, country, protocol, device type
- MySQL storage optimized for Grafana time-series queries
- 3-year data retention capability

## Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Streaming       │     │ Streaming       │     │ Streaming       │
│ Server 1        │     │ Server 2        │     │ Server N        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ POST /api/webhook     │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Stream Stats API     │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │ Active Sessions  │  │  (in-memory)
                    │  │ Manager          │  │
                    │  └────────┬─────────┘  │
                    │           │            │
                    │  ┌────────▼─────────┐  │
                    │  │ Aggregator       │  │  (every minute)
                    │  └────────┬─────────┘  │
                    └───────────┼────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │       MySQL            │
                    │                        │
                    │  - stats_global        │
                    │  - stats_by_server     │
                    │  - stats_by_channel    │
                    │  - stats_by_country    │
                    │  - stats_by_protocol   │
                    │  - stats_by_user_agent │
                    │  - active_sessions     │
                    └────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │       Grafana          │
                    └────────────────────────┘
```

## Project Structure
```
stream_api/
├── app/
│   ├── __init__.py          # Package marker
│   ├── main.py              # FastAPI app, lifespan, scheduler
│   ├── config.py            # Configuration via environment variables
│   ├── database.py          # SQLAlchemy engine and session
│   ├── models.py            # Database table definitions
│   ├── schemas.py           # Pydantic models for request validation
│   ├── webhook.py           # POST /api/webhook endpoint
│   ├── sessions.py          # In-memory active sessions manager
│   ├── aggregator.py        # Per-minute stats aggregation
│   └── classifier.py        # User agent classification
├── requirements.txt         # Python dependencies
├── run.py                   # Uvicorn entry point
├── .env                     # Environment configuration (not in git)
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/webhook` | Receive streaming events (single or batched) |
| GET | `/health` | Health check for load balancers |
| GET | `/stats/active` | Current active session counts |

## Event Format

The service accepts JSON arrays of events:
```json
[
  {
    "time": "2025-11-24T11:10:26.498510Z",
    "event": "play_started",
    "id": "69243cdd-cab1-4849-b276-19819ff4b74c",
    "server": "au13.chiffra.com",
    "media": "7mate",
    "user_id": "134",
    "user_name": "7mate",
    "ip": "58.105.162.248",
    "country": "AU",
    "proto": "hls",
    "bytes": 1266744,
    "token": "591953da3efc46d39881d459f2e6717c",
    "source_id": "69243cd6-6dd3-4f7e-b228-8f65f388e3e6",
    "user_agent": "Lavf53.32.100",
    "opened_at": 1763982557616,
    "query_string": "token=591953da3efc46d39881d459f2e6717c"
  }
]
```

**Event types:** `play_started`, `play_closed`

**Additional fields for `play_closed`:** `closed_at`, `reason`

## Database Schema

**Metrics stored (all tables):**
- `sessions_started` - count of new sessions
- `sessions_closed` - count of ended sessions
- `total_bytes` - bytes transferred
- `bandwidth_bps` - bytes per second
- `watch_time_seconds` - total viewing time
- `unique_users` - distinct user_id count
- `peak_concurrent` - maximum simultaneous viewers

**Dimension tables:**
- `stats_global` - primary key: `minute`
- `stats_by_server` - primary key: `minute`, `server`
- `stats_by_channel` - primary key: `minute`, `channel`
- `stats_by_country` - primary key: `minute`, `country`
- `stats_by_protocol` - primary key: `minute`, `protocol`
- `stats_by_user_agent` - primary key: `minute`, `user_agent_class`

**User agent classes:** `android`, `ios`, `tv`, `stb`, `streaming_server`, `desktop`, `other`

## Configuration

Environment variables (prefix `STREAM_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAM_DB_HOST` | localhost | MySQL host |
| `STREAM_DB_PORT` | 3306 | MySQL port |
| `STREAM_DB_USER` | stream_api | MySQL user |
| `STREAM_DB_PASSWORD` | changeme | MySQL password |
| `STREAM_DB_NAME` | stream_stats | Database name |
| `STREAM_DB_POOL_SIZE` | 10 | Connection pool size |
| `STREAM_DB_POOL_OVERFLOW` | 20 | Max overflow connections |
| `STREAM_AGGREGATION_INTERVAL_SECONDS` | 60 | Aggregation frequency |
| `STREAM_SESSION_SYNC_INTERVAL_SECONDS` | 30 | Session persistence frequency |

---

## Setup Instructions (Ubuntu)

### Prerequisites

- Ubuntu 20.04+
- Python 3.10+
- MySQL 8.0+

### 1. Install System Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv mysql-server
```

### 2. Create MySQL Database
```bash
sudo mysql -u root << EOF
CREATE DATABASE stream_stats CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'stream_api'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON stream_stats.* TO 'stream_api'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 3. Create Application Directory
```bash
sudo mkdir -p /opt/stream_api
sudo chown $USER:$USER /opt/stream_api
cd /opt/stream_api
```

### 4. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Create Environment File
```bash
cat > /opt/stream_api/.env << EOF
STREAM_DB_HOST=localhost
STREAM_DB_PORT=3306
STREAM_DB_USER=stream_api
STREAM_DB_PASSWORD=your_secure_password
STREAM_DB_NAME=stream_stats
EOF

chmod 600 /opt/stream_api/.env
```

### 7. Test Run
```bash
cd /opt/stream_api
source venv/bin/activate
python run.py
```

Verify at: `http://localhost:5000/health`

---

## Install as Systemd Service

### 1. Create Service User
```bash
sudo useradd --system --no-create-home --shell /bin/false stream_api
sudo chown -R stream_api:stream_api /opt/stream_api
```

### 2. Create Systemd Unit File
```bash
sudo cat > /etc/systemd/system/stream-api.service << EOF
[Unit]
Description=Stream Stats API
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=stream_api
Group=stream_api
WorkingDirectory=/opt/stream_api
Environment="PATH=/opt/stream_api/venv/bin"
EnvironmentFile=/opt/stream_api/.env
ExecStart=/opt/stream_api/venv/bin/python run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/stream_api

[Install]
WantedBy=multi-user.target
EOF
```

### 3. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable stream-api
sudo systemctl start stream-api
```

### 4. Check Status
```bash
sudo systemctl status stream-api
sudo journalctl -u stream-api -f
```

### 5. Service Commands
```bash
# Stop
sudo systemctl stop stream-api

# Restart
sudo systemctl restart stream-api

# View logs
sudo journalctl -u stream-api -n 100

# View logs (follow)
sudo journalctl -u stream-api -f
```

---

## Testing

### Send Test Event
```bash
curl -X POST http://localhost:5000/api/webhook \
  -H "Content-Type: application/json" \
  -d '[{
    "time": "2025-11-24T11:10:26.498510Z",
    "event": "play_started",
    "id": "test-session-001",
    "server": "test-server",
    "media": "test-channel",
    "user_id": "user123",
    "user_name": "testuser",
    "ip": "192.168.1.1",
    "country": "AU",
    "proto": "hls",
    "bytes": 0,
    "token": "abc123",
    "source_id": "source-001",
    "user_agent": "TestAgent/1.0",
    "opened_at": 1732450000000,
    "query_string": "token=abc123"
  }]'
```

### Check Active Sessions
```bash
curl http://localhost:5000/stats/active
```

### Health Check
```bash
curl http://localhost:5000/health
```

---

## Grafana Integration

Connect Grafana directly to MySQL. Sample queries:
```sql
-- Concurrent viewers over time
SELECT minute as time, peak_concurrent 
FROM stats_global 
WHERE minute >= NOW() - INTERVAL 24 HOUR
ORDER BY minute;

-- Viewers by channel (last hour)
SELECT minute as time, channel, peak_concurrent
FROM stats_by_channel
WHERE minute >= NOW() - INTERVAL 1 HOUR
ORDER BY minute;

-- Total bandwidth (Mbps)
SELECT minute as time, bandwidth_bps / 1000000 as mbps
FROM stats_global
WHERE minute >= NOW() - INTERVAL 24 HOUR
ORDER BY minute;

-- Top countries
SELECT country, SUM(peak_concurrent) as total_viewers
FROM stats_by_country
WHERE minute >= NOW() - INTERVAL 1 HOUR
GROUP BY country
ORDER BY total_viewers DESC;
```

---

## Maintenance

### Data Retention

To delete old data (run periodically via cron):
```sql
DELETE FROM stats_global WHERE minute < NOW() - INTERVAL 3 YEAR;
DELETE FROM stats_by_server WHERE minute < NOW() - INTERVAL 3 YEAR;
DELETE FROM stats_by_channel WHERE minute < NOW() - INTERVAL 3 YEAR;
DELETE FROM stats_by_country WHERE minute < NOW() - INTERVAL 3 YEAR;
DELETE FROM stats_by_protocol WHERE minute < NOW() - INTERVAL 3 YEAR;
DELETE FROM stats_by_user_agent WHERE minute < NOW() - INTERVAL 3 YEAR;
```

### Backup
```bash
mysqldump -u stream_api -p stream_stats > backup_$(date +%Y%m%d).sql
```

---

## Troubleshooting

**Service won't start:**
```bash
sudo journalctl -u stream-api -n 50
```

**Database connection errors:**
- Verify MySQL is running: `sudo systemctl status mysql`
- Check credentials in `.env`
- Test connection: `mysql -u stream_api -p stream_stats`

**No data in stats tables:**
- Check if events are arriving: `curl http://localhost:5000/stats/active`
- Wait for aggregation (runs at :00 of each minute)
- Check logs: `sudo journalctl -u stream-api -f`

**High memory usage:**
- Check active session count
- Sessions should close automatically; if not, check streaming server configuration