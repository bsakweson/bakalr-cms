#!/usr/bin/env python3
"""
Bakalr CMS Seed Runner

Seeds the CMS with themes, content types, locales, and sample data.

Usage:
    poetry run python seeds/seed_runner.py                    # Full seed (shows inventory first)
    poetry run python seeds/seed_runner.py --inventory        # Show inventory only
    poetry run python seeds/seed_runner.py --no-inventory     # Skip inventory check
    poetry run python seeds/seed_runner.py --only themes      # Only themes
    poetry run python seeds/seed_runner.py --only content-types
    poetry run python seeds/seed_runner.py --only locales
    poetry run python seeds/seed_runner.py --only sample-data
    poetry run python seeds/seed_runner.py --file 02-navigation.json  # Single file
    poetry run python seeds/seed_runner.py --reset            # Delete and reseed all
    poetry run python seeds/seed_runner.py --reset-type 01-page.json  # Reset specific content type
    poetry run python seeds/seed_runner.py --dry-run          # Show what would be created
"""

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

# Configuration
DEFAULT_API_URL = "http://localhost:8000/api/v1"
SEEDS_DIR = Path(__file__).parent
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2  # seconds


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def log_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")


def log_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")


def log_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


def log_error(msg: str):
    print(f"{Colors.RED}✗{Colors.END} {msg}")


def log_retry(msg: str):
    print(f"{Colors.YELLOW}↻{Colors.END} {msg}")


def log_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


