# Security Guide - Bakalr CMS

This document outlines the security features and best practices for Bakalr CMS.

## Table of Contents

- [Security Features](#security-features)
- [Authentication & Authorization](#authentication--authorization)
- [OWASP Top 10 Protection](#owasp-top-10-protection)
- [Security Headers](#security-headers)
- [Secrets Management](#secrets-management)
- [Audit Logging](#audit-logging)
- [Security Checklist](#security-checklist)
- [Incident Response](#incident-response)

## Security Features

Bakalr CMS implements multiple layers of security:

### Core Security

- ✅ JWT-based authentication with bcrypt password hashing
- ✅ Two-Factor Authentication (2FA) with TOTP
- ✅ API key authentication with scoped permissions
- ✅ Role-Based Access Control (RBAC) with field-level permissions
- ✅ Multi-tenancy isolation
- ✅ Rate limiting per user, tenant, and IP
- ✅ CSRF protection for state-changing operations
- ✅ XSS protection with security headers
- ✅ SQL injection prevention with parameterized queries
- ✅ Request validation and sanitization
- ✅ Secure password reset flow with tokens
- ✅ Comprehensive audit logging

### Infrastructure Security

- ✅ HTTPS enforcement (HSTS)
- ✅ Content Security Policy (CSP)
- ✅ CORS configuration
- ✅ Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- ✅ Secrets management (environment variables, AWS Secrets Manager, Vault)
- ✅ Database connection pooling
- ✅ Input sanitization

## Authentication & Authorization

### JWT Authentication

```python
# Login to get JWT token
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# Use token in subsequent requests
GET /api/v1/content/
Authorization: Bearer <access_token>
```

### API Key Authentication

```python
# Create API key
POST /api/v1/auth/api-keys
Authorization: Bearer <jwt_token>
{
  "name": "Production API",
  "permissions": ["content.read", "media.read"]
}

# Use API key
GET /api/v1/content/
X-API-Key: <api_key>
```

### Two-Factor Authentication

```python
# Enable 2FA
POST /api/v1/auth/2fa/enable
Authorization: Bearer <token>

# Verify with TOTP code
POST /api/v1/auth/2fa/verify
{
  "code": "123456"
}
```

## OWASP Top 10 Protection

### A01:2021 – Broken Access Control

**Protection:**

- RBAC with role hierarchy and permission inheritance
- Field-level permissions
- Organization/tenant isolation
- API endpoints protected with permission decorators
- Audit logging for access attempts

```python
from backend.core.permissions import PermissionChecker

# Protect endpoint with permission
@router.get("/content/")
async def list_content(
    user: User = Depends(get_current_active_user),
    _: None = Depends(PermissionChecker.require_permission("content.read"))
):
    # Only users with content.read permission can access
    pass
```

### A02:2021 – Cryptographic Failures

**Protection:**

- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens signed with HS256
- HTTPS enforcement in production
- Sensitive data encrypted at rest
- Secure random token generation

```python
from backend.core.security import get_password_hash, verify_password

# Password hashing
hashed = get_password_hash("password123")
is_valid = verify_password("password123", hashed)
```

### A03:2021 – Injection

**Protection:**

- SQLAlchemy ORM with parameterized queries
- Input validation with Pydantic models
- Request validation middleware
- XSS protection with output encoding
- SQL injection pattern detection

```python
# Safe query with SQLAlchemy
users = db.query(User).filter(User.email == email).all()

# Input validation with Pydantic
class ContentCreate(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=10000)
```

### A04:2021 – Insecure Design

**Protection:**

- Principle of least privilege
- Defense in depth (multiple security layers)
- Secure defaults
- Rate limiting
- CSRF protection

### A05:2021 – Security Misconfiguration

**Protection:**

- Environment-based configuration
- Secrets validation on startup
- Security headers enforced
- Debug mode disabled in production
- Error messages don't leak sensitive info

```bash
# Validate security configuration
poetry run python scripts/security_check.py
```

### A06:2021 – Vulnerable and Outdated Components

**Protection:**

- Regular dependency updates
- Automated security scanning (bandit, safety)
- Pre-commit hooks
- Dependency pinning

```bash
# Check for vulnerabilities
poetry audit
bandit -r backend/
```

### A07:2021 – Identification and Authentication Failures

**Protection:**

- Strong password requirements
- Account lockout after failed attempts
- 2FA support
- Secure session management
- Token expiration and refresh

### A08:2021 – Software and Data Integrity Failures

**Protection:**

- Webhook HMAC signatures
- Content versioning
- Audit logs for all changes
- Database backups

### A09:2021 – Security Logging and Monitoring Failures

**Protection:**

- Comprehensive audit logging
- Security event tracking
- Failed login attempts logged
- Access denied events tracked
- Structured logging format

```python
from backend.core.security_audit import log_login_failure

# Log security events
log_login_failure(
    username="user@example.com",
    request=request,
    reason="invalid_password"
)
```

### A10:2021 – Server-Side Request Forgery (SSRF)

**Protection:**

- URL validation for webhooks
- Restricted internal network access
- Request size limits
- Timeout configuration

## Security Headers

All responses include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; ...
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Content Security Policy

Configure CSP in `backend/core/csp.py`:

```python
from backend.core.csp import CSPBuilder

# Build custom CSP
csp = CSPBuilder()
csp.add_script_src("https://cdn.example.com")
csp.add_style_src("https://fonts.googleapis.com")
policy = csp.build()
```

## Secrets Management

### Environment Variables

Required secrets:

```bash
# Required
SECRET_KEY=<min-32-chars-random-string>
JWT_SECRET_KEY=<min-32-chars-random-string>
DATABASE_URL=postgresql://user:pass@localhost/db

# Optional
REDIS_URL=redis://localhost:6379/0
SMTP_HOST=smtp.example.com
SMTP_USERNAME=user
SMTP_PASSWORD=pass
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### AWS Secrets Manager

```bash
# Configure AWS Secrets Manager
export SECRETS_BACKEND=aws
export AWS_REGION=us-east-1

# Store secrets in AWS
aws secretsmanager create-secret \
    --name production/SECRET_KEY \
    --secret-string '{"value":"your-secret-key"}'
```

### HashiCorp Vault

```bash
# Configure Vault
export SECRETS_BACKEND=vault
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=<token>

# Store secrets in Vault
vault kv put secret/production/SECRET_KEY value="your-secret-key"
```

## Audit Logging

All security events are logged:

```python
from backend.core.security_audit import (
    log_login_success,
    log_access_denied,
    log_permission_violation
)

# Log successful login
log_login_success(
    user_id=user.id,
    username=user.email,
    organization_id=user.organization_id,
    request=request,
    method="password"
)

# Log access denied
log_access_denied(
    user_id=user.id,
    username=user.email,
    resource="content",
    action="delete",
    request=request
)
```

### Audit Log Storage

Audit logs are stored in the database (`audit_logs` table) with:

- Timestamp
- Event type
- User information
- IP address
- User agent
- Action details
- Success/failure status

## Security Checklist

### Before Deployment

- [ ] Change default admin password
- [ ] Generate strong SECRET_KEY (32+ characters)
- [ ] Generate strong JWT_SECRET_KEY (32+ characters)
- [ ] Configure HTTPS with valid SSL certificate
- [ ] Set up database backups
- [ ] Configure SMTP for email notifications
- [ ] Review CORS settings for production domains
- [ ] Disable debug mode (`DEBUG=false`)
- [ ] Run security scanner: `poetry run python scripts/security_check.py`
- [ ] Check for dependency vulnerabilities: `poetry audit`
- [ ] Review and restrict file permissions
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting thresholds
- [ ] Test 2FA functionality
- [ ] Review audit log configuration
- [ ] Set up log aggregation
- [ ] Configure secrets management (AWS/Vault)
- [ ] Test backup and restore procedures

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Update dependencies monthly
- [ ] Rotate API keys quarterly
- [ ] Review user permissions quarterly
- [ ] Test backup restores monthly
- [ ] Review security headers configuration
- [ ] Check for failed login attempts
- [ ] Monitor rate limit violations
- [ ] Review CORS configuration
- [ ] Update SSL certificates before expiration

### Security Monitoring

Monitor these metrics:

- Failed login attempts
- Rate limit violations
- Permission violations
- CSRF token failures
- SQL injection attempts
- Unusual API usage patterns
- Large data exports
- Bulk operations
- Admin actions

## Incident Response

### Security Incident Procedure

1. **Identify**: Detect and confirm the security incident
2. **Contain**: Isolate affected systems
3. **Eradicate**: Remove the threat
4. **Recover**: Restore normal operations
5. **Learn**: Document lessons learned

### Emergency Actions

```bash
# Disable user account
poetry run python scripts/bulk_operations.py \
    --operation disable-user \
    --username suspicious@user.com

# Revoke all API keys for user
poetry run python scripts/bulk_operations.py \
    --operation revoke-api-keys \
    --user-id 123

# Force password reset for all users
poetry run python scripts/bulk_operations.py \
    --operation force-password-reset \
    --organization bakalr-cms
```

### Contact

For security vulnerabilities, contact: `security@yourdomain.com`

**Do not** disclose security vulnerabilities publicly until they are patched.

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
