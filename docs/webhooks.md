# Webhooks Documentation

Webhooks allow you to receive real-time HTTP callbacks when events occur in your Bakalr CMS organization.

## Overview

Webhooks send POST requests to your specified URL when events happen, such as:
- Content created, updated, or deleted
- Media uploaded or deleted
- User actions
- Organization changes

## Creating a Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhooks/bakalr",
    "events": ["content.created", "content.updated", "content.deleted"],
    "secret": "your_webhook_secret_key",
    "active": true,
    "description": "Production webhook for content changes"
  }'
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://your-domain.com/webhooks/bakalr",
  "events": ["content.created", "content.updated", "content.deleted"],
  "secret": "your_webhook_secret_key",
  "active": true,
  "description": "Production webhook for content changes",
  "created_at": "2025-11-25T10:00:00Z"
}
```

## Available Events

| Event | Description |
|-------|-------------|
| `content.created` | New content entry created |
| `content.updated` | Content entry updated |
| `content.deleted` | Content entry deleted |
| `content.published` | Content entry published |
| `media.uploaded` | New media file uploaded |
| `media.deleted` | Media file deleted |

## Webhook Payload Structure

### Common Fields

All webhook payloads include:

```json
{
  "event": "content.created",
  "timestamp": "2025-11-25T10:30:00Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "data": { ... }
}
```

### Content Events

#### content.created

```json
{
  "event": "content.created",
  "timestamp": "2025-11-25T10:30:00Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "content_type": "blog_post",
    "slug": "my-first-post",
    "status": "draft",
    "fields": {
      "title": "My First Post",
      "body": "<p>Hello World!</p>",
      "author": "John Doe"
    },
    "created_by": {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "email": "john@example.com",
      "full_name": "John Doe"
    },
    "created_at": "2025-11-25T10:30:00Z"
  }
}
```

#### content.updated

```json
{
  "event": "content.updated",
  "timestamp": "2025-11-25T11:00:00Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "content_type": "blog_post",
    "slug": "my-first-post-updated",
    "status": "published",
    "fields": {
      "title": "My First Post (Updated)",
      "body": "<p>Hello World! Updated content.</p>",
      "author": "John Doe"
    },
    "updated_by": {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "email": "john@example.com",
      "full_name": "John Doe"
    },
    "updated_at": "2025-11-25T11:00:00Z",
    "changes": {
      "slug": {
        "old": "my-first-post",
        "new": "my-first-post-updated"
      },
      "status": {
        "old": "draft",
        "new": "published"
      }
    }
  }
}
```

#### content.deleted

```json
{
  "event": "content.deleted",
  "timestamp": "2025-11-25T12:00:00Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "content_type": "blog_post",
    "slug": "my-first-post-updated",
    "deleted_by": {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "email": "john@example.com",
      "full_name": "John Doe"
    },
    "deleted_at": "2025-11-25T12:00:00Z"
  }
}
```

### Media Events

#### media.uploaded

```json
{
  "event": "media.uploaded",
  "timestamp": "2025-11-25T10:45:00Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "filename": "hero-image.jpg",
    "file_type": "image/jpeg",
    "file_size": 2048576,
    "url": "https://cdn.yourdomain.com/uploads/images/hero-image.jpg",
    "thumbnail_url": "https://cdn.yourdomain.com/uploads/thumbnails/hero-image.jpg",
    "uploaded_by": {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "email": "john@example.com",
      "full_name": "John Doe"
    },
    "uploaded_at": "2025-11-25T10:45:00Z"
  }
}
```

## Security: HMAC Signature Verification

All webhook requests include an `X-Webhook-Signature` header with an HMAC-SHA256 signature.

### Verifying Signatures

**Python**:
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

# Example usage
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhooks/bakalr', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()
    
    if not verify_webhook_signature(payload, signature, 'your_webhook_secret_key'):
        return {'error': 'Invalid signature'}, 401
    
    data = request.get_json()
    event = data['event']
    
    if event == 'content.created':
        # Handle content creation
        content_id = data['data']['id']
        print(f"New content created: {content_id}")
    
    return {'status': 'success'}, 200
```

**TypeScript/Node.js**:
```typescript
import crypto from 'crypto';
import express from 'express';

function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

const app = express();

app.post('/webhooks/bakalr', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-webhook-signature'] as string;
  const payload = req.body.toString();
  
  if (!verifyWebhookSignature(payload, signature, 'your_webhook_secret_key')) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  const data = JSON.parse(payload);
  const event = data.event;
  
  if (event === 'content.created') {
    const contentId = data.data.id;
    console.log(`New content created: ${contentId}`);
  }
  
  res.json({ status: 'success' });
});
```

## Retry Logic

If your webhook endpoint fails (returns non-2xx status code), Bakalr will retry:

