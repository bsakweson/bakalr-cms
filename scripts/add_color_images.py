#!/usr/bin/env python3
"""Add images to Brazilian Body Wave color variants in CMS."""

import requests

API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL = "http://localhost:8000"

# Get the product
response = requests.get(
    f"{BASE_URL}/api/v1/content/entries",
    headers={"X-API-Key": API_KEY},
    params={"content_type_slug": "product", "slug": "brazilian-body-wave-bundle", "per_page": 1},
)
item = response.json()["items"][0]
product_id = item["id"]
data = item["data"]

# Get the base product image URL
base_image = data.get("primary_image", "/images/products/brazilian-body-wave.jpg")
print(f"Base image: {base_image}")

# Update colors with image URLs (using Unsplash hair images as placeholders)
# In production, you'd replace these with your actual product images per color
data["available_colors"] = [
    {
        "value": "natural-black",
        "label": "Natural Black",
        "hex": "#1a1a1a",
        "image": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&h=600&fit=crop",
    },
    {
        "value": "1b",
        "label": "#1B Off Black",
        "hex": "#2d2d2d",
        "image": "https://images.unsplash.com/photo-1605980776566-0ed5fd7a6c39?w=600&h=600&fit=crop",
    },
    {
        "value": "2",
        "label": "#2 Dark Brown",
        "hex": "#3d2314",
        "image": "https://images.unsplash.com/photo-1595515106969-1ce29566ff1c?w=600&h=600&fit=crop",
    },
    {
        "value": "4",
        "label": "#4 Medium Brown",
        "hex": "#5a3825",
        "image": "https://images.unsplash.com/photo-1562259929-b4e1fd3aef09?w=600&h=600&fit=crop",
    },
    {
        "value": "27",
        "label": "#27 Honey Blonde",
        "hex": "#c99550",
        "image": "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?w=600&h=600&fit=crop",
    },
    {
        "value": "30",
        "label": "#30 Auburn",
        "hex": "#8b4513",
        "image": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=600&h=600&fit=crop",
    },
    {
        "value": "613",
        "label": "#613 Platinum Blonde",
        "hex": "#f5e6c8",
        "image": "https://images.unsplash.com/photo-1492106087820-71f1a00d2b11?w=600&h=600&fit=crop",
    },
    {
        "value": "1b-27",
        "label": "Ombre 1B/27",
        "hex": "#2d2d2d",
        "image": "https://images.unsplash.com/photo-1519699047748-de8e457a634e?w=600&h=600&fit=crop",
    },
    {
        "value": "1b-30",
        "label": "Ombre 1B/30",
        "hex": "#2d2d2d",
        "image": "https://images.unsplash.com/photo-1534180477871-5d6cc81f3920?w=600&h=600&fit=crop",
    },
]

response = requests.patch(
    f"{BASE_URL}/api/v1/content/entries/{product_id}",
    headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    json={"data": data},
)
result = response.json()
colors = result.get("data", {}).get("available_colors", [])
print(f"\nUpdated Brazilian Body Wave with {len(colors)} colors with images:")
for c in colors:
    img = c.get("image", "No image")
    print(f"  - {c['label']}: {img[:60]}...")
