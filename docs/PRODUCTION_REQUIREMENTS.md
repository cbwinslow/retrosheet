# Production Environment Requirements

This document defines the requirements for deploying the Retrosheet Prediction Warehouse to production.

## Overview

The production environment must support data ingestion, model training, prediction serving, and monitoring with high availability and reliability.

## Hardware Requirements

### Minimum Configuration

**Application Server:**
- CPU: 4 cores
- RAM: 16 GB
- Storage: 100 GB SSD
- Network: 1 Gbps

**Database Server:**
- CPU: 8 cores
- RAM: 32 GB
- Storage: 500 GB SSD (for database)
- Network: 1 Gbps

### Recommended Configuration

**Application Server:**
- CPU: 8 cores
- RAM: 32 GB
- Storage: 200 GB SSD
- Network: 10 Gbps

**Database Server:**
- CPU: 16 cores
- RAM: 64 GB
- Storage: 1 TB SSD (for database)
- Network: 10 Gbps

### High Availability Configuration

**Application Servers (3 nodes):**
- CPU: 8 cores each
- RAM: 32 GB each
- Storage: 200 GB SSD each
- Network: 10 Gbps each
- Load balancer in front

**Database Servers (Primary + 2 Replicas):**
- CPU: 16 cores each
- RAM: 64 GB each
- Storage: 1 TB SSD each
- Network: 10 Gbps each
- Streaming replication

## Software Requirements

### Operating System

- **Primary:** Ubuntu 22.04 LTS or later
- **Alternative:** Debian 12 or RHEL 9

### Database

- **PostgreSQL:** 14.x or later
- **Extensions:**
  - `pg_stat_statements` (for query monitoring)
  - `pg_buffercache` (for buffer pool monitoring)
  - `auto_explain` (for slow query logging)

### Python

- **Python:** 3.9 or later
- **Package Manager:** pip or poetry
- **Virtual Environment:** venv or conda

### Dependencies

See `requirements.txt` for complete list. Key dependencies:
- `psycopg2-binary`: PostgreSQL adapter
- `pandas`: Data manipulation
- `scikit-learn`: Machine learning
- `sqlalchemy`: Database ORM
- `joblib`: Model serialization

### Optional Software

- **Redis:** 6.x or later (for caching)
- **DuckDB:** 0.9.x or later (for analytics)
- **NVIDIA Drivers:** Latest (for GPU training)
- **CUDA/cuDNN:** Latest (for GPU training)

## Network Requirements

### Ports

- **PostgreSQL:** 5432
- **Redis:** 6379 (if using)
- **API Server:** 8000 (or configured port)
- **Monitoring:** 9090 (Prometheus)
- **Grafana:** 3000 (if using)

### Bandwidth

- **Minimum:** 1 Gbps
- **Recommended:** 10 Gbps
- **For MLB API:** At least 100 Mbps sustained

### DNS

- **Domain:** Configured with A records
- **SSL/TLS:** Valid certificates for HTTPS
- **CDN:** Optional for static assets

## Security Requirements

### Authentication

- **Database:** Strong passwords, SSL connections
- **API:** API keys or OAuth2
- **SSH:** Key-based authentication, disable password auth

### Authorization

- **Role-based access control (RBAC)**
- **Principle of least privilege**
- **Separate dev/staging/production environments

### Encryption

- **Data at rest:** Full disk encryption (LUKS)
- **Data in transit:** TLS 1.3
- **Secrets:** Encrypted storage (HashiCorp Vault or similar)

### Network Security

- **Firewall:** UFW or iptables
- **Ingress:** Only required ports open
- **Egress:** Restricted to necessary endpoints
- **VPN:** Required for admin access

### Compliance

- **Audit logging:** All admin actions logged
- **Change management:** Approval process for changes
- **Backup verification:** Regular restore tests

## Monitoring Requirements

### Metrics Collection

- **System Metrics:** CPU, RAM, disk, network
- **Database Metrics:** Connections, queries, locks, replication lag
- **Application Metrics:** Request latency, error rates, prediction throughput
- **Business Metrics:** Model accuracy, calibration drift, data quality

### Alerting

- **Critical Alerts:** PagerDuty or similar (immediate notification)
- **Warning Alerts:** Email or Slack (within 15 minutes)
- **Info Alerts:** Dashboard only

### Dashboards

- **System Health:** CPU, RAM, disk, network
- **Database Health:** Connections, queries, replication
- **Application Health:** Requests, errors, latency
- **Model Health:** Accuracy, calibration, drift
- **Data Quality:** Null rates, validation results

### Logging

- **Centralized:** ELK stack or similar
- **Retention:** 90 days minimum
- **Searchable:** Full-text search
- **Structured:** JSON format

## Backup Requirements

### Database Backups

