#!/usr/bin/env python3
"""
Script to add missing seed entries that failed due to timeouts
"""
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import requests

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "bsakweson@gmail.com"
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Angelbenise1")

# Missing items to add
MISSING_CATEGORIES = [
    "braiding-hair",
    "clippers-trimmers",
    "cosmetics",
    "curling-wands",
    "false-lashes",
    "flat-irons",
    "hair-care",
    "hair-tools",
    "kinky-straight-hair",
    "lace-melting",
    "wig-caps",
    "wig-glue-adhesive",
]

MISSING_BRANDS = [
    "andis",
    "ardell",
    "babyliss-pro",
    "bold-hold",
    "cantu",
    "mielle-organics",
    "outre",
    "sensationnel",
    "shea-moisture",
    "wahl",
]

MISSING_PRODUCTS = [
    "bold-hold-lace-tint-spray",
    "brazilian-kinky-curly-bundle",
    "brazilian-water-wave-bundle",
    "full-lace-wig-straight-613-blonde",
    "glueless-lace-front-wig-body-wave",
    "hd-lace-frontal-13x4-body-wave",
    "hd-lace-frontal-13x6-deep-wave",
    "wig-grip-band-velvet",
]


class EntryAdder:
    def __init__(self):
        self.token = None
        self.content_types = {}
        self.seed_data = {}
        self.added_count = 0
        self.skipped_count = 0

    def login(self):
        """Get authentication token"""
        print("🔐 Authenticating...")
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        print("✅ Authenticated")

    def load_seed_data(self):
        """Load seed data files"""
        print("\n📂 Loading seed data...")
        seed_dir = Path(__file__).parent / "seeds" / "sample-data"

        files = {
            "categories": seed_dir / "06-categories.json",
            "brands": seed_dir / "07-brands.json",
            "products": seed_dir / "08-products.json",
        }

        for key, path in files.items():
            if path.exists():
                with open(path) as f:
                    self.seed_data[key] = json.load(f).get("entries", [])
                print(f"✅ Loaded {key}: {len(self.seed_data[key])} entries")
            else:
                print(f"⚠️  Missing {key} file: {path}")

    def get_content_types(self):
        """Get all content types"""
        print("\n📋 Fetching content types...")
        resp = requests.get(
            f"{BASE_URL}/content/types",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        resp.raise_for_status()

        for ct in resp.json():
            self.content_types[ct["api_id"]] = ct["id"]

        print(f"✅ Found {len(self.content_types)} content types:")
        for api_id, ct_id in self.content_types.items():
            print(f"   - {api_id}: {ct_id}")

    def add_entry(self, content_type_api_id: str, entry_data: dict) -> bool:
        """Add a single entry"""
        try:
            # Prepare data payload
            data = entry_data.get("data", {}).copy()

            # Add SEO fields if present
            if "seo_title" in entry_data:
                data["seo_title"] = entry_data["seo_title"]
            if "seo_description" in entry_data:
                data["seo_description"] = entry_data["seo_description"]

            # Prepare payload
            payload = {
                "content_type_id": self.content_types[content_type_api_id],
                "title": entry_data.get("slug", ""),
                "slug": entry_data["slug"],
                "status": entry_data.get("status", "published"),
                "data": data,
            }

            resp = requests.post(
                f"{BASE_URL}/content/entries",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
            )

            if resp.status_code == 201:
                return True
            else:
                print(f"   ❌ HTTP {resp.status_code}: {resp.text[:100]}")
                return False

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            return False

    def add_missing_categories(self):
        """Add missing categories"""
        print("\n📦 Adding missing categories...")

        # Build lookup
        category_lookup = {entry["slug"]: entry for entry in self.seed_data.get("categories", [])}

        for slug in MISSING_CATEGORIES:
            if slug in category_lookup:
                entry = category_lookup[slug]
                print(f"  Adding: {slug}...", end=" ", flush=True)
                if self.add_entry("category", entry):
                    print("✅")
                    self.added_count += 1
                else:
                    self.skipped_count += 1
            else:
                print(f"  ⚠️  {slug} not found in seed data")
                self.skipped_count += 1

    def add_missing_brands(self):
        """Add missing brands"""
        print("\n🏢 Adding missing brands...")

        # Build lookup
        brand_lookup = {entry["slug"]: entry for entry in self.seed_data.get("brands", [])}

        for slug in MISSING_BRANDS:
            if slug in brand_lookup:
                entry = brand_lookup[slug]
                print(f"  Adding: {slug}...", end=" ", flush=True)
                if self.add_entry("brand", entry):
                    print("✅")
                    self.added_count += 1
                else:
                    self.skipped_count += 1
            else:
                print(f"  ⚠️  {slug} not found in seed data")
                self.skipped_count += 1

    def add_missing_products(self):
        """Add missing products"""
        print("\n🛍️  Adding missing products...")

        # Build lookup
        product_lookup = {entry["slug"]: entry for entry in self.seed_data.get("products", [])}

        for slug in MISSING_PRODUCTS:
            if slug in product_lookup:
                entry = product_lookup[slug]
                print(f"  Adding: {slug}...", end=" ", flush=True)
                if self.add_entry("product", entry):
                    print("✅")
                    self.added_count += 1
                else:
                    self.skipped_count += 1
            else:
                print(f"  ⚠️  {slug} not found in seed data")
                self.skipped_count += 1

    def run(self):
        """Main execution"""
        try:
            self.login()
            self.load_seed_data()
            self.get_content_types()

            self.add_missing_categories()
            self.add_missing_brands()
            self.add_missing_products()

            print("\n" + "=" * 50)
            print(f"✅ Added: {self.added_count} entries")
            print(f"⚠️  Skipped: {self.skipped_count} entries")
            print(f"📊 Total: {self.added_count + self.skipped_count} entries processed")
            print("=" * 50)

        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    adder = EntryAdder()
    adder.run()
