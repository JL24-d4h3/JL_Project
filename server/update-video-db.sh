#!/bin/bash
# Script rápido para actualizar la base de datos con el video real

VIDEO_PATH="/home/jleon/2026/PUCP/GTR/CDN/storage/videos/test-video.mp4"
CONTENT_ID="9172b6a0-f838-4f56-9468-9ab7ebd56991"

# Obtener tamaño del archivo
FILE_SIZE=$(stat -c%s "$VIDEO_PATH")

# Obtener duración si ffprobe está disponible
if command -v ffprobe &> /dev/null; then
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_PATH" | cut -d. -f1)
else
    DURATION=300  # 5 minutos por defecto
fi

echo "Video encontrado:"
echo "  Ruta: $VIDEO_PATH"
echo "  Tamaño: $FILE_SIZE bytes ($(($FILE_SIZE / 1024 / 1024)) MB)"
echo "  Duración: $DURATION segundos ($(($DURATION / 60)) minutos)"
echo ""

# Actualizar en la base de datos
echo "Actualizando base de datos..."
psql -U cdn_user -h localhost -d cdn_db <<SQL
UPDATE content 
SET 
    file_path = 'videos/test-video.mp4',
    file_size = $FILE_SIZE,
    duration_seconds = $DURATION,
    file_hash = 'test-video-hash-$(date +%s)'
WHERE id = '$CONTENT_ID';

SELECT id, title, file_path, file_size, duration_seconds 
FROM content 
WHERE id = '$CONTENT_ID';
SQL

echo ""
echo "✅ Base de datos actualizada"
echo ""
echo "Ahora prueba el streaming:"
echo "  curl -I http://localhost:3000/api/content/$CONTENT_ID/stream"
echo ""
echo "O abre el reproductor:"
echo "  firefox /home/jleon/2026/PUCP/GTR/CDN/server/test-player.html"
