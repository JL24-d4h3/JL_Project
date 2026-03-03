#!/bin/bash
# ================================================
# Script para configurar el video de prueba
# ================================================

STORAGE_BASE="/home/jleon/2026/PUCP/GTR/CDN/storage"
VIDEO_DIR="$STORAGE_BASE/videos"
THUMB_DIR="$STORAGE_BASE/thumbnails"

echo "🎬 Configurando video de prueba..."
echo ""

# Crear directorios si no existen
mkdir -p "$VIDEO_DIR"
mkdir -p "$THUMB_DIR"

# Buscar test-video.mp4 en ubicaciones comunes
VIDEO_SOURCE=""
for path in \
    "/home/jleon/test-video.mp4" \
    "/home/jleon/Videos/test-video.mp4" \
    "/home/jleon/Downloads/test-video.mp4" \
    "/home/jleon/2026/test-video.mp4" \
    "/home/jleon/2026/PUCP/test-video.mp4" \
    "/home/jleon/2026/PUCP/GTR/test-video.mp4" \
    "/home/jleon/2026/PUCP/GTR/CDN/test-video.mp4"; do
    if [ -f "$path" ]; then
        VIDEO_SOURCE="$path"
        echo "✓ Video encontrado: $path"
        break
    fi
done

if [ -z "$VIDEO_SOURCE" ]; then
    echo "❌ No se encontró test-video.mp4"
    echo ""
    echo "Por favor, especifica la ruta manualmente:"
    echo "  bash setup-video.sh /ruta/a/tu/test-video.mp4"
    echo ""
    echo "O mueve tu video a:"
    echo "  $VIDEO_DIR/matematicas-intro.mp4"
    exit 1
fi

# Si se pasó un argumento, usarlo como fuente
if [ -n "$1" ]; then
    VIDEO_SOURCE="$1"
fi

# Copiar el video
TARGET="$VIDEO_DIR/matematicas-intro.mp4"
echo "📦 Copiando video a: $TARGET"
cp "$VIDEO_SOURCE" "$TARGET"

if [ ! -f "$TARGET" ]; then
    echo "❌ Error al copiar el video"
    exit 1
fi

echo "✓ Video copiado exitosamente"
echo ""

# Obtener información del video con ffprobe si está disponible
if command -v ffprobe &> /dev/null; then
    echo "📊 Información del video:"
    
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$TARGET" 2>/dev/null | cut -d. -f1)
    SIZE=$(stat -f%z "$TARGET" 2>/dev/null || stat -c%s "$TARGET" 2>/dev/null)
    
    echo "  Duración: $DURATION segundos ($(($DURATION / 60)) minutos)"
    echo "  Tamaño: $SIZE bytes ($(($SIZE / 1024 / 1024)) MB)"
    echo ""
    
    # Generar thumbnail
    THUMB_TARGET="$THUMB_DIR/matematicas-intro.jpg"
    if command -v ffmpeg &> /dev/null; then
        echo "🖼️  Generando thumbnail..."
        ffmpeg -i "$TARGET" -ss 00:00:02 -vframes 1 -vf "scale=640:-1" "$THUMB_TARGET" -y &>/dev/null
        
        if [ -f "$THUMB_TARGET" ]; then
            echo "✓ Thumbnail generado: $THUMB_TARGET"
            
            # Actualizar en la base de datos
            psql -U cdn_user -h localhost -d cdn_db <<SQL
UPDATE content 
SET thumbnail_path = 'thumbnails/matematicas-intro.jpg',
    file_size = $SIZE,
    duration_seconds = $DURATION
WHERE id = '9172b6a0-f838-4f56-9468-9ab7ebd56991';
SQL
            echo "✓ Base de datos actualizada"
        fi
    fi
fi

echo ""
echo "================================================"
echo "✅ Configuración completa"
echo "================================================"
echo ""
echo "Ahora prueba en el navegador:"
echo "  file:///home/jleon/2026/PUCP/GTR/CDN/server/test-player.html"
echo ""
echo "O con curl:"
echo "  curl -I http://localhost:3000/api/content/9172b6a0-f838-4f56-9468-9ab7ebd56991/stream"
echo ""