- **Frequency:** Daily full backups, hourly WAL archives
- **Retention:** 30 days for daily, 7 days for hourly
- **Storage:** Offsite or separate disk
- **Verification:** Weekly restore tests

### Model Artifacts

- **Storage:** Version-controlled in data/models/
- **Backup:** Git repository or S3
- **Retention:** All registered models
- **Verification:** Model loading tests

### Configuration

- **Storage:** Version-controlled in Git
- **Backup:** Git repository
- **Retention:** All versions
- **Verification:** Configuration validation

### Disaster Recovery

- **RPO:** 1 hour (maximum data loss)
- **RTO:** 4 hours (recovery time objective)
- **Location:** Separate geographic region
- **Documentation:** Runbooks tested quarterly

## Scalability Requirements

### Horizontal Scaling

- **Application Servers:** Stateless design allows horizontal scaling
- **Load Balancer:** Nginx or HAProxy
- **Session Storage:** Redis or database-backed

### Vertical Scaling

- **Database:** Read replicas for query scaling
- **Application:** CPU/RAM can be increased
- **Storage:** Can be expanded online

### Auto-scaling

- **Trigger:** CPU > 70% for 5 minutes
- **Action:** Add application server
- **Cooldown:** 10 minutes
- **Maximum:** 10 application servers

## Performance Requirements

### Latency

- **Prediction Serving:** P95 < 100ms
- **Feature Query:** P95 < 50ms
- **Database Query:** P95 < 100ms
- **API Response:** P95 < 200ms

### Throughput

- **Predictions:** 100 predictions/second per server
- **Data Ingestion:** 1000 records/second
- **Database Queries:** 1000 queries/second

### Availability

- **Uptime:** 99.5% annually
- **Downtime:** < 44 hours/year
- **Planned Maintenance:** < 8 hours/month
- **Unplanned Outages:** < 4 hours/year

## High Availability Requirements

### Application Layer

- **Servers:** 3 minimum
- **Load Balancer:** Active-passive or active-active
- **Health Checks:** Every 10 seconds
- **Failover:** Automatic

### Database Layer

- **Primary:** 1 server
- **Replicas:** 2 minimum
- **Replication:** Streaming, synchronous for critical data
- **Failover:** Automatic or manual within 5 minutes

### Storage

- **RAID:** RAID 10 for database
- **Backups:** Offsite storage
- **Redundancy:** Multiple paths

## Development Environment

### Staging

- **Purpose:** Pre-production testing
- **Configuration:** Mirrors production
- **Data:** Anonymized sample data
- **Access:** Development team only

### Development

- **Purpose:** Local development
- **Configuration:** Docker Compose
- **Data:** Small sample dataset
- **Access:** Individual developers

## Operational Requirements

### Runbooks

- **Deployment:** Step-by-step deployment procedure
- **Rollback:** Rollback procedure for failed deployments
- **Emergency:** Emergency response procedures
- **Maintenance:** Regular maintenance procedures

### Documentation

- **Architecture:** Up-to-date architecture diagrams
- **API:** API documentation (OpenAPI/Swagger)
- **Procedures:** Operational procedures documented
- **Troubleshooting:** Common issues and solutions

### Change Management

- **Process:** Pull request review required
- **Testing:** All tests must pass
- **Approval:** Production changes require approval
- **Rollback:** Rollback plan required for changes

## Cost Considerations

### Cloud Hosting

- **Application Servers:** $200-500/month
- **Database Servers:** $500-1000/month
- **Storage:** $100-200/month
- **Bandwidth:** $50-100/month
- **Monitoring:** $50-100/month
- **Total:** $900-1900/month

### On-Premise

- **Hardware:** $10,000-20,000 initial
- **Maintenance:** $2000-5000/year
- **Power/Cooling:** $1000-2000/year
- **Network:** $1000-2000/year
- **Total:** $14,000-29,000 initial + $4000-9000/year

### Staffing

- **DevOps Engineer:** 0.5 FTE
- **Database Administrator:** 0.25 FTE
- **Monitoring:** 0.25 FTE
- **Total:** 1 FTE

## Compliance

### Data Privacy

- **PII:** No personal data in warehouse
- **Anonymization:** Player IDs only
- **Retention:** Configurable retention periods

### Audit

- **Access Logs:** All access logged
- **Change Logs:** All changes logged
- **Retention:** 1 year minimum
- **Review:** Quarterly

## Next Steps

1. Assess current infrastructure against requirements
2. Plan hardware acquisition or cloud provisioning
3. Set up monitoring and alerting
4. Implement backup procedures
5. Create disaster recovery plan
6. Document operational procedures
7. Train operations team
8. Conduct failover testing
9. Deploy to staging for validation
10. Deploy to production with rollback plan
