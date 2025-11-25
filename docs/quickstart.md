# Bakalr CMS - Quick Start Guide

Get started with Bakalr CMS in minutes using this step-by-step guide.

## Prerequisites

- Python 3.11+ (backend) or Node.js 18+ (SDK)
- Redis server (for caching)
- PostgreSQL or SQLite (database)

## Installation

### Using Python SDK

```bash
pip install bakalr-cms-sdk
```

### Using TypeScript/JavaScript SDK

```bash
npm install @bakalr/cms-sdk
# or
yarn add @bakalr/cms-sdk
```

## Quick Start

### Step 1: Register and Authenticate

**Python**:
```python
from bakalr_cms import BakalrClient

# Initialize client
client = BakalrClient(base_url="http://localhost:8000")

# Register new account
user = client.auth.register(
    email="user@example.com",
    password="SecurePass123!",
    full_name="John Doe",
    organization_name="My Company"
)

# Login
tokens = client.auth.login(
    username="user@example.com",
    password="SecurePass123!"
)

print(f"Access Token: {tokens['access_token']}")
```

**TypeScript**:
```typescript
import { BakalrClient } from '@bakalr/cms-sdk';

// Initialize client
const client = new BakalrClient({
  baseUrl: 'http://localhost:8000'
});

// Register new account
const user = await client.auth.register({
  email: 'user@example.com',
  password: 'SecurePass123!',
  fullName: 'John Doe',
  organizationName: 'My Company'
});

// Login
const tokens = await client.auth.login({
  username: 'user@example.com',
  password: 'SecurePass123!'
});

console.log(`Access Token: ${tokens.accessToken}`);
```

**cURL**:
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "organization_name": "My Company"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Step 2: Create a Content Type

**Python**:
```python
# Create a blog post content type
content_type = client.content_types.create(
    name="Blog Post",
    slug="blog_post",
    description="Blog articles",
    schema={
        "title": {
            "type": "text",
            "label": "Title",
            "required": True
        },
        "excerpt": {
            "type": "textarea",
            "label": "Excerpt",
            "description": "Short summary"
        },
        "body": {
            "type": "richtext",
            "label": "Body",
            "required": True
        },
        "author": {
            "type": "text",
            "label": "Author"
        },
        "published_at": {
            "type": "datetime",
            "label": "Published At"
        },
        "featured_image": {
            "type": "image",
            "label": "Featured Image"
        },
        "tags": {
            "type": "text",
            "label": "Tags",
            "description": "Comma-separated tags"
        }
    }
)

print(f"Created content type: {content_type['name']}")
```

**TypeScript**:
```typescript
// Create a blog post content type
const contentType = await client.contentTypes.create({
  name: 'Blog Post',
  slug: 'blog_post',
  description: 'Blog articles',
  schema: {
    title: {
      type: 'text',
      label: 'Title',
      required: true
    },
    excerpt: {
      type: 'textarea',
      label: 'Excerpt',
      description: 'Short summary'
    },
    body: {
      type: 'richtext',
      label: 'Body',
      required: true
    },
    author: {
      type: 'text',
      label: 'Author'
    },
    published_at: {
      type: 'datetime',
      label: 'Published At'
    },
    featured_image: {
      type: 'image',
      label: 'Featured Image'
    },
    tags: {
      type: 'text',
      label: 'Tags',
      description: 'Comma-separated tags'
    }
  }
});

console.log(`Created content type: ${contentType.name}`);
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/content-types \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Blog Post",
    "slug": "blog_post",
    "description": "Blog articles",
    "schema": {
      "title": {
        "type": "text",
        "label": "Title",
        "required": true
      },
      "body": {
        "type": "richtext",
        "label": "Body",
        "required": true
      }
    }
  }'
```

### Step 3: Create Content

**Python**:
```python
# Create a blog post
post = client.content.create(
    content_type="blog_post",
    slug="my-first-post",
    status="published",
    fields={
        "title": "My First Blog Post",
        "excerpt": "This is my first post using Bakalr CMS!",
        "body": "<p>Welcome to my blog. This is the content...</p>",
        "author": "John Doe",
        "published_at": "2025-11-25T10:00:00Z",
        "tags": "tutorial, getting-started, cms"
    }
)

print(f"Created post: {post['fields']['title']}")
print(f"Post ID: {post['id']}")
print(f"URL: /blog/{post['slug']}")
```

