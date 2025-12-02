# Bakalr Boutique - E-commerce Setup Guide

This guide walks you through setting up **Bakalr Boutique**, a modern e-commerce store powered by Bakalr CMS.

## Overview

Bakalr Boutique will be a full-featured online boutique with:
- Product catalog with categories, brands, and collections
- Product reviews and ratings
- Multi-currency support
- Inventory management
- SEO optimization
- Multi-language support (auto-translation)
- Search functionality with Meilisearch
- Media management for product images
- Admin dashboard for content management

## Prerequisites

1. **Bakalr CMS Running**
   ```bash
   cd /Users/bsakweson/dev/bakalr-cms
   docker-compose up -d
   ```

2. **Admin Account**
   - Email: `bsakweson@gmail.com`
   - Password: Your secure password

3. **Services Running**
   - Backend: `http://localhost:8000`
   - Frontend: `http://localhost:3000`
   - Meilisearch: `http://localhost:7700`
   - MinIO (S3): `http://localhost:9000`

## Step 1: Run the E-commerce Setup Script

The setup script will create all necessary content types and sample data:

```bash
cd /Users/bsakweson/dev/bakalr-cms
python3 scripts/setup_ecommerce.py
```

### What Gets Created

#### Content Types

1. **Category** (`category`)
   - Name, description, slug
   - Image
   - Parent category (for nested categories)
   - Display order
   - Featured flag

2. **Brand** (`brand`)
   - Name, description (rich text)
   - Logo
   - Website URL
   - Country of origin
   - Featured flag

3. **Product** (`product`)
   - Basic info: name, SKU, description
   - Pricing: price, sale_price, cost, currency
   - Inventory: stock_quantity, stock_status
   - Relations: category, brand
   - Media: images, featured_image
   - Attributes: weight, dimensions, tags
   - Flags: is_featured, is_new, is_on_sale
   - Reviews: rating, review_count
   - Specifications (JSON)

4. **Collection** (`collection`)
   - Name, description, slug
   - Banner image
   - Product IDs
   - Featured flag
   - Display order

5. **Review** (`review`)
   - Product ID
   - Customer name and email
   - Rating (1-5 stars)
   - Title and comment
   - Verified purchase flag
   - Helpful count

#### Sample Data

- **5 Categories**: Electronics, Clothing, Home & Garden, Sports, Books
- **5 Brands**: Apple, Nike, IKEA, Sony, Adidas
- **15 Products**: iPhones, running shoes, furniture, cameras, sportswear, etc.
- Product images and specifications
- Product relationships to categories and brands

## Step 2: Access the Admin Dashboard

1. Open `http://localhost:3000`
2. Login with your credentials
3. Navigate to **Content** section

You should see:
- Content Types (5 created)
- Content Entries (25+ items)

## Step 3: Configure Search

Enable full-text search for products:

```bash
# Reindex content for search
curl -X POST http://localhost:8000/api/v1/search/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Step 4: Set Up Translations

Enable multiple languages for international customers:

### Enable Locales

```bash
# Enable Spanish
curl -X POST http://localhost:8000/api/v1/translation/locales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "es",
    "name": "Spanish",
    "is_enabled": true,
    "auto_translate": true
  }'

# Enable French
curl -X POST http://localhost:8000/api/v1/translation/locales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "fr",
    "name": "French",
    "is_enabled": true,
    "auto_translate": true
  }'
```

Products will be automatically translated when accessed with `?locale=es` or `?locale=fr`.

## Step 5: Configure SEO

Products automatically get SEO metadata, but you can customize:

```bash
# Update product SEO
curl -X POST http://localhost:8000/api/v1/seo/content/{product_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meta_title": "Premium Running Shoes | Bakalr Boutique",
    "meta_description": "High-performance running shoes with advanced cushioning",
    "keywords": "running shoes, athletic footwear, sports shoes",
    "og_image": "https://example.com/product-image.jpg"
  }'
```

## Step 6: Set Up Media Storage

### Option A: Local Storage (Development)

Already configured by default. Files stored in `uploads/` directory.

### Option B: S3 Storage (Production)

Update `.env`:

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=bakalr-boutique-media
S3_PUBLIC_URL=https://cdn.bakalr-boutique.com
```

Or use MinIO (S3-compatible, already running):

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET_NAME=bakalr-boutique
S3_USE_SSL=false
```

## Step 7: Create Webhooks

Set up webhooks to integrate with external services:

```bash
# Webhook for order notifications (integrate with your order system)
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order Notification",
    "url": "https://your-order-system.com/webhook",
    "events": ["content.created", "content.updated"],
    "secret": "your-webhook-secret"
  }'
