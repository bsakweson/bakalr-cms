# Translation APIs Guide

Bakalr CMS supports multiple translation APIs for automatic content translation. This guide covers setup for various providers.

## Table of Contents

- [Free & Open Source Options](#free--open-source-options)
- [Commercial Options (Free Tiers Available)](#commercial-options-free-tiers-available)
- [Setup Instructions](#setup-instructions)
- [Comparison Table](#comparison-table)

## Free & Open Source Options

### 1. LibreTranslate (Recommended for Self-Hosting)

**100% Free & Open Source** - Self-hostable translation API with no limitations.

**Pros:**
- ✅ Completely free and open source
- ✅ No API key required
- ✅ Self-hostable (full data privacy)
- ✅ No rate limits or character limits
- ✅ Supports 30+ languages
- ✅ Python library available

**Setup with Docker:**

```bash
# Run LibreTranslate server
docker run -ti --rm -p 5000:5000 libretranslate/libretranslate

# Or with docker-compose (add to your docker-compose.yml)
services:
  libretranslate:
    image: libretranslate/libretranslate:latest
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - LT_LOAD_ONLY=en,es,fr,de,it,pt,ru,zh,ja,ko  # Languages to load
    volumes:
      - ./libretranslate-data:/home/libretranslate/.local
```

**Environment Configuration:**

```bash
# .env
TRANSLATION_PROVIDER=libretranslate
LIBRETRANSLATE_URL=http://localhost:5000
# No API key needed!
```

**Python Integration:**

```python
import requests

def translate_text(text: str, source: str, target: str) -> str:
    response = requests.post(
        "http://localhost:5000/translate",
        json={
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        }
    )
    return response.json()["translatedText"]
```

---

### 2. Argos Translate (Offline Python Library)

**Completely Offline** - No API calls, no internet needed.

**Pros:**
- ✅ 100% free and open source
- ✅ Works offline
- ✅ Fast for short texts
- ✅ No external dependencies

**Cons:**
- ⚠️ Limited languages (15 languages)
- ⚠️ Lower quality than cloud services
- ⚠️ Requires model downloads (~100MB per language pair)

**Setup:**

```bash
# Install
pip install argostranslate

# Download language models
import argostranslate.package
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
package_to_install = next(
    filter(lambda x: x.from_code == "en" and x.to_code == "es", available_packages)
)
argostranslate.package.install_from_path(package_to_install.download())
```

**Usage:**

```python
import argostranslate.translate

def translate_text(text: str, source: str, target: str) -> str:
    return argostranslate.translate.translate(text, source, target)
```

---

## Commercial Options (Free Tiers Available)

### 3. Google Cloud Translation API

**500,000 characters/month free**, then $20 per million characters.

**Pros:**
- ✅ High quality translations
- ✅ 130+ languages
- ✅ Fast and reliable
- ✅ Generous free tier

**Cons:**
- ⚠️ Requires Google Cloud account
- ⚠️ Credit card required (even for free tier)
- ⚠️ Paid after free tier

**Setup:**

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable "Cloud Translation API"
   - Create API credentials (API Key or Service Account)

2. **Get API Key:**
   ```bash
   # In Google Cloud Console:
   # APIs & Services → Credentials → Create Credentials → API Key
   ```

3. **Environment Configuration:**
   ```bash
   # .env
   TRANSLATION_PROVIDER=google
   GOOGLE_TRANSLATE_API_KEY=your_api_key_here
   ```

4. **Install Client Library:**
   ```bash
   pip install google-cloud-translate
   ```

5. **Python Integration:**
   ```python
   from google.cloud import translate_v2 as translate
   
   def translate_text(text: str, target: str) -> str:
       translate_client = translate.Client(api_key="YOUR_API_KEY")
       result = translate_client.translate(text, target_language=target)
       return result['translatedText']
   ```

---

### 4. DeepL API

**500,000 characters/month free**, then $5.49 per million characters.

**Pros:**
- ✅ Best translation quality
- ✅ Very generous free tier
- ✅ No credit card required for free tier
- ✅ 31 languages

**Cons:**
- ⚠️ Fewer languages than Google
- ⚠️ Requires signup

**Setup:**

1. **Sign Up:**
   - Go to [DeepL API](https://www.deepl.com/pro-api)
   - Sign up for free account
   - Get API key from dashboard

2. **Environment Configuration:**
   ```bash
   # .env
   TRANSLATION_PROVIDER=deepl
   DEEPL_API_KEY=your_api_key_here
   DEEPL_API_URL=https://api-free.deepl.com/v2/translate  # Free tier
   # or
   DEEPL_API_URL=https://api.deepl.com/v2/translate  # Pro tier
   ```

3. **Install Client Library:**
   ```bash
   pip install deepl
   ```

4. **Python Integration:**
   ```python
   import deepl
   
   def translate_text(text: str, target: str) -> str:
       translator = deepl.Translator("YOUR_API_KEY")
       result = translator.translate_text(text, target_lang=target.upper())
       return result.text
   ```

---

### 5. Microsoft Translator

**2 million characters/month free**, then $10 per million characters.

**Pros:**
- ✅ Very generous free tier
- ✅ 100+ languages
- ✅ Good quality

**Cons:**
- ⚠️ Requires Azure account
- ⚠️ Credit card required

**Setup:**

1. **Create Azure Account:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create "Translator" resource
   - Get API key and region

2. **Environment Configuration:**
   ```bash
   # .env
   TRANSLATION_PROVIDER=microsoft
   MICROSOFT_TRANSLATOR_KEY=your_api_key
   MICROSOFT_TRANSLATOR_REGION=your_region  # e.g., westus2
   ```

---

## Comparison Table

| Provider | Free Tier | Languages | Quality | Setup | API Key | Credit Card |
|----------|-----------|-----------|---------|-------|---------|-------------|
| **LibreTranslate** | ✅ Unlimited | 30+ | ⭐⭐⭐ | Easy | ❌ Not needed | ❌ No |
| **Argos Translate** | ✅ Unlimited | 15 | ⭐⭐ | Easy | ❌ Not needed | ❌ No |
| **Google Translate** | 500k chars/mo | 130+ | ⭐⭐⭐⭐⭐ | Medium | ✅ Required | ⚠️ Yes |
| **DeepL** | 500k chars/mo | 31 | ⭐⭐⭐⭐⭐ | Easy | ✅ Required | ❌ No |
| **Microsoft** | 2M chars/mo | 100+ | ⭐⭐⭐⭐ | Medium | ✅ Required | ⚠️ Yes |

---

## Setup Instructions

### Option 1: LibreTranslate (Recommended for Production)

Best for self-hosted, privacy-focused, or high-volume usage.

```bash
# 1. Add to docker-compose.yml
services:
  libretranslate:
    image: libretranslate/libretranslate:latest
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - LT_LOAD_ONLY=en,es,fr,de,it,pt,ru,zh,ja,ko
    volumes:
      - ./libretranslate-data:/home/libretranslate/.local

# 2. Start service
docker-compose up -d libretranslate

# 3. Configure Bakalr CMS
# In .env:
TRANSLATION_PROVIDER=libretranslate
LIBRETRANSLATE_URL=http://libretranslate:5000
```

### Option 2: DeepL (Recommended for Cloud)

Best for cloud deployments with best quality and no credit card.

```bash
# 1. Sign up at https://www.deepl.com/pro-api (free)

# 2. Get API key from dashboard

# 3. Install library
pip install deepl

# 4. Configure Bakalr CMS
# In .env:
TRANSLATION_PROVIDER=deepl
DEEPL_API_KEY=your_api_key_here
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

### Option 3: Google Translate (Recommended for Scale)

Best for high-volume usage with extensive language support.

```bash
# 1. Create Google Cloud project
# 2. Enable Cloud Translation API
# 3. Create API key

# 4. Install library
pip install google-cloud-translate

# 5. Configure Bakalr CMS
# In .env:
TRANSLATION_PROVIDER=google
GOOGLE_TRANSLATE_API_KEY=your_api_key_here
```

---

## Testing Translation

Test your translation setup:

```bash
# Test translation endpoint
curl -X POST http://localhost:8000/api/v1/translation/translate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "target_locale": "es",
    "source_locale": "en"
  }'

# Expected response:
{
  "translated_text": "¡Hola, mundo!",
  "source_locale": "en",
  "target_locale": "es",
  "provider": "libretranslate"
}
```

---

## Recommendations

### For Development/Testing

→ **LibreTranslate** or **Argos Translate** (completely free, no signup)

### For Production (Self-Hosted)

→ **LibreTranslate** (unlimited, free, privacy-focused)

### For Production (Cloud)

→ **DeepL** (best quality, no credit card, 500k free)
→ **Microsoft** (most generous free tier: 2M chars/month)

### For High Volume

→ **Google Translate** (reliable, extensive language support)

---

## Language Support

### LibreTranslate (30+ languages)

English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, Dutch, Polish, Swedish, Turkish, Czech, Romanian, Greek, Hungarian, Danish, Finnish, Norwegian, and more.

### DeepL (31 languages)

English (US/UK), German, French, Spanish, Italian, Dutch, Polish, Portuguese (EU/BR), Russian, Japanese, Chinese, Bulgarian, Czech, Danish, Estonian, Finnish, Greek, Hungarian, Latvian, Lithuanian, Romanian, Slovak, Slovenian, Swedish, Indonesian, Korean, Norwegian, Turkish, Ukrainian.

### Google Translate (130+ languages)

Covers virtually all major world languages.

---

## Cost Comparison (for 10M characters/month)

| Provider | Monthly Cost | Notes |
|----------|-------------|-------|
| LibreTranslate | **$0** | Self-hosted (server costs only) |
| Argos Translate | **$0** | Offline (no costs) |
| DeepL | $54.90 | After 500k free |
| Microsoft | $80 | After 2M free |
| Google | $200 | After 500k free |

---

## Getting Started

1. **For Quick Start**: Use LibreTranslate with Docker
2. **For Best Quality**: Sign up for DeepL (free, no credit card)
3. **For Scale**: Set up Google Cloud Translation API

All options are already integrated into Bakalr CMS - just configure your `.env` file!