**TypeScript**:
```typescript
// Create a blog post
const post = await client.content.create({
  contentType: 'blog_post',
  slug: 'my-first-post',
  status: 'published',
  fields: {
    title: 'My First Blog Post',
    excerpt: 'This is my first post using Bakalr CMS!',
    body: '<p>Welcome to my blog. This is the content...</p>',
    author: 'John Doe',
    published_at: '2025-11-25T10:00:00Z',
    tags: 'tutorial, getting-started, cms'
  }
});

console.log(`Created post: ${post.fields.title}`);
console.log(`Post ID: ${post.id}`);
console.log(`URL: /blog/${post.slug}`);
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/content \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "blog_post",
    "slug": "my-first-post",
    "status": "published",
    "fields": {
      "title": "My First Blog Post",
      "body": "<p>Welcome to my blog...</p>",
      "author": "John Doe"
    }
  }'
```

### Step 4: Query Content

**Python**:
```python
# Get all blog posts
posts = client.content.list(
    content_type="blog_post",
    status="published",
    limit=10
)

for post in posts['items']:
    print(f"- {post['fields']['title']} ({post['slug']})")

# Get single post by slug
post = client.content.get_by_slug("blog_post", "my-first-post")
print(f"Post: {post['fields']['title']}")
```

**TypeScript**:
```typescript
// Get all blog posts
const posts = await client.content.list({
  contentType: 'blog_post',
  status: 'published',
  limit: 10
});

posts.items.forEach(post => {
  console.log(`- ${post.fields.title} (${post.slug})`);
});

// Get single post by slug
const post = await client.content.getBySlug('blog_post', 'my-first-post');
console.log(`Post: ${post.fields.title}`);
```

**cURL**:
```bash
# List all posts
curl -X GET "http://localhost:8000/api/v1/content?content_type=blog_post&status=published&limit=10" \
  -H "Authorization: Bearer <access_token>"

# Get single post
curl -X GET "http://localhost:8000/api/v1/content/blog_post/slug/my-first-post" \
  -H "Authorization: Bearer <access_token>"
```

### Step 5: Upload Media

**Python**:
```python
# Upload an image
with open("hero-image.jpg", "rb") as f:
    media = client.media.upload(
        file=f,
        filename="hero-image.jpg",
        alt_text="Hero image for blog post"
    )

print(f"Uploaded: {media['filename']}")
print(f"URL: {media['url']}")
print(f"Thumbnail: {media['thumbnail_url']}")

# Update post with featured image
client.content.update(
    post['id'],
    fields={
        **post['fields'],
        "featured_image": media['url']
    }
)
```

**TypeScript**:
```typescript
// Upload an image
const file = fs.readFileSync('hero-image.jpg');
const media = await client.media.upload({
  file: file,
  filename: 'hero-image.jpg',
  altText: 'Hero image for blog post'
});

console.log(`Uploaded: ${media.filename}`);
console.log(`URL: ${media.url}`);
console.log(`Thumbnail: ${media.thumbnailUrl}`);

// Update post with featured image
await client.content.update(post.id, {
  fields: {
    ...post.fields,
    featured_image: media.url
  }
});
```

**cURL**:
```bash
# Upload image
curl -X POST http://localhost:8000/api/v1/media/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@hero-image.jpg" \
  -F "alt_text=Hero image for blog post"
```

### Step 6: Add Translations

**Python**:
```python
# Add Spanish translation
client.translations.create(
    content_id=post['id'],
    locale="es",
    fields={
        "title": "Mi Primera Publicación de Blog",
        "excerpt": "¡Esta es mi primera publicación usando Bakalr CMS!",
        "body": "<p>Bienvenido a mi blog. Este es el contenido...</p>"
    }
)

# Get content with translations
post_with_translations = client.content.get(post['id'], include_translations=True)
print(f"Available locales: {list(post_with_translations['translations'].keys())}")
```

