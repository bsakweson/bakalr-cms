#!/bin/bash

API_KEY="bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL="http://localhost:8000"
PROXY_URL="$BASE_URL/api/v1/media/proxy"

# Function to update product
update_product() {
  local product_id=$1
  local images=$2

  curl -s -X PATCH "$BASE_URL/api/v1/content/entries/$product_id" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"data\": {\"media_gallery\": $images}}" \
    -o /dev/null -w "%{http_code}"
}

echo "Updating product images..."

# Vietnamese Straight Bundle
echo -n "Vietnamese Straight: "
update_product "508a8c57-a1c5-4da6-a24a-e54c06158a5d" \
  "[{\"url\": \"$PROXY_URL/fe94d8b3-0a8d-435a-a008-3b9a3cc90fa7_vietnamese-straight-1.jpg\", \"alt\": \"Vietnamese Straight\"}, {\"url\": \"$PROXY_URL/14fd0047-a024-4fef-8b7c-2a994165d814_vietnamese-straight-2.jpg\", \"alt\": \"Vietnamese Straight Detail\"}]"
echo ""

# Cambodian Raw Wavy Bundle
echo -n "Cambodian Wavy: "
update_product "145c3774-8e8d-4085-adb7-5ce92ed3d6fd" \
  "[{\"url\": \"$PROXY_URL/e61b83aa-b3a9-4320-a69b-3bf7228c1273_cambodian-wavy-2.jpg\", \"alt\": \"Cambodian Raw Wavy\"}]"
echo ""

# HD Lace Closure 5x5 Straight
echo -n "HD Lace Closure 5x5 Straight: "
update_product "b5e3b3d6-3bf2-46f2-aa14-2292e6395db5" \
  "[{\"url\": \"$PROXY_URL/0cc41a4f-de31-4777-af96-18b2541c08d5_lace-closure-1.jpg\", \"alt\": \"HD Lace Closure 5x5\"}, {\"url\": \"$PROXY_URL/1dd22cf8-fb52-41e1-b6c6-edfea7413ed8_lace-closure-2.jpg\", \"alt\": \"HD Lace Closure Detail\"}]"
echo ""

# HD Lace Closure 4x4 Body Wave
echo -n "HD Lace Closure 4x4 Body Wave: "
update_product "36fa1e5f-d5df-46b7-b0f6-ff94e1a912cc" \
  "[{\"url\": \"$PROXY_URL/0cc41a4f-de31-4777-af96-18b2541c08d5_lace-closure-1.jpg\", \"alt\": \"HD Lace Closure 4x4\"}, {\"url\": \"$PROXY_URL/1dd22cf8-fb52-41e1-b6c6-edfea7413ed8_lace-closure-2.jpg\", \"alt\": \"HD Lace Closure Detail\"}]"
echo ""

# HD Lace Frontal 13x4 Body Wave
echo -n "HD Lace Frontal 13x4 Body Wave: "
update_product "d75e974f-bebc-463c-a74e-087d80ec0f26" \
  "[{\"url\": \"$PROXY_URL/0b0feab7-f5c5-4395-b4a0-605f8c5a067f_lace-frontal-1.jpg\", \"alt\": \"HD Lace Frontal 13x4\"}, {\"url\": \"$PROXY_URL/bf8709b1-b9a0-4c5d-8434-3ad6161df5b5_lace-frontal-2.jpg\", \"alt\": \"HD Lace Frontal Detail\"}]"
echo ""

# HD Lace Frontal 13x6 Deep Wave
echo -n "HD Lace Frontal 13x6 Deep Wave: "
update_product "31d5d647-700a-4edf-8f8a-622ff5516ac2" \
  "[{\"url\": \"$PROXY_URL/0b0feab7-f5c5-4395-b4a0-605f8c5a067f_lace-frontal-1.jpg\", \"alt\": \"HD Lace Frontal 13x6\"}, {\"url\": \"$PROXY_URL/bf8709b1-b9a0-4c5d-8434-3ad6161df5b5_lace-frontal-2.jpg\", \"alt\": \"HD Lace Frontal Detail\"}]"
echo ""

# Wig Grip Band Velvet
echo -n "Wig Grip Band Velvet: "
update_product "caf3fdc6-c9cf-495f-b93d-2915a52a390e" \
  "[{\"url\": \"$PROXY_URL/de24e34e-7f24-429d-b8d4-ada69a580c8d_wig-grip-band-1.jpg\", \"alt\": \"Velvet Wig Grip Band\"}]"
echo ""

echo "Done!"
