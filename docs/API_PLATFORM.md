# API del Servidor & Plan de Plataforma Educativa

> Última actualización: 5 de marzo de 2026  
> Versión del servidor: `0.1.0` · Puerto por defecto: `3000`  
> Stack: Express 5 · TypeScript · PostgreSQL · Redis · Multer · FFmpeg

---

## Índice

1. [Resumen de la API](#1-resumen-de-la-api)
2. [Autenticación](#2-autenticación)
3. [Endpoints de Autenticación](#3-endpoints-de-autenticación)
4. [Endpoints de Contenido](#4-endpoints-de-contenido)
5. [Endpoints de Streaming](#5-endpoints-de-streaming)
6. [Endpoints de Upload](#6-endpoints-de-upload)
7. [Endpoints de Categorías](#7-endpoints-de-categorías)
8. [Salud del servidor](#8-salud-del-servidor)
9. [Formato de errores](#9-formato-de-errores)
10. [Modelos de datos](#10-modelos-de-datos)
11. [Plan de la plataforma educativa (`/client`)](#11-plan-de-la-plataforma-educativa-client)

---

## 1. Resumen de la API

| Grupo        | Base path         | Auth requerida |
|--------------|-------------------|---------------|
| Auth         | `/api/auth`       | parcial       |
| Contenido    | `/api/content`    | no (lectura)  |
| Upload       | `/api/upload`     | sí            |
| Categorías   | `/api/categories` | no            |
| Health       | `/health`         | no            |

**Content-Type por defecto:** `application/json`  
**Autorización:** `Authorization: Bearer <jwt_token>`  
**Caché:** Redis. Listados se cachean 5 minutos con clave basada en query params.

---

## 2. Autenticación

El servidor usa **JWT** con sesiones registradas en PostgreSQL.

- Token válido: **7 días**
- Tras **5 intentos fallidos** → cuenta bloqueada 15 minutos
- En cada request autenticado, `last_activity` de la sesión se actualiza

### Flujo

```
[Cliente] → POST /api/auth/login  →  JWT + UserDTO
[Cliente] → GET  /api/auth/me     →  perfil del usuario
[Cliente] → POST /api/auth/logout →  invalidar sesión en DB
```

### Roles disponibles

| Rol          | Descripción                              |
|--------------|------------------------------------------|
| `student`    | Solo lectura y reproducción              |
| `teacher`    | Puede crear contenido (pendiente enable) |
| `admin`      | Gestión general                          |
| `superadmin` | Upload, borrado, gestión total           |

---

## 3. Endpoints de Autenticación

### `POST /api/auth/login`

**Request body:**
```json
{
  "username": "jleon",
  "password": "mi_clave"
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGci...",
    "expires_in": 604800,
    "user": {
      "id": "uuid",
      "username": "jleon",
      "email": "jleon@pucp.pe",
      "full_name": "José León",
      "role": "superadmin",
      "is_active": true,
      "created_at": "2026-03-01T00:00:00.000Z"
    }
  }
}
```

**Errores:**
| Código | Motivo |
|--------|--------|
| `400`  | Falta `username` o `password` |
| `401`  | Credenciales incorrectas |
| `423`  | Cuenta bloqueada (devuelve minutos restantes) |

---

### `GET /api/auth/me`

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "username": "jleon",
    "email": "jleon@pucp.pe",
    "full_name": "José León",
    "role": "superadmin",
    "is_active": true,
    "created_at": "2026-03-01T00:00:00.000Z"
  }
}
```

---

### `POST /api/auth/logout`

**Headers:** `Authorization: Bearer <token>`

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 4. Endpoints de Contenido

### `GET /api/content`

Lista contenido con filtros opcionales y paginación.

**Query params:**

| Param      | Tipo    | Default  | Descripción                                      |
|------------|---------|----------|--------------------------------------------------|
| `page`     | number  | `1`      | Página actual                                    |
| `limit`    | number  | `20`     | Resultados por página (máx razonable: 100)       |
| `category` | uuid    | —        | Filtrar por `category_id`                        |
| `type`     | string  | —        | `video`, `pdf`, `audio`, `image`, `document`     |
| `search`   | string  | —        | Búsqueda full-text en español (PostgreSQL tsvector) + ILIKE |
| `featured` | boolean | —        | `true` para solo destacados                      |
| `sort`     | string  | `recent` | `recent` · `popular` (access_count) · `rating`  |

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Introducción a Redes",
      "description": "...",
      "type": "video",
      "thumbnail_path": "thumbnails/abc123.jpg",
      "duration_seconds": 3600,
      "file_size": 524288000,
      "access_count": 142,
      "average_rating": 4.5,
      "is_featured": true,
      "created_at": "2026-02-10T08:00:00.000Z",
      "category_name": "Redes"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 87,
    "total_pages": 5
  },
  "cached": true
}
```

> `cached: true` aparece solo cuando la respuesta viene de Redis.

---

### `GET /api/content/featured`

Devuelve contenido marcado como `is_featured = true`. Misma estructura de respuesta que la lista.

---

### `GET /api/content/:id`

Detalle completo de un ítem, incluyendo tags y datos del creador.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Introducción a Redes",
    "slug": "introduccion-a-redes",
    "description": "...",
    "type": "video",
    "category_id": "uuid",
    "category_name": "Redes",
    "category_slug": "redes",
    "file_path": "videos/abc123.mp4",
    "file_size": 524288000,
    "file_hash": "sha256hex",
    "mime_type": "video/mp4",
    "duration_seconds": 3600,
    "resolution": "1920x1080",
    "bitrate": 2500000,
    "thumbnail_path": "thumbnails/abc123.jpg",
    "metadata": { "codec": "h264", "fps": 30, "hasAudio": true },
    "access_count": 142,
    "average_rating": 4.5,
    "rating_count": 22,
    "is_featured": true,
    "status": "active",
    "created_by_name": "José León",
    "created_at": "2026-02-10T08:00:00.000Z",
    "tags": [
      { "id": "uuid", "name": "C++", "slug": "cpp" }
    ]
  }
}
```

**Errores:** `404` si no existe o fue eliminado.

---

## 5. Endpoints de Streaming

### `GET /api/content/:id/stream`

Streaming de video/audio con soporte de **HTTP Range requests** (reproducción parcial, seek).

**Headers soportados:**
- `Range: bytes=0-` → responde `206 Partial Content`
- Sin `Range` → responde `200 OK` con el archivo completo

**Response headers (206):**
```
Content-Range: bytes 0-999999/524288000
Accept-Ranges: bytes
Content-Length: 1000000
Content-Type: video/mp4
Cache-Control: public, max-age=31536000
ETag: "sha256hex"
```

**Notas:**
- Solo funciona con `type = 'video'` o `'audio'`; rechaza PDFs/imágenes con `400`
- El acceso queda registrado en `access_log` (asíncrono, no bloquea la respuesta)
- `416 Range Not Satisfiable` si el rango excede el tamaño del archivo

---

### `GET /api/content/:id/thumbnail`

Devuelve la imagen thumbnail generada por FFmpeg.

**Response:** binario `image/jpeg` (o el mime almacenado).  
**Errores:** `404` si no hay thumbnail.

---

## 6. Endpoints de Upload

> Todos requieren `Authorization: Bearer <token>` con rol `superadmin`.

### `POST /api/upload`

Upload de un archivo multimedia o documento.

**Content-Type:** `multipart/form-data`

**Campos del form:**

| Campo        | Tipo   | Req | Descripción                         |
|--------------|--------|-----|-------------------------------------|
| `file`       | File   | ✅  | Archivo a subir                     |
| `title`      | string | ✅  | Título del contenido                |
| `category_id`| uuid   | ✅  | ID de categoría                     |
| `description`| string | ❌  | Descripción opcional                |
| `is_featured`| string | ❌  | `"true"` para destacar              |

**Procesamiento interno:**
1. Multer recibe el archivo en `storage/temp/`
2. Se calcula SHA-256 del archivo (deduplicación)
3. Si el hash ya existe → `409 Conflict`
4. Archivo se mueve a `storage/videos/`, `storage/documents/`, etc.
5. Para video/audio: FFmpeg extrae duración, resolución, bitrate
6. Para video: FFmpeg genera thumbnail en `storage/thumbnails/`
7. Se genera slug a partir del título
8. Registro insertado en PostgreSQL con `status = 'active'`

**Response `201 Created`:**
```json
{
  "success": true,
  "message": "Content uploaded successfully",
  "data": {
    "id": "uuid",
    "title": "Introducción a Redes",
    "slug": "introduccion-a-redes",
    "type": "video",
    "file_path": "videos/abc123.mp4",
    "file_size": 524288000,
    "status": "active",
    "created_at": "2026-03-05T10:00:00.000Z"
  }
}
```

**Errores:**
| Código | Motivo |
|--------|--------|
| `400`  | Sin archivo, sin título, sin `category_id` |
| `401`  | Sin token |
| `403`  | Rol insuficiente |
| `409`  | Archivo duplicado (mismo SHA-256) |

---

### `GET /api/upload/:id/status`

Estado de procesamiento de un contenido recién subido.

**Auth:** cualquier usuario autenticado

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "...",
    "status": "active",
    "type": "video",
    "created_at": "2026-03-05T10:00:00.000Z",
    "updated_at": "2026-03-05T10:00:05.000Z"
  }
}
```

---

### `DELETE /api/upload/:id`

Elimina un contenido (soft delete: marca `deleted_at`). Solo `superadmin` o el creador original.

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Content deleted successfully"
}
```

---

## 7. Endpoints de Categorías

### `GET /api/categories`

Lista todas las categorías activas, ordenadas por `display_order`.

**Response `200 OK`:**
```json
{
  "success": true,
  "count": 8,
  "data": [
    {
      "id": "uuid",
      "name": "Programación",
      "slug": "programacion",
      "description": "...",
      "parent_id": null,
      "icon": "💻",
      "color": "#4F46E5",
      "display_order": 1,
      "is_active": true,
      "created_at": "2026-02-01T00:00:00.000Z"
    }
  ]
}
```

---

### `GET /api/categories/tree`

Estructura jerárquica de categorías (raíces → subcategorías) via CTE recursivo en PostgreSQL.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    { "id": "...", "name": "Ciencias", "parent_id": null, "level": 0 },
    { "id": "...", "name": "Física", "parent_id": "...", "level": 1 },
    { "id": "...", "name": "Mecánica", "parent_id": "...", "level": 2 }
  ]
}
```

---

### `GET /api/categories/:id`

Categoría por ID con sus contenidos (máx 50, ordenados por `is_featured DESC, created_at DESC`).

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "category": { "id": "...", "name": "Redes", "slug": "redes" },
    "content_count": 12,
    "content": [
      {
        "id": "uuid",
        "title": "...",
        "type": "video",
        "thumbnail_path": "thumbnails/abc.jpg",
        "duration_seconds": 1800,
        "file_size": 200000000,
        "access_count": 45,
        "is_featured": false
      }
    ]
  }
}
```

---

## 8. Salud del servidor

### `GET /health`

Verifica conectividad con PostgreSQL y Redis.

**Response `200 OK` (todo OK):**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-05T10:00:00.000Z",
  "environment": "development",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

**Response `503 Service Unavailable` (algún servicio caído):**
```json
{
  "status": "degraded",
  "services": {
    "database": "disconnected",
    "redis": "connected"
  }
}
```

---

## 9. Formato de errores

Todos los errores siguen la misma estructura:

```json
{
  "success": false,
  "error": "Invalid credentials",
  "status": 401
}
```

En modo `development`, se incluye el stack trace completo.

---

## 10. Modelos de datos

### `UserDTO` (lo que el cliente recibe)

```ts
{
  id: string           // UUID
  username: string
  email: string | null
  full_name: string | null
  role: 'student' | 'teacher' | 'admin' | 'superadmin'
  is_active: boolean
  created_at: Date
}
```

### `ContentListDTO`

```ts
{
  id: string
  title: string
  description: string | null
  type: 'video' | 'pdf' | 'audio' | 'image' | 'document' | 'interactive'
  thumbnail_path: string | null
  duration_seconds: number | null
  file_size: number
  access_count: number
  average_rating: number | null
  is_featured: boolean
  created_at: Date
  category_name: string | null
}
```

---

## 11. Plan de la plataforma educativa (`/client`)

> Última actualización: 9 de marzo de 2026

El directorio `/client` tiene la estructura base (Vite + React + Tailwind) pero aún no tiene implementación real. A continuación el plan completo con arquitectura de nivel senior.

### 11.1 Propósito

`/client` es la **interfaz de administración y gestión** del CDN educativo. No es el portal de búsqueda IA (ese es `search_ui`). Sus usuarios son **docentes, admins y el superadmin**.

| App         | Puerto | Usuarios           | Función principal               |
|-------------|--------|--------------------|---------------------------------|
| `search_ui` | 5175   | Estudiantes        | Búsqueda IA, reproducción       |
| `client`    | 5174   | Docentes / Admins  | Gestión de contenido y usuarios |

---

### 11.2 Arquitectura: feature-based

La organización **no** es por tipo de archivo (components/pages/stores), sino por **dominio funcional**. Cada feature es autónoma y contiene todo lo que necesita: componentes, hooks, queries, tipos locales y tests.

```
client/src/
  features/
    auth/
      components/
        LoginForm.tsx          → formulario con react-hook-form + zod
        AuthGuard.tsx          → wrapper de rutas protegidas
      hooks/
        useAuth.ts             → login, logout, estado de sesión
      queries/
        authQueries.ts         → useLoginMutation, useMeQuery
      types.ts                 → LoginPayload, SessionUser
      index.ts                 → re-exports públicos del feature
    content/
      components/
        ContentTable.tsx       → tabla virtualizada (@tanstack/react-virtual)
        ContentCard.tsx
        ContentFilters.tsx     → filtros con URL sync (useSearchParams)
        VideoPlayer.tsx        → <video> nativo + Range requests
        DeleteConfirmDialog.tsx
        ContentEditForm.tsx    → react-hook-form + zod
      hooks/
        useContentFilters.ts   → sincroniza filtros con query string
        useVideoPlayer.ts      → lógica de reproducción aislada
      queries/
        contentQueries.ts      → useContentList, useContentById, useDeleteContent, useUpdateContent
      types.ts
      index.ts
    upload/
      components/
        UploadDropzone.tsx     → react-dropzone, validación de mime/tamaño
        UploadProgress.tsx     → barra real con XHR onprogress
        UploadQueue.tsx        → cola de múltiples archivos
      hooks/
        useUpload.ts           → XHR con progreso + polling de status
      queries/
        uploadQueries.ts       → useUploadMutation, useContentStatus
      types.ts
      index.ts
    categories/
      components/
        CategoryTree.tsx       → árbol jerárquico con @dnd-kit
        CategoryForm.tsx
      hooks/
        useCategoryTree.ts     → construye árbol desde lista plana
      queries/
        categoryQueries.ts     → useCategoriesTree, useCreateCategory, useUpdateCategory
      types.ts
      index.ts
    users/
      components/
        UserTable.tsx
        UserForm.tsx
        RoleBadge.tsx
      queries/
        userQueries.ts         → useUsers, useCreateUser, useUpdateUser
      types.ts
      index.ts
    dashboard/
      components/
        StatsCard.tsx
        RecentUploads.tsx
        AccessChart.tsx        → Recharts (ligero, sin D3)
      queries/
        statsQueries.ts        → useStats
      index.ts
  shared/
    ui/                        → primitivos sin lógica de negocio
      Button.tsx
      Input.tsx
      Badge.tsx
      Modal.tsx               → focus trap + aria-modal
      Skeleton.tsx            → placeholders de carga por forma
      ErrorBoundary.tsx       → por sección, no global
      Toast.tsx               → react-hot-toast wrapper
      VirtualList.tsx         → wrapper de @tanstack/react-virtual
    hooks/
      useDebounce.ts
      useLocalStorage.ts
      usePermission.ts        → usePermission('upload') → boolean según rol
    utils/
      formatBytes.ts
      formatDuration.ts
      buildApiUrl.ts
    constants.ts
  lib/
    apiClient.ts              → axios con interceptors (ver §11.5)
    queryClient.ts            → instancia TanStack Query con defaults
    router.tsx                → rutas con lazy loading
  types/
    api.ts                    → re-export de tipos compartidos con server
  App.tsx
  main.tsx
  index.css
```

---

### 11.3 Rutas y páginas

React Router v6 con **lazy loading** por feature para reducir bundle inicial:

```tsx
// lib/router.tsx
const Login        = lazy(() => import('../features/auth/components/LoginForm'))
const Dashboard    = lazy(() => import('../features/dashboard'))
const ContentList  = lazy(() => import('../features/content'))
const ContentDetail= lazy(() => import('../features/content/components/ContentDetail'))
const Upload       = lazy(() => import('../features/upload'))
const Categories   = lazy(() => import('../features/categories'))
const Users        = lazy(() => import('../features/users'))
```

| Ruta              | Componente lazy       | Rol mínimo  |
|-------------------|-----------------------|-------------|
| `/`               | redirect              | —           |
| `/login`          | `Login`               | público     |
| `/dashboard`      | `Dashboard`           | student     |
| `/content`        | `ContentList`         | student     |
| `/content/:id`    | `ContentDetail`       | student     |
| `/upload`         | `Upload`              | teacher     |
| `/categories`     | `Categories`          | admin       |
| `/users`          | `Users`               | admin       |

`AuthGuard` comprueba el rol con `usePermission` y redirige si es insuficiente.

---

### 11.4 Gestión de estado

Se distinguen dos tipos de estado con herramientas específicas para cada uno:

| Tipo                  | Herramienta              | Razón                                      |
|-----------------------|--------------------------|--------------------------------------------|
| **Server state**      | TanStack Query v5        | caché, revalidación, optimistic updates    |
| **Client/UI state**   | Zustand (mínimo)         | solo sidebar, notificaciones, modal abierto |
| **Form state**        | react-hook-form + zod    | validación compartida con esquemas del server |
| **URL state**         | `useSearchParams`        | filtros persistentes al compartir enlace   |

```ts
// stores/uiStore.ts  — el único store Zustand necesario
interface UIStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
  activeModal: string | null
  openModal: (id: string) => void
  closeModal: () => void
}
```

`authStore` no es necesario: el usuario autenticado se obtiene de `useMeQuery` (TanStack Query) y se cachea automáticamente.

---

### 11.5 Capa de API: axios con interceptors

```ts
// lib/apiClient.ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:3000',
  timeout: 15_000,
})

// Inyectar token en cada request
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('cdn_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Manejar 401 globalmente — logout silencioso
apiClient.interceptors.response.use(
  res => res,
  async error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('cdn_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

Módulos de queries (usan `apiClient` internamente y exponen hooks de TanStack Query):

```
features/
  auth/queries/authQueries.ts       → useMeQuery(), useLoginMutation()
  content/queries/contentQueries.ts → useContentList(filters), useContentById(id),
                                       useUpdateContent(), useDeleteContent()
  upload/queries/uploadQueries.ts   → useUploadMutation(), useContentStatus(id)
  categories/queries/...            → useCategoriesTree(), useCreateCategory()
  users/queries/...                 → useUsers(), useCreateUser()
  dashboard/queries/...             → useStats()
```

**Caché e invalidación:**

| Acción                | Invalida                            |
|-----------------------|-------------------------------------|
| Upload exitoso        | `['content', 'list']`, `['stats']`  |
| Editar contenido      | `['content', id]`, `['content', 'list']` |
| Borrar contenido      | `['content', 'list']`, `['stats']`  |
| Crear/editar categoría| `['categories']`                    |

Stale times:
- Lista de contenido: `60s` (cambia poco)
- Árbol de categorías: `300s`
- Stats del dashboard: `120s`
- Detalle de contenido: `120s`

---

### 11.6 Upload con progreso real

Sin polling. Progreso nativo con `XMLHttpRequest` + `upload.onprogress`:

```ts
// features/upload/hooks/useUpload.ts
export function useUpload() {
  const [progress, setProgress] = useState(0)
  const queryClient = useQueryClient()

  const upload = useCallback((formData: FormData): Promise<UploadedContent> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      const token = localStorage.getItem('cdn_token')

      xhr.upload.onprogress = e => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100))
      }

      xhr.onload = () => {
        if (xhr.status === 201) {
          const data = JSON.parse(xhr.responseText).data
          queryClient.invalidateQueries({ queryKey: ['content', 'list'] })
          queryClient.invalidateQueries({ queryKey: ['stats'] })
          resolve(data)
        } else {
          reject(JSON.parse(xhr.responseText))
        }
      }

      xhr.open('POST', `${import.meta.env.VITE_API_URL}/api/upload`)
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.send(formData)
    })
  }, [queryClient])

  return { upload, progress }
}
```

---

### 11.7 Validación compartida con zod

Los esquemas zod se usan tanto en el formulario (client) como en el futuro para validación server-side, evitando duplicar reglas:

```ts
// types/api.ts (o packages/types en monorepo futuro)
import { z } from 'zod'

export const uploadSchema = z.object({
  title:       z.string().min(3).max(200),
  description: z.string().max(2000).optional(),
  category_id: z.string().uuid(),
  is_featured: z.boolean().default(false),
})

export const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export type UploadPayload = z.infer<typeof uploadSchema>
export type LoginPayload  = z.infer<typeof loginSchema>
```

---

### 11.8 Accesibilidad (a11y)

- `Modal.tsx` implementa **focus trap** (`focus-trap-react`) y `aria-modal="true"`
- `ContentTable` usa `role="grid"` + navegación por teclado con `←→↑↓`
- Todos los botones de icono tienen `aria-label` explícito
- Skeletons con `aria-busy="true"` en el contenedor padre
- Contraste mínimo WCAG AA en todos los colores de texto

---

### 11.9 Testing

```
vitest + @testing-library/react
playwright (e2e)

features/auth/
  __tests__/
    LoginForm.test.tsx      → render, submit, error 401, bloqueo 423
    useAuth.test.ts         → unit del hook

features/upload/
  __tests__/
    useUpload.test.ts       → mock XHR, progreso, error 409

e2e/
  auth.spec.ts              → login → dashboard → logout
  upload.spec.ts            → login → ir a /upload → subir archivo → ver en lista
```

---

### 11.10 Dependencias

```bash
# core
npm install react-router-dom axios zod

# server state
npm install @tanstack/react-query @tanstack/react-query-devtools

# forms
npm install react-hook-form @hookform/resolvers

# upload & drag/drop
npm install react-dropzone

# listas grandes
npm install @tanstack/react-virtual

# drag & drop categorías
npm install @dnd-kit/core @dnd-kit/sortable

# notificaciones
npm install react-hot-toast

# charts (dashboard)
npm install recharts

# a11y
npm install focus-trap-react

# Zustand (solo UI state)
npm install zustand

# testing
npm install -D vitest @testing-library/react @testing-library/user-event
npm install -D playwright @playwright/test
```

---

### 11.11 Variables de entorno (`client/.env`)

```env
VITE_API_URL=http://localhost:3000
VITE_APP_TITLE=CDN Offline — Administración
VITE_QUERY_STALE_TIME=60000
```

---

### 11.12 Prioridad de implementación

| Sprint | Feature                    | Bloqueado por              |
|--------|----------------------------|----------------------------|
| 1      | `lib/` base (apiClient, queryClient, router) | — |
| 1      | `features/auth` completo   | `POST /api/auth/login`     |
| 2      | `features/content` listado + detalle | `GET /api/content` |
| 2      | `features/dashboard` stats básicas | `GET /api/stats` (pendiente) |
| 3      | `features/upload` con progreso real | `POST /api/upload` |
| 3      | `features/categories` árbol + CRUD | `POST/PATCH /api/categories` (pendiente) |
| 4      | `features/users`           | `GET/POST/PATCH /api/users` (pendiente) |
| 4      | Tests unitarios críticos   | sprints 1-3 completos      |
| 5      | e2e con Playwright         | todo lo anterior           |

---

### 11.13 Endpoints pendientes en el servidor

Los siguientes **aún no están implementados** y son necesarios para completar el cliente:

| Método  | Path                    | Sprint cliente | Notas                          |
|---------|-------------------------|----------------|--------------------------------|
| `PATCH` | `/api/content/:id`      | 2              | Editar título, categoría, destacado |
| `GET`   | `/api/stats`            | 2              | Totales para dashboard         |
| `POST`  | `/api/categories`       | 3              | Crear categoría                |
| `PATCH` | `/api/categories/:id`   | 3              | Editar / reordenar             |
| `GET`   | `/api/users`            | 4              | Listar usuarios (admin)        |
| `POST`  | `/api/users`            | 4              | Crear usuario                  |
| `PATCH` | `/api/users/:id`        | 4              | Editar rol/estado              |
| `DELETE`| `/api/users/:id`        | 4              | Soft delete / desactivar       |
| `POST`  | `/api/content/:id/rate` | 5              | Calificación de contenido      |
