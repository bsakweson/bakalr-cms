# Bakalr CMS Seeds

This directory contains seed data for the Bakalr Boutique beauty supply store.

## Directory Structure

```text
seeds/
├── README.md                    # This file
├── seed_runner.py               # Master seed script
├── themes/
│   └── boutique-theme.json      # Dark chocolate & gold theme
├── content-types/
│   ├── product.json             # Product content type schema
│   ├── category.json            # Category content type schema
│   ├── brand.json               # Brand content type schema
│   ├── collection.json          # Collection content type schema
│   └── review.json              # Review content type schema
├── locales/
│   └── enabled-locales.json     # en (default), es, fr
└── sample-data/
    ├── categories.json          # Hair, Skin, Nails, Body, Tools
    ├── brands.json              # Beauty brands
    └── products/
        ├── hair-products.json   # Hair care products
        ├── skin-products.json   # Skincare products
        ├── nail-products.json   # Nail products
        └── body-products.json   # Body care products
```

## Usage

### Prerequisites

1. Bakalr CMS backend running on `http://localhost:8000`
2. Admin user account created
3. Python 3.11+ with `httpx` installed

### Running Seeds

```bash
# Full seed (themes + content types + locales + sample data)
cd /path/to/bakalr-cms
poetry run python seeds/seed_runner.py

# Seed specific components
poetry run python seeds/seed_runner.py --only themes
poetry run python seeds/seed_runner.py --only content-types
poetry run python seeds/seed_runner.py --only locales
poetry run python seeds/seed_runner.py --only sample-data

# Reset and reseed (deletes existing data first)
poetry run python seeds/seed_runner.py --reset

# Dry run (shows what would be created)
poetry run python seeds/seed_runner.py --dry-run
```

### Environment Variables

The seed runner uses these environment variables:

```bash
SEED_API_URL=http://localhost:8000/api/v1  # API base URL
SEED_ADMIN_EMAIL=admin@example.com          # Admin email
SEED_ADMIN_PASSWORD=your-password           # Admin password
```

Or create a `.env.seed` file in the seeds directory.

## Content Types

### Product
- `name` (string, required) - Product name
- `description` (richtext) - Product description
- `price` (number, required) - Price in USD
- `compare_at_price` (number) - Original price for sales
- `sku` (string, required) - Stock keeping unit
- `barcode` (string) - UPC/EAN barcode
- `quantity` (number) - Stock quantity
- `category_id` (reference) - Link to category
- `brand_id` (reference) - Link to brand
- `images` (array) - Product images
- `featured_image` (image) - Main product image
- `tags` (array) - Product tags
- `is_featured` (boolean) - Featured product flag
- `is_active` (boolean) - Active/visible flag

### Category

- `name` (string, required) - Category name
- `description` (textarea) - Category description
- `image` (image) - Category image
- `parent_id` (reference) - Parent category (for hierarchy)
- `sort_order` (number) - Display order

### Brand

- `name` (string, required) - Brand name
- `description` (richtext) - Brand story
- `logo` (image) - Brand logo
- `website` (url) - Brand website
- `country` (string) - Country of origin

### Collection

- `name` (string, required) - Collection name
- `description` (richtext) - Collection description
- `image` (image) - Collection banner
- `products` (array) - Product IDs in collection
- `is_featured` (boolean) - Featured collection flag
- `start_date` (date) - Collection start date
- `end_date` (date) - Collection end date

### Review

- `product_id` (reference, required) - Product being reviewed
- `rating` (number, required) - 1-5 star rating
- `title` (string) - Review title
- `content` (textarea, required) - Review text
- `reviewer_name` (string, required) - Reviewer name
- `reviewer_email` (email) - Reviewer email
- `is_verified` (boolean) - Verified purchase flag
- `is_approved` (boolean) - Moderation status

## Multi-Language Support

All content supports translations in:
- **English (en)** - Default language
- **Spanish (es)** - Spanish translations
- **French (fr)** - French translations

Translatable fields are marked in the content type schemas.

## Theme

The boutique theme uses:
- **Primary**: Dark Chocolate Brown (#3D2817)
- **Secondary**: Rich Gold (#D4AF37)
- **Accent**: Rose Gold (#B76E79)
- **Background**: Cream (#FDF5E6)
- **Text**: Dark Brown (#2C1810)

## Adding New Seed Data

1. Add JSON files to the appropriate directory
2. Follow the existing schema format
3. Include translations in `_translations` object
4. Run the seed runner

## License

Part of Bakalr CMS - Proprietary
