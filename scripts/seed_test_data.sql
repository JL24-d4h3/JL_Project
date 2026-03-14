-- ─────────────────────────────────────────────────────────────────────────────
-- seed_test_data.sql — Contenido de prueba para CDN Offline
-- Seguro de re-ejecutar: trunca content y reinsertta.
-- Ejecutar: psql "postgresql://cdn_user:<your_password>@localhost:5432/cdn_dev" -f scripts/seed_test_data.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- Limpiar contenido anterior (no toca categories ni users)
TRUNCATE content CASCADE;

-- ── Contenido de prueba ───────────────────────────────────────────────────────
-- Usa los slugs de la jerarquía de categorías v2.
-- Archivos "active" tienen rutas permanentes (videos/, documents/, etc.).
-- Archivos "pending" tienen rutas temporales (temp/).
-- Archivos "rejected" conservan ruta temporal (ya no importa, son sólo registro).

INSERT INTO content (
  title, slug, description, type, category_id,
  file_path, file_size, file_hash, mime_type,
  duration_seconds, resolution, thumbnail_path,
  status, is_featured,
  created_by, updated_by, updated_at
)
SELECT
  t.title, t.slug, t.description, t.type::varchar,
  (SELECT id FROM categories WHERE slug = t.cat_slug LIMIT 1),
  t.file_path, t.file_size, t.file_hash, t.mime_type,
  t.duration_seconds, t.resolution, t.thumbnail_path,
  t.status, t.is_featured,
  (SELECT id FROM users WHERE username = 'docente1'),
  CASE t.status
    WHEN 'active' THEN (SELECT id FROM users WHERE username = 'admin')
    ELSE (SELECT id FROM users WHERE username = 'docente1')
  END,
  NOW() - (t.age_days || ' days')::interval
FROM (VALUES
  -- ── ACTIVE ──────────────────────────────────────────────────────────────

  ( 'Introducción a los Algoritmos de Búsqueda',
    'intro-algoritmos-busqueda',
    'Explicación visual de BFS y DFS con animaciones paso a paso. Ideal para Ciencias de la Computación.',
    'video', 'algoritmos-programacion',
    'videos/algo-busqueda-bfs-dfs.mp4', 142680064,
    'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    'video/mp4', 1245, '1920x1080',
    'thumbnails/a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2.jpg',
    'active', true, 5 ),

  ( 'Límites y Continuidad — Cálculo I',
    'limites-continuidad-calculo-i',
    'Apuntes completos sobre límites, continuidad y definición épsilon-delta. PDF de 48 páginas con ejercicios resueltos.',
    'document', 'calculo',
    'documents/limites-continuidad-apuntes.pdf', 3145728,
    'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3',
    'application/pdf', NULL, NULL, NULL,
    'active', false, 3 ),

  ( 'Leyes de Newton — Experimentos Caseros',
    'leyes-newton-experimentos-caseros',
    'Video demostrativo de las tres leyes de Newton reproducibles en casa con materiales simples.',
    'video', 'fisica',
    'videos/newton-experimentos-caseros.mp4', 89478485,
    'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
    'video/mp4', 854, '1280x720',
    'thumbnails/c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4.jpg',
    'active', true, 7 ),

  ( 'Historia del Perú Precolombino — Mapa Conceptual',
    'peru-precolombino-mapa-conceptual',
    'Imagen con mapa conceptual de las culturas precolombinas del Perú: Caral, Chavín, Paracas, Nazca, Tiwanaku, Wari, Chimú e Inca.',
    'image', 'historia-peru',
    'images/peru-precolombino-mapa.png', 2097152,
    'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5',
    'image/png', NULL, '3840x2160', NULL,
    'active', false, 10 ),

  ( 'English Pronunciation — Minimal Pairs Practice',
    'english-minimal-pairs-practice',
    'Audio pack con 30 pares mínimos del inglés para practicar pronunciación: ship/sheep, live/leave, etc.',
    'audio', 'ingles',
    'audio/english-minimal-pairs-pack.mp3', 18874368,
    'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6',
    'audio/mpeg', 2340, NULL, NULL,
    'active', false, 2 ),

  ( 'Tabla Periódica — Resumen Interactivo',
    'tabla-periodica-resumen-interactivo',
    'PDF imprimible con la tabla periódica completa, grupos, períodos y propiedades de cada elemento.',
    'document', 'quimica',
    'documents/tabla-periodica-completa.pdf', 4194304,
    'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1',
    'application/pdf', NULL, NULL, NULL,
    'active', false, 8 ),

  -- ── PENDING ─────────────────────────────────────────────────────────────

  ( 'Mitosis y Meiosis — Animación 3D',
    'mitosis-meiosis-animacion-3d',
    'Video animado en 3D de los procesos de mitosis y meiosis celular, con narración en español.',
    'video', 'biologia-celular-genetica',
    'temp/bio-mitosis-meiosis-3d.mp4', 210763776,
    'a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3',
    'video/mp4', 1560, '1920x1080',
    'thumbnails/a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3.jpg',
    'pending', false, 0 ),

  ( 'Hoja de Referencia — Distribuciones de Probabilidad',
    'hoja-referencia-distribuciones-probabilidad',
    'Cheat sheet en Excel con fórmulas y tablas para distribuciones normal, Poisson y binomial.',
    'document', 'estadistica-probabilidad',
    'temp/estadistica-distribuciones-cheatsheet.xlsx', 524288,
    'b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    NULL, NULL, NULL,
    'pending', false, 0 ),

  ( 'Implementación de Árbol AVL en Python',
    'implementacion-arbol-avl-python',
    'Código fuente completo de un árbol AVL balanceado en Python con inserción, eliminación y rotaciones.',
    'document', 'estructuras-datos',
    'temp/estructuras-avl-tree-python.zip', 102400,
    'c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5',
    'application/zip', NULL, NULL, NULL,
    'pending', false, 0 ),

  -- ── REJECTED ────────────────────────────────────────────────────────────

  ( 'Video sin descripción ni contexto educativo',
    'video-sin-descripcion-contexto',
    NULL,
    'video', 'fisica',
    'temp/rejected-video-borroso.mp4', 55050240,
    'd5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6',
    'video/mp4', 120, '640x360', NULL,
    'rejected', false, 1 )

) AS t(title, slug, description, type, cat_slug,
       file_path, file_size, file_hash, mime_type,
       duration_seconds, resolution, thumbnail_path,
       status, is_featured, age_days)
ON CONFLICT (file_hash) DO NOTHING;

-- Razón de rechazo
UPDATE content
SET rejected_reason = 'La calidad del video es muy baja (360p borroso) y no incluye descripción ni contexto educativo claro.'
WHERE file_hash = 'd5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6';

-- ── Verificación ──────────────────────────────────────────────────────────────
SELECT status, COUNT(*) AS filas FROM content GROUP BY status ORDER BY status;
