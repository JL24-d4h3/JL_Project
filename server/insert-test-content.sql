-- ================================================
-- INSERTAR CONTENIDO DE PRUEBA
-- ================================================

-- Opción 1: Con un video existente (necesitas tener el archivo)
INSERT INTO content (
  title, 
  description, 
  type, 
  category_id, 
  created_by,
  file_path, 
  file_size, 
  file_hash, 
  mime_type,
  duration_seconds,
  resolution,
  status,
  is_featured
) VALUES (
  'Introducción a las Matemáticas',
  'Video tutorial básico de matemáticas para estudiantes',
  'video',
  'a000a592-4350-4d1f-96b7-99aa45cc1039', -- Matemáticas
  '676f6d7c-38fc-4105-838f-ea59cb606b19', -- admin
  'videos/matematicas-intro.mp4',
  15728640, -- 15 MB aproximadamente
  'abc123def456hash789',
  'video/mp4',
  300, -- 5 minutos
  '1280x720',
  'active',
  true
);

-- Opción 2: Contenido de texto/PDF
INSERT INTO content (
  title, 
  description, 
  type, 
  category_id, 
  created_by,
  file_path, 
  file_size, 
  file_hash, 
  mime_type,
  status,
  is_featured
) VALUES (
  'Guía de Estudio de Ciencias',
  'Material de apoyo para el curso de ciencias naturales',
  'pdf',
  '37a47e87-1237-4dcd-b462-7f99baf33ddb', -- Ciencias
  '676f6d7c-38fc-4105-838f-ea59cb606b19', -- admin
  'documents/ciencias-guia.pdf',
  2097152, -- 2 MB
  'xyz789abc123hash456',
  'application/pdf',
  'active',
  true
);

-- Opción 3: Video de ejemplo con metadatos completos
INSERT INTO content (
  title, 
  description, 
  type, 
  category_id, 
  created_by,
  file_path, 
  file_size, 
  file_hash, 
  mime_type,
  duration_seconds,
  resolution,
  bitrate,
  thumbnail_path,
  status,
  is_featured,
  priority
) VALUES (
  'Historia del Perú - Época Colonial',
  'Documental educativo sobre la época colonial peruana con animaciones y recreaciones históricas',
  'video',
  'bb47ba58-38cc-4df7-ab89-c80e81394516', -- Historia
  '676f6d7c-38fc-4105-838f-ea59cb606b19', -- admin
  'videos/historia-peru-colonial.mp4',
  52428800, -- 50 MB
  'historia123colonial456hash',
  'video/mp4',
  1200, -- 20 minutos
  '1920x1080',
  2500000, -- 2.5 Mbps
  'thumbnails/historia-peru-colonial.jpg',
  'active',
  true,
  8
);

-- Verificar qué se insertó
SELECT 
  id,
  title,
  type,
  file_size / 1024 / 1024 AS size_mb,
  duration_seconds / 60 AS duration_min,
  status,
  is_featured,
  created_at
FROM content
ORDER BY created_at DESC
LIMIT 5;