class SeedRunner:
    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        email: Optional[str] = None,
        password: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.api_url = api_url.rstrip("/")
        self.email = email or os.getenv("SEED_ADMIN_EMAIL", "")
        self.password = password or os.getenv("SEED_ADMIN_PASSWORD", "")
        self.dry_run = dry_run
        self.token: Optional[str] = None
        # Increased timeout for translation operations
        self.client = httpx.Client(timeout=120.0)

        # Track created items for relationships
        self.created_content_types: Dict[str, str] = {}  # slug -> id
        self.created_categories: Dict[str, str] = {}  # slug -> id
        self.created_brands: Dict[str, str] = {}  # slug -> id

    def authenticate(self) -> bool:
        """Login and get JWT token"""
        if self.dry_run:
            log_info("DRY RUN: Would authenticate with API")
            return True

        if not self.password:
            log_error("No password provided. Set SEED_ADMIN_PASSWORD environment variable.")
            return False

        try:
            response = self.client.post(
                f"{self.api_url}/auth/login",
                json={"email": self.email, "password": self.password},
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                log_success(f"Authenticated as {self.email}")
                return True
            else:
                log_error(f"Authentication failed: {response.text}")
                return False
        except Exception as e:
            log_error(f"Connection error: {e}")
            return False

    def _headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file"""
        with open(path) as f:
            return json.load(f)

    def _api_post(self, endpoint: str, data: Dict, description: str = "") -> Optional[Dict]:
        """Make POST request to API - retries until success or already exists"""
        if self.dry_run:
            log_info(f"DRY RUN: POST {endpoint}")
            return {"id": "dry-run-id"}

        retry_delay = INITIAL_RETRY_DELAY
        attempt = 0

        while True:  # Keep retrying until success
            attempt += 1
            try:
                response = self.client.post(
                    f"{self.api_url}/{endpoint}",
                    json=data,
                    headers=self._headers(),
                )
                if response.status_code in (200, 201):
                    return response.json()
                elif response.status_code == 409:
                    # Already exists - this is idempotent, skip
                    log_warning(f"Already exists, skipping: {description or endpoint}")
                    return {"id": "existing", "_already_exists": True}
                elif response.status_code == 400:
                    # Check if it's an "already exists" error
                    error_text = response.text.lower()
                    if "already exists" in error_text or "duplicate" in error_text:
                        log_warning(f"Already exists, skipping: {description or endpoint}")
                        return {"id": "existing", "_already_exists": True}
                    # Other 400 errors are not retryable - genuine validation errors
                    log_error(f"Validation error for {description or endpoint}: {response.text}")
                    return None
                else:
                    # All other errors - retry
                    log_retry(
                        f"Error ({response.status_code}), retrying in {retry_delay}s... (attempt {attempt})"
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)  # Cap at 60 seconds
                    continue
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                log_retry(
                    f"Connection error ({type(e).__name__}), retrying in {retry_delay}s... (attempt {attempt})"
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
                continue
            except Exception as e:
                log_error(f"Unexpected error: {e}")
                return None

    def _api_get(self, endpoint: str) -> Optional[Dict]:
        """Make GET request to API - retries until success"""
        if self.dry_run:
            return None

        retry_delay = INITIAL_RETRY_DELAY
        attempt = 0

        while True:  # Keep retrying until success
            attempt += 1
            try:
                response = self.client.get(
                    f"{self.api_url}/{endpoint}",
                    headers=self._headers(),
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None  # Not found is a valid response
                else:
                    log_retry(
                        f"GET error ({response.status_code}), retrying in {retry_delay}s... (attempt {attempt})"
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)
                    continue
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                log_retry(
                    f"Connection error ({type(e).__name__}), retrying in {retry_delay}s... (attempt {attempt})"
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
                continue
            except Exception as e:
                log_error(f"Unexpected error: {e}")
                return None

    def _api_delete(self, endpoint: str) -> bool:
        """Make DELETE request to API - retries until success"""
        if self.dry_run:
            log_info(f"DRY RUN: DELETE {endpoint}")
            return True

        retry_delay = INITIAL_RETRY_DELAY
        attempt = 0

        while True:  # Keep retrying until success
            attempt += 1
            try:
                response = self.client.delete(
                    f"{self.api_url}/{endpoint}",
                    headers=self._headers(),
                )
                if response.status_code in (200, 204):
                    return True
                elif response.status_code == 404:
                    # Already deleted - idempotent
                    return True
                else:
                    log_retry(
                        f"DELETE error ({response.status_code}), retrying in {retry_delay}s... (attempt {attempt})"
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)
                    continue
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                log_retry(
                    f"Connection error ({type(e).__name__}), retrying in {retry_delay}s... (attempt {attempt})"
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
                continue
            except Exception as e:
                log_error(f"Unexpected error: {e}")
                return False

    # ==================== INVENTORY ====================

    def show_inventory(self):
        """Show current inventory of content types and entries in the database"""
        log_header("Current Database Inventory")

        if not self.token and not self.authenticate():
            return False

        # Get all content types
        types_result = self._api_get("content/types")
        if not types_result:
            log_warning("Could not fetch content types")
            return True

        items = types_result if isinstance(types_result, list) else types_result.get("items", [])
        
        if not items:
            log_info("Database is empty - no content types found")
            print()
            return True

        # Build inventory
        total_entries = 0
        inventory = []

        for ct in items:
            api_id = ct.get("api_id")
            name = ct.get("name")
            
            # Count entries for this content type (API uses content_type_slug)
            entries_result = self._api_get(f"content/entries?content_type_slug={api_id}&page_size=1")
            entry_count = 0
            if entries_result:
                entry_count = entries_result.get("total", 0)
            
            inventory.append({
                "name": name,
                "api_id": api_id,
                "entries": entry_count
            })
            total_entries += entry_count

        # Display inventory
        print(f"\n{'Content Type':<35} {'API ID':<30} {'Entries':>8}")
        print("-" * 75)
        
        for item in sorted(inventory, key=lambda x: x["name"]):
            print(f"{item['name']:<35} {item['api_id']:<30} {item['entries']:>8}")
        
        print("-" * 75)
        print(f"{'TOTAL':<35} {len(inventory)} content types{' ':>13} {total_entries:>8}")
        print()

        return True

    # ==================== RESET DATA ====================

    def reset_all(self):
        """Delete all content entries and content types"""
        log_header("Resetting Database Content")

        if not self.authenticate():
            return False

        # First delete all content entries
        log_info("Fetching content entries to delete...")
        entries_result = self._api_get("content/entries?page_size=1000")
        if entries_result:
            items = entries_result.get("items", [])
            log_info(f"Found {len(items)} content entries to delete")
            for entry in items:
                entry_id = entry.get("id")
                slug = entry.get("slug")
                if self._api_delete(f"content/entries/{entry_id}"):
                    log_success(f"Deleted entry: {slug}")
                else:
                    log_error(f"Failed to delete entry: {slug}")

        # Then delete all content types
        log_info("Fetching content types to delete...")
        types_result = self._api_get("content/types")
        if types_result:
            items = (
                types_result if isinstance(types_result, list) else types_result.get("items", [])
            )
            log_info(f"Found {len(items)} content types to delete")
            for ct in items:
                ct_id = ct.get("id")
                name = ct.get("name")
                if self._api_delete(f"content/types/{ct_id}"):
                    log_success(f"Deleted content type: {name}")
                else:
                    log_error(f"Failed to delete content type: {name}")

        log_success("Reset complete!")
        return True

    def reset_content_type(self, content_type_file: str):
        """Reset a specific content type and its data by file name"""
        log_header(f"Resetting Content Type: {content_type_file}")

        if not self.authenticate():
            return False

        # Find the content type file
        content_types_dir = SEEDS_DIR / "content-types"
        ct_file = content_types_dir / content_type_file
        
        if not ct_file.exists():
            # Try without path prefix
            matching = list(content_types_dir.glob(f"*{content_type_file}*"))
            if matching:
                ct_file = matching[0]
            else:
                log_error(f"Content type file not found: {content_type_file}")
                log_info(f"Available files: {[f.name for f in content_types_dir.glob('*.json')]}")
                return False

        # Load the content type definition to get api_id
        ct_data = self._load_json(ct_file)
        api_id = ct_data.get("api_id")
        
        if not api_id:
            log_error(f"No api_id found in {ct_file.name}")
            return False

        log_info(f"Resetting content type: {ct_data['name']} (api_id: {api_id})")

        # Find the content type ID
        types_result = self._api_get("content/types")
        content_type_id = None
        if types_result:
            items = types_result if isinstance(types_result, list) else types_result.get("items", [])
            for ct in items:
                if ct.get("api_id") == api_id:
                    content_type_id = ct.get("id")
                    break

        if content_type_id:
            # Delete all content entries of this type
            log_info(f"Fetching entries for content type: {api_id}...")
            entries_result = self._api_get(f"content/entries?content_type_slug={api_id}&page_size=1000")
            if entries_result:
                items = entries_result.get("items", [])
                log_info(f"Found {len(items)} entries to delete")
                for entry in items:
                    entry_id = entry.get("id")
                    slug = entry.get("slug")
                    if self._api_delete(f"content/entries/{entry_id}"):
                        log_success(f"Deleted entry: {slug}")
                    else:
                        log_error(f"Failed to delete entry: {slug}")

            # Delete the content type itself
            log_info(f"Deleting content type: {ct_data['name']}...")
            if self._api_delete(f"content/types/{content_type_id}"):
                log_success(f"Deleted content type: {ct_data['name']}")
            else:
                log_error(f"Failed to delete content type: {ct_data['name']}")
        else:
            log_warning(f"Content type {api_id} not found in database, will create fresh")

        log_success(f"Reset complete for: {api_id}")
        return True

    def seed_content_type_file(self, content_type_file: str):
        """Seed a specific content type and find its related sample data"""
        log_header(f"Re-seeding Content Type: {content_type_file}")

        if not self.token and not self.authenticate():
            return False

        # Find the content type file
        content_types_dir = SEEDS_DIR / "content-types"
        ct_file = content_types_dir / content_type_file
        
        if not ct_file.exists():
            matching = list(content_types_dir.glob(f"*{content_type_file}*"))
            if matching:
                ct_file = matching[0]
            else:
                log_error(f"Content type file not found: {content_type_file}")
                return False

        # Load and create the content type
        ct_data = self._load_json(ct_file)
        api_id = ct_data.get("api_id")

        log_info(f"Creating content type: {ct_data['name']}")
        payload = {
            "name": ct_data["name"],
            "api_id": ct_data["api_id"],
            "description": ct_data.get("description", ""),
            "fields": ct_data.get("fields", []),
        }
        if ct_data.get("display_field"):
            payload["display_field"] = ct_data["display_field"]

        result = self._api_post("content/types", payload, description=f"content type: {ct_data['name']}")
        if result and not result.get("_already_exists"):
            self.created_content_types[api_id] = result.get("id")
            log_success(f"Created content type: {ct_data['name']} (id: {result.get('id')})")

        # Fetch content type IDs for reference
        self._fetch_content_type_ids()

        # Find and seed related sample data files
        sample_data_dir = SEEDS_DIR / "sample-data"
        if sample_data_dir.exists():
            self.created_entries = {}
            for sample_file in sorted(sample_data_dir.glob("*.json")):
                data = self._load_json(sample_file)
                
                # Check if this file contains entries for our content type
                if isinstance(data, list):
                    entries = data
                    shared_content_type = None
                else:
                    entries = data.get("entries", [])
                    shared_content_type = data.get("content_type")

                # Filter entries that match our content type
                matching_entries = []
                for entry in entries:
                    entry_ct = entry.get("content_type_api_id") or entry.get("content_type") or shared_content_type
                    if entry_ct == api_id:
                        matching_entries.append(entry)

                if matching_entries:
                    log_info(f"Found {len(matching_entries)} entries in {sample_file.name}")
                    for entry in matching_entries:
                        self._create_content_entry(entry, shared_content_type=shared_content_type)

        log_success(f"Re-seeding complete for: {api_id}")
        return True

    # ==================== SEED THEMES ====================

    def seed_themes(self):
        """Seed theme definitions"""
        log_header("Seeding Themes")

        themes_dir = SEEDS_DIR / "themes"
        if not themes_dir.exists():
            log_warning("No themes directory found")
            return

        for theme_file in themes_dir.glob("*.json"):
            theme_data = self._load_json(theme_file)
            log_info(f"Creating theme: {theme_data.get('display_name', theme_data.get('name'))}")

            result = self._api_post(
                "themes", theme_data, description=f"theme: {theme_data['name']}"
            )
            if result and not result.get("_already_exists"):
                log_success(f"Created theme: {theme_data['name']}")

    # ==================== SEED LOCALES ====================

    def seed_locales(self):
        """Seed enabled locales"""
        log_header("Seeding Locales")

        locales_file = SEEDS_DIR / "locales" / "enabled-locales.json"
        if not locales_file.exists():
            log_warning("No locales file found")
            return

        data = self._load_json(locales_file)
        for locale in data.get("locales", []):
            if locale.get("is_default"):
                log_info(f"Skipping default locale: {locale['code']}")
                continue

            log_info(f"Enabling locale: {locale['name']} ({locale['code']})")
            result = self._api_post(
                "translation/locales",
                {
                    "code": locale["code"],
                    "name": locale["name"],
                    "native_name": locale.get("native_name", locale["name"]),
                    "is_enabled": locale.get("is_enabled", True),
                },
                description=f"locale: {locale['code']}",
            )
            if result and not result.get("_already_exists"):
                log_success(f"Enabled locale: {locale['code']}")

    # ==================== SEED CONTENT TYPES ====================

    def seed_content_types(self):
        """Seed content type definitions"""
        log_header("Seeding Content Types")

        content_types_dir = SEEDS_DIR / "content-types"
        if not content_types_dir.exists():
            log_warning("No content-types directory found")
            return

        # Load all JSON files in sorted order (numbered files like 01-page.json)
        ct_files = sorted(content_types_dir.glob("*.json"))

        if not ct_files:
            log_warning("No content type files found")
            return

        for ct_file in ct_files:
            ct_data = self._load_json(ct_file)
            if not ct_data:
                continue

            log_info(f"Creating content type: {ct_data['name']}")

            # Prepare the payload matching API schema (ContentTypeCreate)
            # API requires: name, api_id, fields[], optional: description, display_field
            payload = {
                "name": ct_data["name"],
                "api_id": ct_data["api_id"],
                "description": ct_data.get("description", ""),
                "fields": ct_data.get("fields", []),
            }

            # Add display_field if present
            if ct_data.get("display_field"):
                payload["display_field"] = ct_data["display_field"]

            result = self._api_post(
                "content/types", payload, description=f"content type: {ct_data['name']}"
            )
            if result and not result.get("_already_exists"):
                self.created_content_types[ct_data["api_id"]] = result.get("id")
                log_success(f"Created content type: {ct_data['name']} (id: {result.get('id')})")
            elif result and result.get("_already_exists"):
                # Fetch the existing ID
                self._fetch_content_type_ids()

    # ==================== SEED SAMPLE DATA ====================

    def seed_sample_data(self):
        """Seed sample data from numbered JSON files"""
        log_header("Seeding Sample Data")

        sample_data_dir = SEEDS_DIR / "sample-data"
        if not sample_data_dir.exists():
            log_warning("No sample-data directory found")
            return

        # First, get content type IDs if not already cached
        if not self.created_content_types and not self.dry_run:
            self._fetch_content_type_ids()

        # Track all created entries by slug for reference resolution
        self.created_entries: Dict[str, str] = {}  # slug -> id

        # Load all JSON files in sorted order (numbered files like 01-site-settings.json)
        sample_files = sorted(sample_data_dir.glob("*.json"))

        if not sample_files:
            log_warning("No sample data files found")
            return

        for sample_file in sample_files:
            log_info(f"Processing: {sample_file.name}")
            data = self._load_json(sample_file)

            # Handle both array format and {"entries": [...]} format
            if isinstance(data, list):
                entries = data
                shared_content_type = None
            else:
                entries = data.get("entries", [])
                # Support top-level content_type that applies to all entries
                shared_content_type = data.get("content_type")

            if not entries:
                log_warning(f"No entries found in {sample_file.name}")
                continue

            for entry in entries:
                self._create_content_entry(entry, shared_content_type=shared_content_type)

    def _fetch_content_type_ids(self):
        """Fetch existing content type IDs"""
        result = self._api_get("content/types")
        if result:
            # Handle both list and paginated response formats
            items = result if isinstance(result, list) else result.get("items", [])
            for ct in items:
                # Use api_id as the key (this is the unique identifier)
                api_id = ct.get("api_id") or ct.get("slug")  # fallback for compatibility
                self.created_content_types[api_id] = ct["id"]

    def _create_content_entry(self, entry: Dict, shared_content_type: Optional[str] = None):
        """Create a single content entry"""
        # Support per-entry content_type_api_id or shared content_type from parent
        content_type_api_id = entry.get("content_type_api_id") or shared_content_type
        content_type_id = self.created_content_types.get(content_type_api_id)

        if not content_type_id and not self.dry_run:
            log_error(
                f"Content type '{content_type_api_id}' not found. Run --only content-types first."
            )
            return

        slug = entry.get("slug")
        status = entry.get("status", "published")
        # Support "data", "content_data", and "fields" field names
        data = entry.get("content_data") or entry.get("data") or entry.get("fields", {})

        # Handle reference placeholders (e.g., _brand_slug, _category_slug)
        # These will be resolved to actual IDs after the referenced entries exist
        brand_slug = entry.pop("_brand_slug", None)
        category_slug = entry.pop("_category_slug", None)
        product_slugs = entry.pop("_product_slugs", None)
        parent_slug = entry.pop("_parent_slug", None)

        # Resolve references if they exist
        if brand_slug and brand_slug in self.created_entries:
            data["brand_id"] = self.created_entries[brand_slug]
        if category_slug and category_slug in self.created_entries:
            data["category_id"] = self.created_entries[category_slug]
        if parent_slug and parent_slug in self.created_entries:
            data["parent_id"] = self.created_entries[parent_slug]
        if product_slugs:
            resolved_ids = [
                self.created_entries[ps] for ps in product_slugs if ps in self.created_entries
            ]
            if resolved_ids:
                data["product_ids"] = resolved_ids

        # Build payload matching ContentEntryCreate schema
        payload = {
            "content_type_id": content_type_id,
            "slug": slug,
            "status": status,
            "data": data,
        }

        # Add SEO fields if present
        if entry.get("seo_title"):
            payload["seo_title"] = entry["seo_title"]
        if entry.get("seo_description"):
            payload["seo_description"] = entry["seo_description"]
        if entry.get("seo_keywords"):
            payload["seo_keywords"] = entry["seo_keywords"]
        if entry.get("og_image"):
            payload["og_image"] = entry["og_image"]

        result = self._api_post(
            "content/entries", payload, description=f"{content_type_api_id}: {slug}"
        )
        if result:
            entry_id = result.get("id")
            # Track entries even if they already existed (for reference resolution)
            if slug:
                if result.get("_already_exists"):
                    # Fetch the existing entry ID for reference resolution
                    existing = self._api_get(
                        f"content/entries?slug={slug}&content_type_slug={content_type_api_id}"
                    )
                    if existing and existing.get("items"):
                        entry_id = existing["items"][0].get("id")
                self.created_entries[slug] = entry_id

            # Get a display name from data
            display_name = data.get("name") or data.get("question") or data.get("site_name") or slug
            if not result.get("_already_exists"):
                log_success(f"Created {content_type_api_id}: {display_name}")

    # ==================== MAIN ENTRY POINTS ====================

    def run_all(self):
        """Run all seeds in order"""
        if not self.authenticate():
            return False

        self.seed_themes()
        self.seed_locales()
        self.seed_content_types()
        self.seed_sample_data()

        log_header("Seeding Complete!")
        return True

    def run_only(self, component: str):
        """Run only a specific seed component"""
        if not self.authenticate():
            return False

        if component == "themes":
            self.seed_themes()
        elif component == "locales":
            self.seed_locales()
        elif component == "content-types":
            self.seed_content_types()
        elif component == "sample-data":
            self.seed_sample_data()
        else:
            log_error(f"Unknown component: {component}")
            return False

        log_header(f"Seeding {component} Complete!")
        return True

    def run_file(self, filename: str):
        """Run seed for a specific file from sample-data"""
        if not self.authenticate():
            return False

        sample_data_dir = SEEDS_DIR / "sample-data"

        # Try to find the file (with or without path)
        if "/" in filename or "\\" in filename:
            sample_file = Path(filename)
        else:
            sample_file = sample_data_dir / filename

        if not sample_file.exists():
            # Try glob pattern match
            matches = list(sample_data_dir.glob(f"*{filename}*"))
            if matches:
                sample_file = matches[0]
            else:
                log_error(f"File not found: {filename}")
                log_info("Available files in sample-data:")
                for f in sorted(sample_data_dir.glob("*.json")):
                    log_info(f"  - {f.name}")
                return False

        log_header(f"Seeding File: {sample_file.name}")

        # Get content type IDs
        if not self.created_content_types and not self.dry_run:
            self._fetch_content_type_ids()

        # Track entries for reference resolution
        self.created_entries: Dict[str, str] = {}

        log_info(f"Processing: {sample_file.name}")
        data = self._load_json(sample_file)

        # Handle both array format and {"entries": [...]} format
        if isinstance(data, list):
            entries = data
            shared_content_type = None
        else:
            entries = data.get("entries", [])
            # Support top-level content_type that applies to all entries
            shared_content_type = data.get("content_type")

        if not entries:
            log_warning(f"No entries found in {sample_file.name}")
            return True

        for entry in entries:
            self._create_content_entry(entry, shared_content_type=shared_content_type)

        log_header(f"Seeding {sample_file.name} Complete!")
        return True


def main():
    parser = argparse.ArgumentParser(description="Bakalr CMS Seed Runner")
    parser.add_argument(
        "--api-url",
        default=os.getenv("SEED_API_URL", DEFAULT_API_URL),
        help="API base URL",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("SEED_ADMIN_EMAIL"),
        help="Admin email for authentication",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SEED_ADMIN_PASSWORD"),
        help="Admin password for authentication",
    )
    parser.add_argument(
        "--only",
        choices=["themes", "locales", "content-types", "sample-data"],
        help="Only seed a specific component",
    )
    parser.add_argument(
        "--file",
        help="Only seed a specific file from sample-data (e.g., 02-navigation.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing content entries and content types before seeding",
    )
    parser.add_argument(
        "--reset-type",
        metavar="FILE",
        help="Reset a specific content type and its data (e.g., 01-page.json)",
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Show current database inventory and exit",
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help="Skip showing inventory before seeding",
    )

    args = parser.parse_args()

    # Get email and password from args (which fall back to env vars)
    email = args.email
    password = args.password
    
    # Only prompt interactively if not in dry-run mode and values not provided
    if not args.dry_run:
        if not email:
            try:
                email = input("Admin email: ").strip()
                if not email:
                    log_error("Email is required")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                log_error("\nEmail is required. Use --email or SEED_ADMIN_EMAIL env var")
                sys.exit(1)
        
        if not password:
            try:
                password = getpass.getpass("Admin password: ")
                if not password:
                    log_error("Password is required")
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                log_error("\nPassword is required. Use --password or SEED_ADMIN_PASSWORD env var")
                sys.exit(1)

    runner = SeedRunner(
        api_url=args.api_url,
        email=email,
        password=password,
        dry_run=args.dry_run,
    )

    # If --inventory flag, just show inventory and exit
    if args.inventory:
        runner.show_inventory()
        sys.exit(0)

    # Show inventory before any operation (unless --no-inventory)
    if not args.no_inventory and not args.dry_run:
        runner.show_inventory()
        try:
            proceed = input("Proceed with seeding? [Y/n]: ").strip().lower()
            if proceed and proceed not in ('y', 'yes'):
                log_info("Aborted by user")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print()
            log_info("Aborted by user")
            sys.exit(0)

    if args.reset:
        log_info("Running reset to clear existing data...")
        if not runner.reset_all():
            log_error("Reset failed!")
            sys.exit(1)
        log_success("Data cleared. Proceeding with seeding...")

    if args.reset_type:
        if not runner.reset_content_type(args.reset_type):
            log_error("Reset content type failed!")
            sys.exit(1)
        # After reset, re-seed just that content type and its sample data
        runner.seed_content_type_file(args.reset_type)
        sys.exit(0)

    if args.file:
        success = runner.run_file(args.file)
    elif args.only:
        success = runner.run_only(args.only)
    else:
        success = runner.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
