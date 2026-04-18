# Scaling Preparation

This document describes scaling strategies and preparation for the Retrosheet Prediction Warehouse.

## Overview

The warehouse should be designed to scale horizontally to handle increased load and data volume.

## Scaling Dimensions

### Vertical Scaling (Scale Up)

**Current:**
- Application: 4 cores, 16 GB RAM
- Database: 8 cores, 32 GB RAM

**Scaled:**
- Application: 16 cores, 64 GB RAM
- Database: 32 cores, 128 GB RAM

**When to Use:**
- Single-server deployment
- Simple scaling needs
- Limited budget

**Pros:**
- Simple to implement
- No distributed system complexity
- Lower operational overhead

**Cons:**
- Single point of failure
- Limited maximum capacity
- Expensive at high end

### Horizontal Scaling (Scale Out)

**Current:**
- Application: 1 server
- Database: 1 primary

**Scaled:**
- Application: 10 servers
- Database: 1 primary + 5 replicas

**When to Use:**
- High availability requirements
- Large user base
- Need for redundancy

**Pros:**
- High availability
- Better fault tolerance
- More cost-effective at scale

**Cons:**
- Increased complexity
- Distributed system challenges
- Higher operational overhead

## Application Scaling

### Stateless Design

**Current State:**
- Prediction serving is stateless
- Model caching is in-memory

**Scaling Strategy:**
1. Deploy multiple application servers
2. Use load balancer (Nginx/HAProxy)
3. Share model cache via Redis
4. Use database connection pooling

**Implementation:**
```python
# Load balancer configuration (Nginx)
upstream retrosheet_api {
    server app1.example.com:8000;
    server app2.example.com:8000;
    server app3.example.com:8000;
    least_conn;
}

server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://retrosheet_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Auto-scaling

**Trigger Conditions:**
- CPU > 70% for 5 minutes
- Memory > 80% for 5 minutes
- Request queue > 100

**Scale Policy:**
- Add 1 server when triggered
- Maximum 10 servers
- Cooldown 10 minutes
- Remove idle servers after 30 minutes

**Implementation:**
```yaml
# Kubernetes Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: retrosheet-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: retrosheet-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Caching Strategy

**Current:**
- In-memory model cache per server

**Scaled:**
- Redis shared cache
- CDN for static assets
- Database query cache

**Implementation:**
```python
# Redis cache configuration
import redis

cache = redis.Redis(
    host='redis.example.com',
    port=6379,
    db=0,
    decode_responses=True
)

def get_model_cached(model_id):
    """Get model from Redis cache."""
    cache_key = f"model:{model_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return joblib.loads(cached)
    
    # Load from disk and cache
    model = load_model_from_disk(model_id)
    cache.set(cache_key, joblib.dumps(model), ex=3600)
    return model
```

## Database Scaling

### Read Replicas

**Current:**
- Single database server

**Scaled:**
- 1 primary + 5 read replicas

**Use Cases:**
- Read-heavy workloads
- Analytics queries
- Reporting

**Implementation:**
```sql
-- Configure streaming replication
-- On primary
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET wal_keep_size = '1GB';

-- Create replication user
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'password';
GRANT REPLICATION ON DATABASE retrosheet TO replicator;

-- On replica
ALTER SYSTEM SET hot_standby = on;
```

### Connection Pooling

**Current:**
- Individual connections per request

**Scaled:**
- Connection pool per application server
- PgBouncer for connection management

**Implementation:**
```python
# Connection pool configuration
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url(),
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=3600,
)
```

### Query Optimization

**Current:**
- Basic indexes on primary keys

**Scaled:**
- Composite indexes for common queries
- Partial indexes for filtered queries
- Materialized views for complex queries

