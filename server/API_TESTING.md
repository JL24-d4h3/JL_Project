# ================================================
# API TESTING GUIDE
# CDN Offline - Backend Endpoints
# ================================================

# Prerequisite: Server running on http://localhost:3000
# Run: cd server && npm run dev

# ================================================
# 1. HEALTH CHECK
# ================================================

curl http://localhost:3000/health

# Expected:
# {
#   "status": "healthy",
#   "services": {
#     "database": "connected",
#     "redis": "connected"
#   }
# }

# ================================================
# 2. CATEGORIES
# ================================================

# List all categories
curl http://localhost:3000/api/categories

# Get categories tree
curl http://localhost:3000/api/categories/tree

# Get category by ID (replace with actual UUID from DB)
curl http://localhost:3000/api/categories/{category_id}

# ================================================
# 3. CONTENT - List & Search
# ================================================

# List all content (paginated)
curl http://localhost:3000/api/content

# With pagination
curl "http://localhost:3000/api/content?page=1&limit=10"

# Filter by category
curl "http://localhost:3000/api/content?category={category_id}"

# Filter by type
curl "http://localhost:3000/api/content?type=video"

# Search
curl "http://localhost:3000/api/content?search=matematicas"

# Featured only
curl "http://localhost:3000/api/content?featured=true"

# Sort by popular
curl "http://localhost:3000/api/content?sort=popular"

# Get featured content
curl http://localhost:3000/api/content/featured

# Get content by ID
curl http://localhost:3000/api/content/{content_id}

# ================================================
# 4. AUTHENTICATION
# ================================================

# Login (default user: admin/admin123)
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# Save the token from response:
# export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Get current user
curl http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Logout
curl -X POST http://localhost:3000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# ================================================
# 5. VIDEO STREAMING
# ================================================

# Stream video (full)
curl http://localhost:3000/api/content/{content_id}/stream

# Stream with Range (first 1MB)
curl -H "Range: bytes=0-1048575" \
  http://localhost:3000/api/content/{content_id}/stream

# Get thumbnail
curl http://localhost:3000/api/content/{content_id}/thumbnail \
  --output thumbnail.jpg

# ================================================
# 6. TESTING WITH VIDEO PLAYER
# ================================================

# In browser, open:
# http://localhost:3000/api/content/{content_id}/stream

# Or use Video.js:
# <video controls>
#   <source src="http://localhost:3000/api/content/{content_id}/stream" type="video/mp4">
# </video>

# ================================================
# 7. ERROR HANDLING TESTS
# ================================================

# Invalid endpoint (404)
curl http://localhost:3000/api/invalid

# Invalid content ID (404)
curl http://localhost:3000/api/content/00000000-0000-0000-0000-000000000000

# Invalid login (401)
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "invalid", "password": "wrong"}'

# No token (401)
curl http://localhost:3000/api/auth/me

# ================================================
# 8. POSTMAN COLLECTION
# ================================================

# Import this JSON into Postman:
{
  "info": {
    "name": "CDN Offline API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health"
      }
    },
    {
      "name": "Login",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/auth/login",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\"username\": \"admin\", \"password\": \"admin123\"}"
        }
      }
    },
    {
      "name": "Get Categories",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/categories"
      }
    },
    {
      "name": "Get Content",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/content"
      }
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:3000"
    }
  ]
}

# ================================================
# 9. QUICK VERIFICATION SCRIPT
# ================================================

#!/bin/bash
# test-api.sh

BASE_URL="http://localhost:3000"

echo "Testing CDN Offline API..."

echo "\n1. Health Check"
curl -s $BASE_URL/health | jq

echo "\n2. Categories"
curl -s $BASE_URL/api/categories | jq '.count'

echo "\n3. Content"
curl -s $BASE_URL/api/content | jq '.pagination'

echo "\n4. Login"
TOKEN=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.data.token')

echo "Token: ${TOKEN:0:20}..."

echo "\n5. Get Me"
curl -s $BASE_URL/api/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data.username'

echo "\nAll tests completed!"
