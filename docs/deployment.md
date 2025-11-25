# Bakalr CMS - Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Health Checks](#health-checks)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)
- [Backup and Restore](#backup-and-restore)

## Prerequisites

### Required Software

- Docker 24.0+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.20+ (included with Docker Desktop)
- Git

### System Requirements

**Minimum (Development)**:

- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB

**Recommended (Production)**:

- CPU: 4+ cores
- RAM: 8GB+
- Disk: 50GB+ (SSD recommended)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/bakalr-cms.git
cd bakalr-cms
```

### 2. Start Development Environment

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop all services
docker-compose -f docker-compose.dev.yml down
```

### 3. Access Application

- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **GraphQL**: `http://localhost:8000/api/v1/graphql`
- **Meilisearch**: `http://localhost:7700`

### 4. Default Credentials

```text
Email: admin@bakalr.cms
Password: admin123
```

**⚠️ Change these immediately in production!**

## Development Deployment

### Full Stack with Hot-Reload

```bash
# Start all services with hot-reload
docker-compose -f docker-compose.dev.yml up -d

# View backend logs
docker-compose -f docker-compose.dev.yml logs -f backend

# View frontend logs
docker-compose -f docker-compose.dev.yml logs -f frontend

# Restart a service
docker-compose -f docker-compose.dev.yml restart backend

# Stop and remove all containers
docker-compose -f docker-compose.dev.yml down -v
```

### Run Database Migrations

```bash
# Run migrations
docker-compose -f docker-compose.dev.yml exec backend poetry run alembic upgrade head

# Create new migration
docker-compose -f docker-compose.dev.yml exec backend poetry run alembic revision --autogenerate -m "description"

# Rollback migration
docker-compose -f docker-compose.dev.yml exec backend poetry run alembic downgrade -1
```

### Seed Database

```bash
# Seed with default data
docker-compose -f docker-compose.dev.yml exec backend poetry run python scripts/seed_database.py
```

### Run Tests

```bash
# Run all tests
docker-compose -f docker-compose.dev.yml exec backend poetry run pytest

# Run with coverage
docker-compose -f docker-compose.dev.yml exec backend poetry run pytest --cov=backend --cov-report=html
```

## Production Deployment

### 1. Prepare Environment

```bash
# Copy production environment template
cp .env.production.example .env.production

# Generate secrets
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('MEILI_MASTER_KEY=' + secrets.token_urlsafe(16))"

# Edit .env.production with your values
nano .env.production
```

### 2. Build Images

```bash
# Build all images
docker-compose build --no-cache

# Build specific service
docker-compose build backend
docker-compose build frontend
```

### 3. Start Production Stack

```bash
# Start all services
docker-compose --env-file .env.production up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed initial data
docker-compose exec backend python scripts/seed_database.py
```

### 5. Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Check all services
docker-compose ps
```

## Environment Configuration

### Required Variables

```bash
# Application
SECRET_KEY=<min-32-chars>
JWT_SECRET_KEY=<min-32-chars>

# Database
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_PASSWORD=<strong-password>

# Meilisearch
MEILI_MASTER_KEY=<min-16-chars>

# CORS
CORS_ORIGINS=https://yourdomain.com
```

### Optional Variables

```bash
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=<app-password>

# AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=bakalr-cms-media
STORAGE_BACKEND=s3

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=INFO
```

## Health Checks

### Backend Health

```bash
# Health endpoint
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-25T10:30:00Z"
}
```

### Database Health

```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U bakalr

# Check Redis
docker-compose exec redis redis-cli ping
```

### Container Health

```bash
# View health status of all containers
docker-compose ps

# View detailed health
docker inspect --format='{{json .State.Health}}' bakalr-backend | jq
```

## Scaling

### Horizontal Scaling

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Scale frontend to 2 instances
docker-compose up -d --scale frontend=2
```

### Resource Limits

Edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Load Balancing

Use Nginx or Traefik for load balancing multiple instances.

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port
lsof -ti:8000

# Kill process
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

#### 2. Database Connection Failed

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify credentials
docker-compose exec backend env | grep DATABASE_URL

# Test connection
docker-compose exec backend python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://bakalr:password@postgres:5432/bakalr_cms'); print(engine.connect())"
```

#### 3. Frontend Build Failed

```bash
# Clear Next.js cache
docker-compose exec frontend rm -rf .next

# Rebuild
docker-compose build frontend --no-cache

# Check logs
docker-compose logs frontend
```

#### 4. Out of Memory

```bash
# Check resource usage
docker stats

# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

### Debug Commands

```bash
# Enter container shell
docker-compose exec backend sh
docker-compose exec frontend sh

# View environment variables
docker-compose exec backend env

# Check file permissions
docker-compose exec backend ls -la /app

# View process list
docker-compose exec backend ps aux
```

## Backup and Restore

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U bakalr bakalr_cms | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore backup
gunzip < backup_20251125_103000.sql.gz | docker-compose exec -T postgres psql -U bakalr bakalr_cms
```

### Volume Backup

```bash
# Backup volumes
docker run --rm \
  -v bakalr-cms_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .

# Restore volumes
docker run --rm \
  -v bakalr-cms_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_data_backup.tar.gz -C /data
```

### Full System Backup

```bash
# Backup script
./scripts/backup_system.sh

# Includes:
# - Database dump
# - Redis data
# - Uploaded files
# - Configuration files
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since timestamp
docker-compose logs --since 2025-11-25T10:00:00 backend
```

### Resource Monitoring

```bash
# Real-time stats
docker stats

# Export metrics (Prometheus format)
curl http://localhost:8000/metrics
```

## Security Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Generate strong secrets (32+ characters)
- [ ] Configure HTTPS with valid SSL certificate
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure CORS for production domains
- [ ] Set `DEBUG=False`
- [ ] Run security scanner: `docker-compose exec backend python scripts/security_check.py`
- [ ] Review file permissions
- [ ] Set up monitoring and alerting
- [ ] Configure automatic backups
- [ ] Test disaster recovery

## Next Steps

1. **Set up SSL/TLS**: Configure Nginx with Let's Encrypt
2. **CDN**: Add CloudFlare or AWS CloudFront
3. **Monitoring**: Integrate Prometheus + Grafana
4. **CI/CD**: Set up GitHub Actions for automated deployment
5. **Backups**: Configure automated daily backups

---

For more information, see:

- [Security Guide](./security.md)
- [API Documentation](http://localhost:8000/docs)
- [Quick Start Guide](./quickstart.md)
