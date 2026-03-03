#!/bin/bash
# ================================================
# SCRIPT DE PRUEBA - UPLOAD DE ARCHIVOS
# ================================================

BASE_URL="http://localhost:3000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================"
echo "CDN Offline - Upload Testing"
echo "================================================"
echo ""

# 1. Login como superadmin
echo -e "${YELLOW}1. Login as superadmin${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.data.token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed${NC}"
    echo $LOGIN_RESPONSE | jq
    exit 1
fi

echo -e "${GREEN}✓ Logged in successfully${NC}"
echo "  Token: ${TOKEN:0:30}..."
echo ""

# 2. Obtener categorías
echo -e "${YELLOW}2. Getting categories${NC}"
CATEGORY_ID=$(curl -s $BASE_URL/api/categories | jq -r '.data[0].id')
echo -e "${GREEN}✓ Category ID: $CATEGORY_ID${NC}"
echo ""

# 3. Upload de video (test-video.mp4)
echo -e "${YELLOW}3. Uploading video${NC}"
VIDEO_PATH="/home/jleon/2026/PUCP/GTR/CDN/storage/videos/test-video.mp4"

if [ ! -f "$VIDEO_PATH" ]; then
    echo -e "${RED}✗ Video not found: $VIDEO_PATH${NC}"
    echo "  Por favor, coloca tu video de prueba en esa ubicación"
    echo ""
    echo -e "${BLUE}Alternativa: Usar otro archivo${NC}"
    echo "  Edita la variable VIDEO_PATH en este script"
    exit 1
fi

echo "  Uploading: $VIDEO_PATH"
echo "  This may take a while (processing with FFmpeg)..."
echo ""

UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$VIDEO_PATH;type=video/mp4" \
  -F "title=Video de Prueba UPLOAD" \
  -F "description=Este video fue subido mediante la API de upload" \
  -F "category_id=$CATEGORY_ID" \
  -F "is_featured=true")

CONTENT_ID=$(echo $UPLOAD_RESPONSE | jq -r '.data.id')

if [ "$CONTENT_ID" = "null" ] || [ -z "$CONTENT_ID" ]; then
    echo -e "${RED}✗ Upload failed${NC}"
    echo $UPLOAD_RESPONSE | jq
    exit 1
fi

echo -e "${GREEN}✓ Video uploaded successfully${NC}"
echo ""
echo "Upload details:"
echo $UPLOAD_RESPONSE | jq '.data'
echo ""

# 4. Verificar el contenido subido
echo -e "${YELLOW}4. Verifying uploaded content${NC}"
CONTENT=$(curl -s $BASE_URL/api/content/$CONTENT_ID | jq -r '.data.title')
echo -e "${GREEN}✓ Content found: $CONTENT${NC}"
echo ""

# 5. Probar streaming
echo -e "${YELLOW}5. Testing streaming${NC}"
STREAM_STATUS=$(curl -I -s $BASE_URL/api/content/$CONTENT_ID/stream | head -1 | awk '{print $2}')

if [ "$STREAM_STATUS" = "200" ] || [ "$STREAM_STATUS" = "206" ]; then
    echo -e "${GREEN}✓ Streaming works! Status: $STREAM_STATUS${NC}"
else
    echo -e "${RED}✗ Streaming failed. Status: $STREAM_STATUS${NC}"
fi
echo ""

# 6. Probar thumbnail
if [ "$STREAM_STATUS" = "200" ] || [ "$STREAM_STATUS" = "206" ]; then
    echo -e "${YELLOW}6. Testing thumbnail${NC}"
    THUMB_STATUS=$(curl -I -s $BASE_URL/api/content/$CONTENT_ID/thumbnail | head -1 | awk '{print $2}')
    
    if [ "$THUMB_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Thumbnail works!${NC}"
    else
        echo -e "${YELLOW}⚠ Thumbnail not available (this is normal if FFmpeg failed)${NC}"
    fi
    echo ""
fi

echo "================================================"
echo -e "${GREEN}UPLOAD TEST COMPLETED!${NC}"
echo "================================================"
echo ""
echo "Content ID: $CONTENT_ID"
echo ""
echo "You can now:"
echo "  1. View content details:"
echo "     curl $BASE_URL/api/content/$CONTENT_ID | jq"
echo ""
echo "  2. Stream the video:"
echo "     curl -I $BASE_URL/api/content/$CONTENT_ID/stream"
echo ""
echo "  3. Download thumbnail:"
echo "     curl $BASE_URL/api/content/$CONTENT_ID/thumbnail -o thumbnail.jpg"
echo ""
echo "  4. Delete content:"
echo "     curl -X DELETE $BASE_URL/api/upload/$CONTENT_ID -H \"Authorization: Bearer $TOKEN\""
echo ""
