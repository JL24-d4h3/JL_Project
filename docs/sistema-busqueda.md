# Sistema de Búsqueda de Archivos

## Concepto General

El sistema de búsqueda **NO funciona a nivel de carpetas del filesystem** sino a nivel de **base de datos**.

Los archivos físicos se organizan en carpetas por tipo (videos/, images/, audio/, code/, documents/) pero la búsqueda y navegación se realiza completamente a través de metadatos en PostgreSQL.

## Estructura de Almacenamiento vs Búsqueda

### Estructura Física (Storage)

```
storage/
├── videos/          # Archivos .mp4, .webm, .mkv, etc.
├── audio/           # Archivos .mp3, .wav, .flac, etc.
├── images/          # Archivos .jpg, .png, .gif, etc.
├── code/            # Archivos .py, .js, .java, etc.
├── documents/       # Archivos .pdf, .docx, .xlsx, etc.
├── thumbnails/      # Miniaturas generadas
├── temp/            # Uploads temporales (pending)
└── archived/        # Archivos archivados (soft delete)
```

**Los nombres de archivo son hashes SHA-256**, NO reflejan el contenido:
- ❌ `storage/videos/Transformada_de_Fourier.mp4`
- ✅ `storage/videos/a3f8b9c2...d4e5f6.mp4`

### Estructura Lógica (Base de Datos)

La tabla `content` tiene estos campos principales:

```sql
- id              UUID (identificador único)
- title           VARCHAR (ej: "Transformada de Fourier")
- description     TEXT (descripción detallada)
- type            VARCHAR (video | audio | image | code | document | pdf)
- category_id     UUID → referencia a tabla categories
- tags            TEXT[] (array de etiquetas)
- file_path       VARCHAR (ruta relativa: "videos/a3f8b9c2...mp4")
- created_at      TIMESTAMP
- status          VARCHAR (pending | active | rejected)
```

## Cómo Busca un Usuario

### Ejemplo: "Transformada de Fourier"

#### ❌ Incorrecto (No se hace así)

```
1. Navegar a storage/
2. Entrar a Matemáticas y Ciencias Exactas/
3. Entrar a Cálculo/
4. Buscar "Transformada de Fourier.mp4"
```

#### ✅ Correcto (Así funciona)

```
1. Usuario escribe "Transformada de Fourier" en buscador
2. Sistema consulta BD con full-text search
3. Retorna todos los items donde:
   - title contenga "Transformada" o "Fourier"
   - description contenga esas palabras
   - tags contengan esas palabras
4. Usuario puede filtrar opcionalmente por:
   - Categoría: "Matemáticas y Ciencias Exactas"
   - Tipo: "video"
   - Destacados
   - Ordenamiento: reciente, popular, mejor calificado
```

## API de Búsqueda

### Endpoint Principal

```
GET /api/content
```

### Parámetros de Query

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `search` | string | Búsqueda de texto completo | `?search=fourier` |
| `category` | UUID | ID de categoría | `?category=550e8400-...` |
| `type` | string | Tipo de contenido | `?type=video` |
| `featured` | boolean | Solo destacados | `?featured=true` |
| `sort` | string | Ordenamiento | `?sort=popular` |
| `page` | number | Página (paginación) | `?page=2` |
| `limit` | number | Items por página | `?limit=20` |

### Tipos de Búsqueda

#### 1. Búsqueda de Texto Completo (Full-Text Search)

```http
GET /api/content?search=transformada fourier
```

Busca en:
- Título
- Descripción
- Tags (si aplica)

Usa PostgreSQL `to_tsvector` con configuración en **español** para:
- Stemming (transformación → transforma)
- Eliminar palabras vacías (el, la, de, etc.)

También hace búsqueda parcial con `ILIKE` para coincidencias exactas.

#### 2. Filtros Combinados

```http
GET /api/content?category=550e8400-...&type=video&search=fourier
```

Busca videos en la categoría "Matemáticas" que contengan "fourier".

#### 3. Ordenamiento

**Por reciente** (default):
```http
GET /api/content?sort=recent
```

**Por popularidad** (más vistos):
```http
GET /api/content?sort=popular
```

**Por calificación**:
```http
GET /api/content?sort=rating
```

### Ejemplo Completo

**Búsqueda**: "Videos de cálculo sobre transformada de fourier, ordenados por popularidad"

```http
GET /api/content?search=transformada%20fourier
  &category=550e8400-e29b-41d4-a716-446655440000
  &type=video
  &sort=popular
  &page=1
  &limit=20
```

## Flujo de Búsqueda en Frontend

### 1. Usuario en Buscador/Dashboard