- **Retry Schedule**: Exponential backoff
  - 1st retry: After 1 minute
  - 2nd retry: After 5 minutes
  - 3rd retry: After 15 minutes
  - 4th retry: After 1 hour
  - 5th retry: After 6 hours
- **Max Retries**: 5 attempts
- **Timeout**: 30 seconds per request

After 5 failed attempts, the webhook delivery is marked as failed and you'll receive a notification.

## Webhook Logs

View delivery logs for debugging:

```bash
curl -X GET http://localhost:8000/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000/logs \
  -H "Authorization: Bearer <access_token>"
```

**Response**:
```json
{
  "logs": [
    {
      "id": "110e8400-e29b-41d4-a716-446655440000",
      "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
      "event": "content.created",
      "status_code": 200,
      "response_time_ms": 145,
      "attempt": 1,
      "success": true,
      "created_at": "2025-11-25T10:30:05Z"
    },
    {
      "id": "220e8400-e29b-41d4-a716-446655440000",
      "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
      "event": "content.updated",
      "status_code": 500,
      "response_time_ms": 5000,
      "attempt": 1,
      "success": false,
      "error": "Connection timeout",
      "created_at": "2025-11-25T11:00:10Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50
}
```

## Testing Webhooks

### Using webhook.site

For quick testing, use [webhook.site](https://webhook.site):

1. Go to https://webhook.site
2. Copy your unique URL
3. Create a webhook with that URL
4. Trigger an event (create content, upload media, etc.)
5. View the request details on webhook.site

### Using ngrok for Local Development

```bash
# Install ngrok
brew install ngrok

# Start your local server
python app.py

# Expose it with ngrok
ngrok http 5000

# Use the ngrok URL in your webhook
# e.g., https://abc123.ngrok.io/webhooks/bakalr
```

## Managing Webhooks

### List All Webhooks

```bash
curl -X GET http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer <access_token>"
```

### Update a Webhook

```bash
curl -X PUT http://localhost:8000/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://new-domain.com/webhooks/bakalr",
    "events": ["content.created", "content.updated"],
    "active": true
  }'
```

### Delete a Webhook

```bash
curl -X DELETE http://localhost:8000/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>"
```

### Pause/Resume a Webhook

```bash
# Pause
curl -X PUT http://localhost:8000/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'

# Resume
curl -X PUT http://localhost:8000/api/v1/webhooks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

## Best Practices

### Security
- ✅ Always verify HMAC signatures
- ✅ Use HTTPS endpoints only
- ✅ Rotate webhook secrets regularly
- ✅ Implement rate limiting on your webhook endpoint
- ❌ Never log sensitive data from webhooks

### Reliability
- ✅ Return 2xx status code quickly (< 5 seconds)
- ✅ Process webhooks asynchronously (use queues)
- ✅ Implement idempotency (webhooks may be delivered multiple times)
- ✅ Store webhook IDs to detect duplicates
- ❌ Don't perform heavy processing synchronously

### Monitoring
- ✅ Monitor webhook logs regularly
- ✅ Set up alerts for failed deliveries
- ✅ Track response times
- ✅ Test webhooks in staging before production

### Example: Idempotent Webhook Handler

```python
from flask import Flask, request
import redis

app = Flask(__name__)
redis_client = redis.Redis()

@app.route('/webhooks/bakalr', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    webhook_id = f"{data['webhook_id']}:{data['timestamp']}"
    
    # Check if we've already processed this webhook
    if redis_client.get(webhook_id):
        return {'status': 'already_processed'}, 200
    
    # Mark as processed (expires after 24 hours)
    redis_client.setex(webhook_id, 86400, '1')
    
    # Process the webhook
    process_webhook(data)
    
    return {'status': 'success'}, 200
```

## Troubleshooting

### Webhook Not Firing

1. Check webhook is active: `active: true`
2. Verify event is in subscribed events list
3. Check organization/tenant context
4. Review webhook logs for errors

### Signature Verification Failing

1. Ensure you're using the raw request body (not parsed JSON)
2. Check secret key matches
3. Verify HMAC algorithm is SHA-256
4. Use `hmac.compare_digest()` for comparison (prevents timing attacks)

### High Failure Rate

1. Check your endpoint is accessible (firewall, DNS)
2. Ensure it returns < 5 seconds
3. Verify SSL certificate is valid
4. Check response status codes (must be 2xx)
5. Review your error logs

## Rate Limits

Webhook endpoints are subject to:
- **Max concurrent requests**: 10 per webhook
- **Max deliveries**: 1000 per hour per webhook
- **Burst limit**: 50 requests in 10 seconds

If limits are exceeded, additional events are queued and delivered when capacity is available.

## Support

For webhook issues:
- 📖 [API Documentation](http://localhost:8000/api/scalar)
- 🐛 [Report Issues](https://github.com/yourusername/bakalr-cms/issues)
- 💬 [Discussions](https://github.com/yourusername/bakalr-cms/discussions)
