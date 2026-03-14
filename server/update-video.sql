-- Actualizar contenido para apuntar al video real
UPDATE content 
SET 
    file_path = 'videos/test-video.mp4',
    file_size = 5242880,  -- Ajustar después según el tamaño real
    duration_seconds = 60,  -- Ajustar después
    file_hash = 'test-video-hash-updated'
WHERE id = '9172b6a0-f838-4f56-9468-9ab7ebd56991';

-- Verificar
SELECT 
    id, 
    title, 
    file_path, 
    file_size / 1024 / 1024 AS size_mb,
    duration_seconds,
    status
FROM content 
WHERE id = '9172b6a0-f838-4f56-9468-9ab7ebd56991';
