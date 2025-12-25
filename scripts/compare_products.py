#!/usr/bin/env python3
"""Compare products in seed files vs database"""
import getpass
import json
import os

import httpx

API_URL = os.getenv("SEED_API_URL", "http://localhost:8000/api/v1")


def main():
    # Get credentials
    email = os.getenv("SEED_ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.getenv("SEED_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    client = httpx.Client(timeout=30)

    # Authenticate
    login_resp = client.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
    if login_resp.status_code != 200:
        print(f"Authentication failed: {login_resp.json().get('detail', 'Unknown error')}")
        return
    token = login_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✓ Authenticated as {email}")
    print()

    # Get all content types to find product
    resp = client.get(f"{API_URL}/content/types", headers=headers)
    types = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])

    print("=== PRODUCT CONTENT TYPES ===")
    product_api_id = None
    for ct in types:
        name = ct.get("name", "").lower()
        api_id = ct.get("api_id", "").lower()
        if "product" in name or "product" in api_id:
            print(f"  Name: {ct.get('name')}")
            print(f"  API ID: {ct.get('api_id')}")
            print(f"  Entries: {ct.get('entry_count', 'N/A')}")
            print()
            if ct.get("api_id") == "product":
                product_api_id = ct.get("api_id")

    if not product_api_id:
        print("No 'product' content type found!")
        return

    # Get products from DB
    resp = client.get(
        f"{API_URL}/content/entries?content_type_slug={product_api_id}&page_size=100",
        headers=headers,
    )
    data = resp.json()
    db_items = data.get("items", [])
    db_slugs = set(item.get("slug") for item in db_items if item.get("slug"))

    # Load seed file
    with open("seeds/sample-data/11-products.json") as f:
        seed_products = json.load(f)
    seed_slugs = set(p.get("slug") for p in seed_products if p.get("slug"))

    print("=== PRODUCT COMPARISON ===")
    print()
    print(f"In seed file (11-products.json): {len(seed_slugs)}")
    print(f"In database:                     {len(db_slugs)}")
    print()

    missing_from_db = seed_slugs - db_slugs
    extra_in_db = db_slugs - seed_slugs

    if missing_from_db:
        print(f"Missing from DB ({len(missing_from_db)}):")
        for slug in sorted(missing_from_db):
            print(f"  - {slug}")
        print()

    if extra_in_db:
        print(f"Extra in DB - not in seed file ({len(extra_in_db)}):")
        for slug in sorted(extra_in_db):
            print(f"  - {slug}")

    if not missing_from_db and not extra_in_db:
        print("✓ Database and seed file are in sync!")


if __name__ == "__main__":
    main()
