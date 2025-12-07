# Bakalr CMS API Reference

Quick reference for API endpoints used by the seed runner and integrations.

**Base URL**: `http://localhost:8000/api/v1`

---

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login with email/password |
| POST | `/auth/register` | Register new user |
| POST | `/auth/logout` | Logout (invalidate token) |
| POST | `/auth/refresh` | Refresh access token |

**Login Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Login Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Themes

**Prefix**: `/themes`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/themes` | Create theme |
| GET | `/themes` | List themes |
| GET | `/themes/{id}` | Get theme by ID |
| PATCH | `/themes/{id}` | Update theme |
| DELETE | `/themes/{id}` | Delete theme |
| POST | `/themes/{id}/activate` | Activate theme |
| GET | `/themes/active/current` | Get active theme |

**Create Theme Request:**
```json
{
  "name": "my-theme",
  "display_name": "My Theme",
  "description": "Optional description",
  "colors": {
    "primary": "#3D2817",
    "secondary": "#D4AF37",
    "accent": "#B76E79",
    "background": "#FDF5E6",
    "surface": "#FFFFFF",
    "text": "#2C1810",
    "textSecondary": "#5C4033",
    "border": "#D4C4B0",
    "error": "#F44336",
    "warning": "#FF9800",
    "success": "#4CAF50",
    "info": "#2196F3"
  },
  "typography": {
    "fontFamily": "'Inter', sans-serif",
    "headingFontFamily": "'Playfair Display', serif"
  },
  "spacing": {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "1rem",
    "lg": "1.5rem",
    "xl": "2rem"
  },
  "borderRadius": {
    "sm": "0.25rem",
    "md": "0.5rem",
    "lg": "1rem",
    "full": "9999px"
  },
  "shadows": {
    "sm": "0 1px 2px rgba(0,0,0,0.05)",
    "md": "0 4px 6px rgba(0,0,0,0.1)",
    "lg": "0 10px 15px rgba(0,0,0,0.1)"
  }
}
```

**Required `colors` fields**: `primary`, `secondary`, `accent`, `background`, `surface`, `text`, `textSecondary`, `border`, `error`, `warning`, `success`, `info`

---

## Content Types

**Prefix**: `/content/types`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/content/types` | Create content type |
| GET | `/content/types` | List content types |
| GET | `/content/types/{id}` | Get content type |
| PUT | `/content/types/{id}` | Update content type |
| DELETE | `/content/types/{id}` | Delete content type |

**Create Content Type Request:**
```json
{
  "name": "Product",
  "slug": "product",
  "description": "Products for the store",
  "schema": {
    "name": {
      "type": "string",
      "label": "Product Name",
      "required": true
    },
    "price": {
      "type": "number",
      "label": "Price",
      "required": true
    }
  }
}
```

---

## Content Entries

**Prefix**: `/content/entries`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/content/entries` | Create entry |
| GET | `/content/entries` | List entries |
| GET | `/content/entries/{id}` | Get entry |
| PUT | `/content/entries/{id}` | Full update |
| PATCH | `/content/entries/{id}` | Partial update |
| DELETE | `/content/entries/{id}` | Delete entry |
| POST | `/content/entries/{id}/publish` | Publish entry |
| POST | `/content/entries/{id}/duplicate` | Duplicate entry |

**Create Entry Request:**
```json
{
  "content_type_id": "uuid-here",
  "title": "My Product",
  "slug": "my-product",
  "status": "draft",
  "fields": {
    "name": "My Product",
    "price": 29.99
  }
}
```

**Status values**: `draft`, `published`, `archived`

---

## Translations / Locales

**Prefix**: `/translation`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/translation/locales` | Enable locale |
| GET | `/translation/locales` | List locales |
| GET | `/translation/locales/{id}` | Get locale |
| PUT | `/translation/locales/{id}` | Update locale |
| DELETE | `/translation/locales/{id}` | Disable locale |
| POST | `/translation/translate` | Translate text |

**Enable Locale Request:**
```json
{
  "code": "es",
  "name": "Spanish",
  "native_name": "Español",
  "is_enabled": true
}
```

---

## Media

**Prefix**: `/media`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/media/upload` | Upload file (multipart) |
| GET | `/media` | List media |
| GET | `/media/{id}` | Get media |
| DELETE | `/media/{id}` | Delete media |

**Upload**: Use `multipart/form-data` with `file` field.

---

## Search

**Prefix**: `/search`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | Search content |
| POST | `/search/reindex` | Reindex all content |

**Search Query Params**: `?q=keyword&content_type=product&limit=20`

---

## Users

**Prefix**: `/users`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Current user profile |
| PATCH | `/users/me` | Update profile |
| GET | `/users` | List users (admin) |
| POST | `/users` | Create user (admin) |

---

## Organizations

**Prefix**: `/organization`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/organization` | Get current org |
| PATCH | `/organization` | Update org settings |

---

## Tenant Switching

**Prefix**: `/tenant`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenant/organizations` | List user's orgs |
| POST | `/tenant/switch` | Switch organization |
| POST | `/tenant/set-default` | Set default org |

---

## Webhooks

**Prefix**: `/webhooks`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks` | Create webhook |
| GET | `/webhooks` | List webhooks |
| GET | `/webhooks/{id}` | Get webhook |
| PATCH | `/webhooks/{id}` | Update webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/{id}/test` | Test webhook |

---

## Common Response Formats

**Success (single item):**
```json
{
  "id": "uuid",
  "name": "...",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Success (list):**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

**Error (RFC 7807):**
```json
{
  "type": "https://bakalr.cms/errors/400",
  "title": "Bad Request",
  "status": 400,
  "detail": "Validation error message",
  "instance": "/api/v1/themes"
}
```

---

## Authentication Header

All endpoints (except `/auth/login`, `/auth/register`) require:

```text
Authorization: Bearer <access_token>
```