**Implementation:**
```sql
-- Composite index for feature queries
CREATE INDEX idx_features_pa_season
    ON features.plate_appearance_advanced_examples
    (plate_appearance_id, feature_season);

-- Partial index for recent data
CREATE INDEX idx_events_recent
    ON core.events(game_id, inning)
    WHERE game_date >= CURRENT_DATE - INTERVAL '1 year';

-- Materialized view for aggregated stats
CREATE MATERIALIZED VIEW mv_daily_stats AS
SELECT
    game_date,
    COUNT(*) AS games,
    AVG(home_score + away_score) AS avg_runs
FROM core.games
GROUP BY game_date;
```

## Feature Store Scaling

### DuckDB Integration

**Purpose:** Offload analytical queries to DuckDB

**Use Cases:**
- Large-scale aggregations
- Feature backfilling
- Historical analysis

**Implementation:**
```python
import duckdb

# Connect to DuckDB
con = duckdb.connect('feature_store.duckdb')

# Export from PostgreSQL to DuckDB
con.execute("""
    COPY (
        SELECT * FROM features.plate_appearance_advanced_examples
    ) TO 'features.parquet' (FORMAT PARQUET);
""")

# Query in DuckDB
result = con.execute("""
    SELECT
        inning,
        AVG(outs_before) AS avg_outs
    FROM read_parquet('features.parquet')
    GROUP BY inning
""").fetchall()
```

### Redis Integration

**Purpose:** Cache frequently accessed features

**Use Cases:**
- Live game state
- Player career stats
- Team form statistics

**Implementation:**
```python
# Cache live game state
def cache_live_game_state(game_id, state):
    cache_key = f"live_game:{game_id}"
    cache.set(cache_key, json.dumps(state), ex=300)  # 5 minute TTL

def get_cached_live_game_state(game_id):
    cache_key = f"live_game:{game_id}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)
    return None
```

## Model Serving Scaling

### Batch Prediction

**Current:**
- Individual predictions

**Scaled:**
- Batch predictions for efficiency
- GPU acceleration for large batches

**Implementation:**
```python
def predict_batch(frames, model, batch_size=100):
    """Make predictions in batches."""
    results = []
    
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        
        # Extract features
        features = extract_features_batch(batch)
        
        # Batch prediction
        probabilities = model.predict_proba(features)
        
        # Process results
        for j, prob in enumerate(probabilities):
            results.append({
                'plate_appearance_id': batch[j]['plate_appearance_id'],
                'probabilities': dict(zip(model.classes_, prob))
            })
    
    return results
```

### Model Versioning

**Current:**
- Single active model

**Scaled:**
- Multiple model versions
- A/B testing
- Canary deployments

**Implementation:**
```python
# A/B testing
def predict_with_ab_test(game_id, pa_id, model_a_id, model_b_id, split=0.5):
    """Predict with A/B testing."""
    import random
    
    if random.random() < split:
        return predict_pa_outcome_distribution(
            game_id=game_id,
            plate_appearance_id=pa_id,
            model_id=model_a_id
        )
    else:
        return predict_pa_outcome_distribution(
            game_id=game_id,
            plate_appearance_id=pa_id,
            model_id=model_b_id
        )
```

## Data Ingestion Scaling

### Parallel Processing

**Current:**
- Sequential year processing

**Scaled:**
- Parallel year processing
- Multi-threaded extraction
- Concurrent loading

**Implementation:**
```python
from concurrent.futures import ThreadPoolExecutor

def process_year(year):
    """Process a single year."""
    extract_chadwick(years=[year])
    load_chadwick(years=[year])

# Process multiple years in parallel
years = range(2000, 2025)
with ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(process_year, years)
```

### Streaming Ingestion

**Current:**
- Batch loading after extraction

**Scaled:**
- Streaming load during extraction
- Real-time processing
- Reduced memory footprint

**Implementation:**
```python
# Stream data during extraction
def stream_load(extracted_file):
    """Stream extracted data to database."""
    with open(extracted_file) as f:
        reader = csv.DictReader(f)
        
        # Process in chunks
        chunk = []
        for row in reader:
            chunk.append(row)
            
            if len(chunk) >= 1000:
                load_chunk(chunk)
                chunk = []
        
        # Load remaining
        if chunk:
            load_chunk(chunk)
```