```
┌─────────────────────────────┐
│ 🔍 Buscar contenido...      │
│   [Transformada de Fourier] │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Envía request al backend:   │
│ GET /api/content            │
│   ?search=transformada...   │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Backend consulta PostgreSQL:│
│ SELECT * FROM content       │
│ WHERE to_tsvector(...)      │
│   @@ plainto_tsquery(...)   │
│ AND status = 'active'       │
│ ORDER BY access_count DESC  │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Retorna array de resultados:│
│ [{                          │
│   id: "...",                │
│   title: "Transformada...", │
│   file_path: "videos/...",  │
│   thumbnail_path: "...",    │
│   category_name: "Cálculo"  │
│ }]                          │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Frontend renderiza cards    │
│ con thumbnails y metadata   │
└─────────────────────────────┘
```

### 2. Usuario Click en Resultado

```
┌─────────────────────────────┐
│ Usuario hace click en video │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Frontend solicita streaming:│
│ GET /api/stream/:id         │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Backend busca file_path:    │
│ SELECT file_path FROM ...   │
│ WHERE id = :id              │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Sirve archivo desde disco:  │
│ storage/videos/a3f8b9c2...  │
│ con HTTP Range support      │
└─────────────────────────────┘
```

## Categorías y Organización

Las categorías **NO son carpetas físicas**, son registros en la tabla `categories`:

```sql
CREATE TABLE categories (
  id UUID PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT,
  parent_id UUID REFERENCES categories(id),
  slug VARCHAR(250) UNIQUE NOT NULL
);
```

Ejemplos de categorías:

```
- Matemáticas y Ciencias Exactas
  ├── Cálculo
  ├── Álgebra
  └── Geometría
- Ciencias Naturales
  ├── Física
  ├── Química
  └── Biología
- Programación
  ├── Python
  ├── JavaScript
  └── Bases de Datos
```

### Navegación por Categoría

**Listar contenido de una categoría**:
```http
GET /api/content?category=<category_id>
```

**Listar subcategorías**:
```http
GET /api/categories/:id/children
```

## Índices de Búsqueda

Para optimizar las búsquedas, PostgreSQL tiene estos índices:

```sql
-- Índice de full-text search
CREATE INDEX idx_content_search
ON content
USING GIN(to_tsvector('spanish', title || ' ' || COALESCE(description, '')));

-- Índice por categoría
CREATE INDEX idx_content_category ON content(category_id);

-- Índice por tipo
CREATE INDEX idx_content_type ON content(type);

-- Índice por estado
CREATE INDEX idx_content_status ON content(status);

-- Índice por tags (si aplica)
CREATE INDEX idx_content_tags ON content USING GIN(tags);
```

## Caché de Búsquedas

Las búsquedas se cachean en Redis con TTL de 1 hora:

```
Cache Key: content:list:{query_params_hash}
TTL: 3600 segundos
```

Ejemplo:
```
content:list:{"search":"fourier","type":"video","page":1}
```

El caché se invalida cuando:
- Se aprueba nuevo contenido
- Se edita contenido existente
- Se elimina contenido

## Comparación: Filesystem vs Base de Datos

| Aspecto | Filesystem | Base de Datos (Usado) |
|---------|------------|----------------------|
| Búsqueda | `find`, `grep` lento | Índices PostgreSQL rápido |
| Metadata | Nombres de archivo | Campos estructurados |
| Filtros | Imposible/complejo | SQL queries flexibles |
| Ordenamiento | Por fecha de archivo | Por popularidad, rating, etc. |
| Full-text | No nativo | `to_tsvector` optimizado |
| Categorías | Carpetas anidadas | Relaciones en BD |
| Escalabilidad | Limitada | Alta (millones de registros) |
| Caché | Caché de FS del SO | Redis dedicado |

## Preguntas Frecuentes

### ¿Por qué los archivos se nombran con hashes?

1. **Unicidad**: El hash SHA-256 del contenido garantiza que no haya duplicados
2. **Seguridad**: No se expone información sensible en nombres de archivo
3. **Integridad**: Se puede verificar que el archivo no se corrompió

### ¿Cómo se relacionan las categorías con las carpetas?

**No se relacionan**. Las categorías son completamente independientes de la estructura de carpetas:

- Carpetas: organizan por **tipo** (video, audio, etc.)
- Categorías: organizan por **tema** (matemáticas, física, etc.)

### Si borro un archivo del disco, ¿desaparece de las búsquedas?

No de inmediato. El registro en la BD sigue existiendo. Cuando un usuario intente acceder, el sistema detectará que el archivo no existe y:
1. Registrará el error
2. Marcará el contenido como inválido
3. Puede auto-reparar si hay backups

Lo correcto es usar el endpoint de eliminación que actualiza BD y filesystem.

### ¿Puedo buscar por extensión de archivo?

No directamente, pero puedes filtrar por `type`:
```http
GET /api/content?type=video  # Incluye .mp4, .webm, .mkv, etc.
GET /api/content?type=audio  # Incluye .mp3, .wav, .flac, etc.
```

---

**Última actualización**: 2026-03-13
