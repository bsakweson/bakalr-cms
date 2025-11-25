# Authentication Guide

Bakalr CMS provides multiple authentication methods to secure your API requests.

## Authentication Methods

### 1. JWT Bearer Tokens (Recommended for User Actions)

JWT (JSON Web Token) authentication is the primary method for user-based authentication.

#### Getting Started

1. **Register a new account**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "organization_name": "My Company"
  }'
```

2. **Login to get access token**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

3. **Use the access token in requests**:
```bash
curl -X GET http://localhost:8000/api/v1/content-types \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

#### Token Refresh

Access tokens expire after 30 minutes. Use the refresh token to get a new access token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

#### Token Revocation

Logout and revoke tokens:

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

### 2. API Keys (Recommended for Service-to-Service)

API keys are ideal for server-to-server communication and automation.

#### Creating an API Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "scopes": ["read:content", "write:content"],
    "expires_at": "2026-12-31T23:59:59Z"
  }'
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Production API Key",
  "key": "bak_live_1234567890abcdef1234567890abcdef",
  "scopes": ["read:content", "write:content"],
  "created_at": "2025-11-25T10:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

⚠️ **Important**: Save the `key` value securely. It won't be shown again.

#### Using API Keys

Include the API key in the `X-API-Key` header:

```bash
curl -X GET http://localhost:8000/api/v1/content-types \
  -H "X-API-Key: bak_live_1234567890abcdef1234567890abcdef"
```

#### API Key Scopes

Available scopes:
- `read:content` - Read content entries
- `write:content` - Create/update/delete content
- `read:media` - Access media files
- `write:media` - Upload/delete media
- `admin:users` - Manage users
- `admin:roles` - Manage roles and permissions

### 3. Two-Factor Authentication (2FA)

Enhance security with TOTP-based 2FA.

#### Enabling 2FA

1. **Request 2FA setup**:
```bash
curl -X POST http://localhost:8000/api/v1/two-factor/enable \
  -H "Authorization: Bearer <access_token>"
```

**Response**:
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "otpauth://totp/Bakalr:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Bakalr",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344",
    "44332211",
    "55667788"
  ]
}
```

2. **Scan QR code** with authenticator app (Google Authenticator, Authy, 1Password)

3. **Verify 2FA setup**:
```bash
curl -X POST http://localhost:8000/api/v1/two-factor/verify \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456"
  }'
```

#### Login with 2FA

When 2FA is enabled, login requires an additional step:

1. **Initial login** (returns `requires_2fa: true`):
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "SecurePass123!"
  }'
```

2. **Complete login with 2FA code**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-2fa \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "code": "123456"
  }'
```

#### Using Backup Codes

If you lose access to your authenticator app:

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-2fa \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "backup_code": "12345678"
  }'
```

### 4. Password Reset Flow

#### Request Password Reset

```bash
curl -X POST http://localhost:8000/api/v1/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

User receives an email with a reset link.

#### Reset Password

```bash
curl -X POST http://localhost:8000/api/v1/password-reset/reset \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset_token_from_email",
    "new_password": "NewSecurePass456!"
  }'
```

## Multi-Tenancy & Organization Switching

### Switching Organizations

Users can belong to multiple organizations. Switch context:

```bash
curl -X POST http://localhost:8000/api/v1/tenant/switch \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

Returns new tokens scoped to the selected organization.

### Listing User Organizations

```bash
curl -X GET http://localhost:8000/api/v1/tenant/organizations \
  -H "Authorization: Bearer <access_token>"
```

## Security Best Practices

### Token Storage

- ✅ Store tokens in secure, httpOnly cookies (web apps)
- ✅ Use secure storage (Keychain, Keystore) for mobile apps
- ❌ Never store tokens in localStorage (XSS vulnerable)

### API Key Management

- ✅ Rotate API keys regularly
- ✅ Use environment variables, never hardcode
- ✅ Set expiration dates
- ✅ Use minimal scopes (principle of least privilege)
- ❌ Never commit API keys to version control

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

### Rate Limiting

- Authenticated users: 100 requests/minute
- Unauthenticated: 20 requests/minute
- API keys: 200 requests/minute

Rate limit headers in response:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700000000
```

## Error Responses

### 401 Unauthorized

```json
{
  "type": "https://api.yourdomain.com/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden

```json
{
  "type": "https://api.yourdomain.com/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "You don't have permission to access this resource"
}
```

### 429 Rate Limit Exceeded

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "detail": "Rate limit exceeded for user"
}
```

## Code Examples

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "username": "user@example.com",
        "password": "SecurePass123!"
    }
)
data = response.json()
access_token = data["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "http://localhost:8000/api/v1/content-types",
    headers=headers
)
content_types = response.json()
```

### TypeScript/JavaScript

```typescript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'SecurePass123!'
  })
});
const { access_token } = await loginResponse.json();

// Make authenticated request
const response = await fetch('http://localhost:8000/api/v1/content-types', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const contentTypes = await response.json();
```

### cURL

```bash
# Store token in variable
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"SecurePass123!"}' \
  | jq -r '.access_token')

# Use token
curl -X GET http://localhost:8000/api/v1/content-types \
  -H "Authorization: Bearer $TOKEN"
```

## Support

For issues or questions:
- 📖 [API Documentation](http://localhost:8000/api/scalar)
- 🐛 [Report Issues](https://github.com/yourusername/bakalr-cms/issues)
- 💬 [Discussions](https://github.com/yourusername/bakalr-cms/discussions)
