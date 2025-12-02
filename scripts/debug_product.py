#!/usr/bin/env python3
import asyncio
import json

import httpx


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        login_resp = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "bsakweson@gmail.com", "password": "Angelbenise123!@#"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        types_resp = await client.get("http://localhost:8000/api/v1/content/types", headers=headers)
        product_type_id = next(
            ct["id"] for ct in types_resp.json() if ct.get("api_id") == "product"
        )

        products_resp = await client.get(
            f"http://localhost:8000/api/v1/content/entries?content_type_id={product_type_id}&page_size=1",
            headers=headers,
        )
        product = products_resp.json()["items"][0]

        print("Product structure:")
        print(json.dumps(product, indent=2))


asyncio.run(main())