```

## Step 8: Customize the Theme

Update the boutique theme:

```bash
curl -X POST http://localhost:8000/api/v1/themes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bakalr Boutique Theme",
    "colors": {
      "primary": "#2C1810",
      "secondary": "#8B4513",
      "accent": "#D2691E",
      "background": "#FFF8F0",
      "text": "#2C1810"
    },
    "typography": {
      "font_family": "Inter, system-ui, sans-serif",
      "heading_font": "Playfair Display, serif"
    }
  }'
```

## Step 9: Front-end Integration

### REST API

```javascript
// Fetch products
const response = await fetch('http://localhost:8000/api/v1/content/entries?content_type=product&status=published');
const { items } = await response.json();

// Get single product
const product = await fetch('http://localhost:8000/api/v1/content/entries/1');

// Search products
const results = await fetch('http://localhost:8000/api/v1/search?q=running+shoes');
```

### GraphQL API

```graphql
query GetProducts {
  contentEntries(
    content_type_slug: "product"
    status: "published"
    per_page: 12
  ) {
    items {
      id
      slug
      content_data
      seo_metadata
    }
    pagination {
      total
      has_next
    }
  }
}
```

## Step 10: Content Management Workflow

### Adding New Products

1. **Via Admin Dashboard** (Recommended)
   - Go to Content → Create Entry
   - Select "Product" content type
   - Fill in all fields
   - Upload images
   - Set SEO metadata
   - Publish

2. **Via API**
   ```bash
   curl -X POST http://localhost:8000/api/v1/content/entries \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "content_type_id": 3,
       "title": "New Product",
       "slug": "new-product",
       "status": "published",
       "fields": {
         "name": "New Product",
         "sku": "NP001",
         "price": 99.99,
         "description": "<p>Product description</p>",
         "stock_quantity": 50,
         "stock_status": "in_stock",
         "category": "Electronics",
         "brand": "Apple",
         "is_featured": true
       }
     }'
   ```

### Managing Categories

Categories support nesting for better organization:

```json
{
  "name": "Running Shoes",
  "slug": "running-shoes",
  "parent_category": "Sports",
  "display_order": 1,
  "is_featured": true
}
```

### Creating Collections

Curate product collections for promotions:

```json
{
  "name": "Summer Sale 2025",
  "slug": "summer-sale-2025",
  "description": "<p>Hot deals for summer!</p>",
  "products": "1,5,8,12,15",
  "is_featured": true,
  "display_order": 1
}
```

## Advanced Features

### Analytics

Track product views and performance:

```bash
# Get product analytics
curl http://localhost:8000/api/v1/analytics/content \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Content Relationships

Link related products:

```bash
# Create relationship
curl -X POST http://localhost:8000/api/v1/content/relationships \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entry_id": 1,
    "target_entry_id": 5,
    "relationship_type": "related_products",
    "metadata": {"relation": "accessories"}
  }'
```

### Scheduled Publishing

Schedule product launches:

```bash
curl -X POST http://localhost:8000/api/v1/content/schedule \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_entry_id": 10,
    "action": "publish",
    "scheduled_at": "2025-12-01T00:00:00Z"
  }'
```

### Content Templates

Create templates for consistent product entries:

```bash
curl -X POST http://localhost:8000/api/v1/content/templates \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Standard Product Template",
    "content_type_id": 3,
    "field_defaults": {
      "currency": "USD",
      "stock_status": "in_stock",
      "is_featured": false
    }
  }'
```

## Next Steps

1. **Build the Storefront**: Create a Next.js/React storefront using the CMS API
2. **Integrate Payment**: Add Stripe/PayPal checkout (outside CMS scope)
3. **Set Up Analytics**: Integrate Google Analytics via webhooks
4. **Configure Email**: Set up transactional emails for orders
5. **Go Live**: Deploy to production with proper SSL and CDN

## Troubleshooting

### Issue: Products Not Appearing

**Check content status:**
```bash
curl http://localhost:8000/api/v1/content/entries?status=published \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Only published content appears in delivery endpoints.

### Issue: Search Not Working

**Reindex content:**
```bash
curl -X POST http://localhost:8000/api/v1/search/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue: Images Not Loading

**Check storage configuration** in `.env`:
- Verify `STORAGE_BACKEND` is set correctly
- For S3: Check AWS credentials and bucket permissions
- For local: Verify `UPLOAD_DIR` has write permissions

## Resources

- **API Documentation**: <http://localhost:8000/api/docs>
- **GraphQL Playground**: <http://localhost:8000/api/v1/graphql>
- **Admin Dashboard**: <http://localhost:3000>
- **Meilisearch Dashboard**: <http://localhost:7700>
- **MinIO Console**: <http://localhost:9001>

## Support

For questions or issues:
- Check the [Getting Started Guide](./getting-started.md)
- Review [API Documentation](http://localhost:8000/api/docs)
- Open an issue on GitHub

---

**Ready to launch Bakalr Boutique!** 🛍️