**TypeScript**:
```typescript
// Add Spanish translation
await client.translations.create({
  contentId: post.id,
  locale: 'es',
  fields: {
    title: 'Mi Primera Publicación de Blog',
    excerpt: '¡Esta es mi primera publicación usando Bakalr CMS!',
    body: '<p>Bienvenido a mi blog. Este es el contenido...</p>'
  }
});

// Get content with translations
const postWithTranslations = await client.content.get(post.id, { includeTranslations: true });
console.log(`Available locales: ${Object.keys(postWithTranslations.translations)}`);
```

**cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/translations \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "<post_id>",
    "locale": "es",
    "fields": {
      "title": "Mi Primera Publicación de Blog",
      "body": "<p>Bienvenido...</p>"
    }
  }'
```

### Step 7: Search Content

**Python**:
```python
# Search across all content
results = client.search.query(
    q="blog tutorial",
    content_types=["blog_post"],
    limit=10
)

print(f"Found {results['total']} results")
for result in results['hits']:
    print(f"- {result['title']} (score: {result['_score']})")
```

**TypeScript**:
```typescript
// Search across all content
const results = await client.search.query({
  q: 'blog tutorial',
  contentTypes: ['blog_post'],
  limit: 10
});

console.log(`Found ${results.total} results`);
results.hits.forEach(result => {
  console.log(`- ${result.title} (score: ${result._score})`);
});
```

**cURL**:
```bash
curl -X GET "http://localhost:8000/api/v1/search?q=blog%20tutorial&content_type=blog_post&limit=10" \
  -H "Authorization: Bearer <access_token>"
```

## Common Use Cases

### Blog Platform

```python
# Create blog content type
client.content_types.create(name="Blog Post", slug="blog_post", schema={...})

# Create posts
client.content.create(content_type="blog_post", ...)

# Query published posts
posts = client.content.list(content_type="blog_post", status="published", sort="-published_at")

# Implement pagination
page1 = client.content.list(content_type="blog_post", skip=0, limit=10)
page2 = client.content.list(content_type="blog_post", skip=10, limit=10)
```

### E-commerce Product Catalog

```python
# Create product content type
client.content_types.create(
    name="Product",
    slug="product",
    schema={
        "name": {"type": "text", "required": True},
        "description": {"type": "richtext"},
        "price": {"type": "number", "required": True},
        "sku": {"type": "text", "required": True},
        "images": {"type": "text"},  # JSON array of image URLs
        "stock": {"type": "number"},
        "category": {"type": "text"}
    }
)

# Add products
client.content.create(
    content_type="product",
    fields={
        "name": "Wireless Headphones",
        "price": 99.99,
        "sku": "WH-001",
        "stock": 50
    }
)

# Search products
products = client.search.query(q="wireless", content_types=["product"])
```

### Documentation Site

```python
# Create doc page content type
client.content_types.create(
    name="Doc Page",
    slug="doc_page",
    schema={
        "title": {"type": "text", "required": True},
        "content": {"type": "richtext", "required": True},
        "category": {"type": "select", "options": ["Guide", "API", "Tutorial"]},
        "order": {"type": "number"}
    }
)

# Create docs with relationships
getting_started = client.content.create(content_type="doc_page", fields={...})
advanced = client.content.create(content_type="doc_page", fields={...})

# Link related docs
client.relationships.create(
    source_id=getting_started['id'],
    target_id=advanced['id'],
    relationship_type="next_page"
)
```

## Next Steps

- 📖 [Authentication Guide](./authentication.md) - Learn about JWT, API keys, and 2FA
- 🪝 [Webhooks Documentation](./webhooks.md) - Set up real-time event notifications
- 🔍 [Search Guide](./search.md) - Advanced search with Meilisearch
- 🎨 [Theming Guide](./theming.md) - Customize the admin UI
- 🌍 [Translation Guide](./translation.md) - Multi-language content management
- 📊 [GraphQL Guide](./graphql.md) - Query content with GraphQL

## Support

- 📖 [Full API Documentation](http://localhost:8000/api/scalar)
- 🐛 [Report Issues](https://github.com/yourusername/bakalr-cms/issues)
- 💬 [Community Discussions](https://github.com/yourusername/bakalr-cms/discussions)
- 📧 [Email Support](mailto:support@yourdomain.com)
