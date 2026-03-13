-- ─────────────────────────────────────────────────────────────
-- Seed: Categorías jerárquicas para CDN Offline Escolar/Universitario
-- Estructura: 7 áreas temáticas → ~38 sub-materias
-- ─────────────────────────────────────────────────────────────

-- Limpiar todas las categorías existentes (las 5 básicas del seed anterior)
-- pero preservar referencias de content (se actualiza a NULL temporalmente)
UPDATE content SET category_id = NULL WHERE category_id IN (
  SELECT id FROM categories
);
TRUNCATE categories CASCADE;

-- ─── NIVEL 1: Áreas temáticas raíz ───────────────────────────

INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
VALUES
  ('Matemáticas y Ciencias Exactas', 'matematicas-exactas',
   'Álgebra, geometría, cálculo, física, química y estadística',
   NULL, '📐', '#3B82F6', 1, true),

  ('Ciencias Naturales', 'ciencias-naturales',
   'Biología, ecología, astronomía y geología',
   NULL, '🔬', '#22C55E', 2, true),

  ('Humanidades y Ciencias Sociales', 'humanidades-sociales',
   'Historia, geografía, filosofía, psicología y ciencias sociales',
   NULL, '📚', '#F59E0B', 3, true),

  ('Tecnología e Informática', 'tecnologia-informatica',
   'Programación, bases de datos, redes, robótica e IA',
   NULL, '💻', '#8B5CF6', 4, true),

  ('Idiomas y Comunicación', 'idiomas-comunicacion',
   'Español, inglés, francés, portugués y comunicación académica',
   NULL, '🌐', '#06B6D4', 5, true),

  ('Arte y Cultura', 'arte-cultura',
   'Literatura, música, artes visuales, teatro y danza',
   NULL, '🎨', '#EC4899', 6, true),

  ('Educación Física y Salud', 'educacion-fisica-salud',
   'Deportes, actividad física, nutrición y primeros auxilios',
   NULL, '⚽', '#EF4444', 7, true);


-- ─── NIVEL 2: Sub-materias ────────────────────────────────────

-- ── Matemáticas y Ciencias Exactas
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT
  sub.name, sub.slug, sub.description,
  cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Aritmética y Álgebra', 'aritmetica-algebra',
   'Operaciones, ecuaciones, funciones y expresiones algebraicas', 1),
  ('Geometría y Trigonometría', 'geometria-trigonometria',
   'Figuras, ángulos, áreas, volúmenes y razones trigonométricas', 2),
  ('Cálculo', 'calculo',
   'Límites, derivadas, integrales y ecuaciones diferenciales', 3),
  ('Estadística y Probabilidad', 'estadistica-probabilidad',
   'Datos, distribuciones, inferencia estadística y probabilidad', 4),
  ('Física', 'fisica',
   'Mecánica, termodinámica, electricidad, ondas y física moderna', 5),
  ('Química', 'quimica',
   'Átomos, reacciones, estequiometría, orgánica e inorgánica', 6)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'matematicas-exactas';


-- ── Ciencias Naturales
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Biología Celular y Genética', 'biologia-celular-genetica',
   'Célula, ADN, herencia, evolución y biotecnología', 1),
  ('Ecología y Medio Ambiente', 'ecologia-medio-ambiente',
   'Ecosistemas, biodiversidad, ciclos y cambio climático', 2),
  ('Anatomía y Fisiología', 'anatomia-fisiologia',
   'Sistemas del cuerpo humano y procesos biológicos', 3),
  ('Geología y Astronomía', 'geologia-astronomia',
   'Terra interior, minerales, sistema solar y cosmología', 4)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'ciencias-naturales';