## Monitoring Scaling

### Metrics Collection

**Current:**
- Basic system metrics

**Scaled:**
- Application metrics
- Database metrics
- Business metrics
- Custom metrics

**Implementation:**
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
prediction_counter = Counter('predictions_total', 'Total predictions')
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
active_models = Gauge('active_models', 'Number of active models')

# Use metrics
@prediction_latency.time()
def predict_pa_outcome_distribution(...):
    prediction_counter.inc()
    # ... prediction logic
```

### Alert Scaling

**Current:**
- Email alerts

**Scaled:**
- PagerDuty for critical alerts
- Slack for warnings
- Webhook for custom integrations

**Implementation:**
```yaml
# AlertManager configuration
receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: <PAGERDUTY_KEY>
      severity: critical
  
  - name: slack
    slack_configs:
      - api_url: <SLACK_WEBHOOK>
      channel: '#alerts'
      severity: warning
```

## Cost Optimization

### Reserved Instances

**Strategy:**
- Use reserved instances for baseline load
- Use spot instances for burst capacity
- Auto-scale between reserved and spot

**Savings:**
- Reserved: 50-70% discount
- Spot: 70-90% discount

### Right-sizing

**Strategy:**
- Monitor resource utilization
- Downsize over-provisioned resources
- Use burstable instances for low-load services

**Implementation:**
```bash
# Monitor utilization
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=retrosheet-api \
    --period 3600 \
    --statistics Average

# Right-size based on utilization
aws ec2 modify-instance-attribute \
    --instance-id i-1234567890abcdef0 \
    --attribute-type instanceType \
    --attribute-value t3.medium
```

## Disaster Recovery Scaling

### Multi-Region Deployment

**Strategy:**
- Deploy to multiple regions
- DNS failover
- Data replication

**Implementation:**
```yaml
# Route53 health checks
type: A
alias:
  name: retrosheet-api.example.com
  type: CNAME
  evaluate-target-health: true
  records:
    - region1.example.com
    - region2.example.com
```

### Data Replication

**Strategy:**
- Cross-region replication
- Point-in-time recovery
- Backup to separate region

**Implementation:**
```bash
# Configure cross-region replication
aws rds create-db-instance-read-replica \
    --source-db-instance-identifier retrosheet-prod \
    --db-instance-identifier retrosheet-replica \
    --availability-zone us-west-2a
```

## Scaling Roadmap

### Phase 1: Basic Scaling (1-3 months)
- [ ] Add connection pooling
- [ ] Implement Redis caching
- [ ] Add read replicas for database
- [ ] Set up load balancer

### Phase 2: Auto-scaling (3-6 months)
- [ ] Implement application auto-scaling
- [ ] Set up monitoring and alerting
- [ ] Implement batch prediction
- [ ] Optimize database queries

### Phase 3: Advanced Scaling (6-12 months)
- [ ] Deploy to multiple regions
- [ ] Implement DuckDB analytics
- [ ] Set up GPU acceleration
- [ ] Implement model A/B testing

### Phase 4: Optimization (ongoing)
- [ ] Right-sizing based on metrics
- [ ] Cost optimization
- [ ] Performance tuning
- [ ] Capacity planning

## Testing

### Load Testing

**Tools:**
- Locust
- k6
- Apache Bench

**Test Scenarios:**
- 100 predictions/second
- 1000 predictions/second
- 10000 predictions/second

**Validation:**
- Latency < 100ms P95
- Error rate < 1%
- No memory leaks

### Stress Testing

**Test Scenarios:**
- Sustained high load
- Spike traffic
- Database connection exhaustion

**Validation:**
- System remains stable
- Graceful degradation
- Automatic recovery

## Next Steps

1. Assess current capacity and growth projections
2. Implement connection pooling
3. Set up Redis caching
4. Add database read replicas
5. Configure load balancer
6. Implement auto-scaling
7. Set up monitoring and alerting
8. Conduct load testing
9. Optimize based on results
10. Plan for future growth