-- ── Humanidades y Ciencias Sociales
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Historia Universal', 'historia-universal',
   'Prehistoria, edad antigua, media, moderna y contemporánea', 1),
  ('Historia del Perú', 'historia-peru',
   'Culturas preincaicas, Tahuantinsuyo, colonia, república', 2),
  ('Geografía', 'geografia',
   'Geografía física, humana, económica y del Perú', 3),
  ('Educación Ciudadana y Cívica', 'educacion-ciudadana',
   'Derechos, instituciones democráticas, constitución y ciudadanía', 4),
  ('Filosofía y Ética', 'filosofia-etica',
   'Lógica, epistemología, ética, valores y pensamiento crítico', 5),
  ('Psicología', 'psicologia',
   'Procesos mentales, aprendizaje, desarrollo y psicología social', 6),
  ('Sociología y Economía', 'sociologia-economia',
   'Sociedad, organización social, microeconomía y macroeconomía', 7)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'humanidades-sociales';


-- ── Tecnología e Informática
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Algoritmos y Programación', 'algoritmos-programacion',
   'Pseudocódigo, diagramas de flujo, Python, Java, C/C++, JS y más', 1),
  ('Estructuras de Datos', 'estructuras-datos',
   'Listas, pilas, colas, árboles, grafos y algoritmos de búsqueda/ordenamiento', 2),
  ('Base de Datos', 'base-de-datos',
   'SQL, modelado relacional, NoSQL y diseño de bases de datos', 3),
  ('Redes y Comunicaciones', 'redes-comunicaciones',
   'Protocolo TCP/IP, topologías, seguridad y arquitecturas de red', 4),
  ('Inteligencia Artificial y ML', 'inteligencia-artificial',
   'Machine learning, deep learning, NLP y aplicaciones de IA', 5),
  ('Electrónica y Robótica', 'electronica-robotica',
   'Circuitos, microcontroladores, Arduino, Raspberry Pi y automatización', 6),
  ('Sistemas Operativos', 'sistemas-operativos',
   'Linux, Windows, gestión de procesos, memoria y sistemas de archivos', 7)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'tecnologia-informatica';


-- ── Idiomas y Comunicación
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Comunicación y Literatura', 'comunicacion-literatura',
   'Comprensión lectora, producción de textos, oratoria y géneros literarios', 1),
  ('Inglés', 'ingles',
   'Gramática, vocabulario, listening, speaking y preparación para exámenes', 2),
  ('Francés', 'frances',
   'Niveles A1–B2: gramática, vocabulario y expresión oral', 3),
  ('Portugués', 'portugues',
   'Niveles básico–intermedio para hispanohablantes', 4),
  ('Redacción Académica', 'redaccion-academica',
   'APA, IEEE, ensayos, artículos científicos y tesis universitarias', 5)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'idiomas-comunicacion';


-- ── Arte y Cultura
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Literatura Clásica y Universal', 'literatura-clasica',
   'Narrativa, poesía, drama y análisis de obras literarias', 1),
  ('Música y Educación Musical', 'musica-educacion-musical',
   'Teoría musical, solfeo, instrumentos, géneros y apreciación musical', 2),
  ('Artes Visuales y Plástica', 'artes-visuales',
   'Dibujo, pintura, escultura, fotografía y diseño gráfico', 3),
  ('Historia del Arte', 'historia-del-arte',
   'Movimientos artísticos desde la antigüedad hasta el arte contemporáneo', 4),
  ('Teatro y Expresión Corporal', 'teatro-expresion-corporal',
   'Técnicas teatrales, danza, performance y expresión escénica', 5)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'arte-cultura';


-- ── Educación Física y Salud
INSERT INTO categories (name, slug, description, parent_id, icon, color, display_order, is_active)
SELECT sub.name, sub.slug, sub.description, cat.id, NULL, cat.color, sub.ord, true
FROM (VALUES
  ('Deportes y Actividad Física', 'deportes-actividad-fisica',
   'Fútbol, básquet, atletismo, natación y deportes escolares', 1),
  ('Primeros Auxilios y Seguridad', 'primeros-auxilios',
   'RCP, vendajes, emergencias, seguridad vial y prevención', 2),
  ('Nutrición y Bienestar', 'nutricion-bienestar',
   'Alimentación saludable, macronutrientes, salud mental y autocuidado', 3)
) AS sub(name, slug, description, ord)
CROSS JOIN categories cat
WHERE cat.slug = 'educacion-fisica-salud';
