# Plan de implementación — `client/admin`

> Fecha: 9 de marzo de 2026  
> Puerto de desarrollo: `5174`  
> Rol de usuario: `admin` / `superadmin`  
> Stack: Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · react-hook-form · zod · Recharts

---

## 1. Propósito

`/client/admin` es el **panel de control del curador / administrador** de la CDN. Su función principal es la cola de revisión de contenido enviado por docentes, pero también incluye gestión completa de la plataforma: categorías, usuarios y estadísticas.

```
Login (admin/superadmin)
  ├── Cola de revisión        ← función principal
  ├── Gestión de contenido    ← todo el catálogo, no solo pendientes
  ├── Gestión de categorías
  ├── Gestión de usuarios
  └── Dashboard / estadísticas
```

---

## 2. Flujo de revisión (función core)

```
Admin abre cola de revisión
  │
  ├── Ve listado de envíos con status='pending'
  │     título · tipo · usuario que envió · fecha · tamaño
  │
  ├── Abre detalle de un envío
  │     ├── Preview real: video player / PDF viewer / imagen
  │     ├── Metadata FFmpeg: duración, resolución, codec, bitrate
  │     ├── Información del sender: nombre, rol, historial
  │     └── Formulario de revisión
  │
  └── Decisión:
        ├── [Aprobar]  → PATCH status: 'active'  (visible en CDN)
        ├── [Curar]    → edita título/desc/categoría → PATCH status: 'active'
        └── [Rechazar] → motivo obligatorio → PATCH status: 'rejected'
                         → sender recibe notificación visual en su app
```

---

## 3. Páginas y rutas

| Ruta                     | Componente            | Descripción                                  |
|--------------------------|-----------------------|----------------------------------------------|
| `/`                      | redirect              | → `/login` o → `/review`                    |
| `/login`                 | `LoginPage`           | Solo para roles admin/superadmin             |
| `/review`                | `ReviewQueuePage`     | Cola de pendientes — vista principal         |
| `/review/:id`            | `ReviewDetailPage`    | Detalle completo + formulario de decisión    |
| `/content`               | `ContentPage`         | Catálogo completo con filtros y acciones     |
| `/content/:id`           | `ContentDetailPage`   | Ver/editar cualquier contenido activo        |
| `/categories`            | `CategoriesPage`      | Árbol de categorías, crear/editar/reordenar  |
| `/users`                 | `UsersPage`           | Gestión de cuentas (solo superadmin)         |
| `/dashboard`             | `DashboardPage`       | Métricas y gráficos                          |

---

## 4. Estructura de archivos

```
client/admin/
  src/
    features/
      auth/
        components/
          LoginForm.tsx
          AuthGuard.tsx          → redirige si rol < admin
        hooks/
          useAuth.ts
        queries/
          authQueries.ts
        types.ts
        index.ts
      review/                    ← feature principal
        components/
          ReviewQueue.tsx        → tabla de pendientes, ordenable por fecha/tipo
          ReviewQueueCard.tsx    → card compacta con avatar del sender
          ReviewDetail.tsx       → layout split: preview izq. | formulario der.
          ReviewForm.tsx         → react-hook-form: acción + motivo (req. si rechaza)
          ContentPreview.tsx     → dispatcher: VideoPreview | PDFPreview | ImagePreview
          VideoPreview.tsx       → <video> nativo + src=/api/content/:id/stream
          PDFPreview.tsx         → <iframe> o react-pdf
          ImagePreview.tsx       → <img> con lazy load
          MetadataPanel.tsx      → muestra codec, fps, resolución, bitrate, hash
          SenderInfo.tsx         → nombre, rol, historial de envíos del sender
          DecisionBadge.tsx      → approved/rejected/pending con icon
        hooks/
          useReviewQueue.ts      → filtros + paginación de la cola
          useReviewDecision.ts   → lógica de submit del formulario
        queries/
          reviewQueries.ts       → usePendingQueue, useReviewById, useReviewDecision
        schemas/
          reviewSchema.ts        → zod: action(approve|curate|reject), reason(req si reject)
        types.ts
        index.ts
      content/
        components/
          ContentTable.tsx       → tabla virtualizada, todos los status
          ContentFilters.tsx     → status, tipo, categoría, búsqueda, sort
          ContentEditForm.tsx    → editar título/desc/categoría/destacado
          DeleteConfirmDialog.tsx
          StatusToggle.tsx       → activar/archivar inline
        hooks/
          useContentFilters.ts   → URL sync con useSearchParams
        queries/
          contentQueries.ts      → useAllContent, useContentById, useUpdateContent, useDeleteContent
        types.ts
        index.ts
      categories/
        components/
          CategoryTree.tsx       → árbol con @dnd-kit/sortable
          CategoryForm.tsx       → crear / editar
          CategoryDeleteDialog.tsx
        hooks/
          useCategoryTree.ts     → lista plana → árbol jerárquico
        queries/
          categoryQueries.ts     → useCategoriesTree, useCreateCategory, useUpdateCategory, useDeleteCategory
        types.ts
        index.ts
      users/
        components/
          UserTable.tsx
          UserForm.tsx           → crear usuario, asignar rol
          UserStatusToggle.tsx   → activar/desactivar cuenta
          RoleBadge.tsx
        queries/
          userQueries.ts         → useUsers, useCreateUser, useUpdateUser
        types.ts
        index.ts
      dashboard/
        components/
          StatsGrid.tsx          → total contenido / pendientes / usuarios / accesos hoy
          AccessChart.tsx        → Recharts LineChart: accesos por día (últimos 30 días)
          TopContent.tsx         → top 10 más vistos
          PendingAlert.tsx       → banner si hay N envíos pendientes sin revisar
          RecentDecisions.tsx    → últimas 10 decisiones del admin
        queries/
          statsQueries.ts        → useStats, useAccessTimeline, useTopContent
        index.ts
    shared/
      ui/
        Button.tsx
        Input.tsx
        Textarea.tsx
        Select.tsx
        Badge.tsx
        Modal.tsx               → focus trap + aria-modal
        Skeleton.tsx
        ErrorBoundary.tsx       → por sección
        Toast.tsx
        ConfirmDialog.tsx       → reutilizable para delete/reject
        Pagination.tsx
        VirtualList.tsx         → @tanstack/react-virtual
        Tooltip.tsx
      layout/
        Sidebar.tsx             → nav con badge de pendientes en "Cola"
        TopBar.tsx              → nombre del admin + logout
        PageHeader.tsx
      hooks/
        useDebounce.ts
        useLocalStorage.ts
        usePermission.ts        → usePermission('users') → rol >= superadmin
      utils/
        formatBytes.ts
        formatDuration.ts
        formatDate.ts
        buildQueryString.ts
    lib/
      apiClient.ts
      queryClient.ts
      router.tsx
    types/
      api.ts
    App.tsx
    main.tsx
    index.css
  public/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.js
  postcss.config.js
  .env
  .env.example
```

---

## 5. Layout del panel de revisión

```
┌─────────────────────────────────────────────────────────────────┐
│ CDN Admin        Cola de revisión (3 pendientes)    Admin ▼     │
├──────────┬──────────────────────────────────────────────────────┤
│ Dashboard│  Cola de revisión                                    │
│ Cola [3] │  ┌──────────────────────────────────────────────┐   │
│ Contenido│  │ 🎬 "Intro a Redes TCP/IP"   Juan García  2h  │   │
│ Categorías│  │    video · 450 MB · Redes                    │   │
│ Usuarios │  ├──────────────────────────────────────────────┤   │
│          │  │ 📄 "Guía de Python"         Ana Torres   5h  │   │
│          │  │    pdf · 8 MB · Programación                  │   │
│          │  └──────────────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────────────┘
```

Al hacer clic en un ítem:

```
┌──────────────────────────────────────────────────────────────────┐
│ ← Cola     "Intro a Redes TCP/IP"                                │
├──────────────────────────────┬───────────────────────────────────┤
│  PREVIEW                     │  REVISIÓN                         │
│                              │                                   │
│  ┌────────────────────────┐  │  Enviado por: Juan García         │
│  │                        │  │  Fecha: 9 mar 2026, 10:32         │
│  │   ▶  VIDEO PLAYER      │  │  Categoría propuesta: Redes       │
│  │                        │  │                                   │
│  └────────────────────────┘  │  ── Curación (opcional) ──        │
│                              │  Título    [___________________]  │
│  Metadata                    │  Descripción [_________________]  │
│  Duración:  45:00            │  Categoría [Seleccionar ▼     ]   │
│  Resolución: 1920×1080       │  Destacar  [ ]                    │
│  Codec:     h264             │                                   │
│  Bitrate:   2.5 Mbps         │  Motivo de rechazo (si rechaza):  │
│  Tamaño:    450 MB           │  [_______________________________] │
│  Hash:      abc123...        │                                   │
│                              │  [Rechazar] [Curar+Aprobar] [Aprobar] │
└──────────────────────────────┴───────────────────────────────────┘
```

---

## 6. Formulario de revisión — schema zod

```ts
// features/review/schemas/reviewSchema.ts
import { z } from 'zod'

export const reviewSchema = z.discriminatedUnion('action', [
  z.object({
    action: z.literal('approve'),
  }),
  z.object({
    action: z.literal('curate'),
    title:       z.string().min(3).max(200).optional(),
    description: z.string().max(2000).optional(),
    category_id: z.string().uuid().optional(),
    is_featured: z.boolean().optional(),
  }),
  z.object({
    action: z.literal('reject'),
    reason: z.string().min(10, 'El motivo debe tener al menos 10 caracteres'),
  }),
])

export type ReviewPayload = z.infer<typeof reviewSchema>
```

---

## 7. Gestión de estado

| Tipo         | Herramienta          | Qué maneja                                    |
|--------------|----------------------|-----------------------------------------------|
| Server state | TanStack Query v5    | cola, contenido, categorías, usuarios, stats  |
| UI state     | Zustand (mínimo)     | sidebar, modal activo, notificaciones         |
| Form state   | react-hook-form + zod| ReviewForm, ContentEditForm, UserForm         |
| URL state    | `useSearchParams`    | filtros de ContentTable, paginación           |

### Invalidaciones de caché

| Acción admin          | Invalida                                     |
|-----------------------|----------------------------------------------|
| Aprobar envío         | `['review', 'queue']`, `['content', 'list']`, `['stats']` |
| Rechazar envío        | `['review', 'queue']`                        |
| Editar contenido      | `['content', id]`, `['content', 'list']`     |
| Crear categoría       | `['categories']`                             |
| Desactivar usuario    | `['users']`                                  |

---

## 8. Sidebar badge de pendientes

El badge con el número de envíos pendientes en el sidebar se actualiza automáticamente con `useQuery` cada 60 segundos:

```ts
const { data } = useQuery({
  queryKey: ['review', 'count'],
  queryFn: () => apiClient.get('/api/upload/pending/count'),
  refetchInterval: 60_000,
})
```

---

## 9. Permisos por rol

| Feature            | `admin` | `superadmin` |
|--------------------|---------|--------------|
| Ver cola revisión  | ✅      | ✅           |
| Aprobar/rechazar   | ✅      | ✅           |
| Editar contenido   | ✅      | ✅           |
| Borrar contenido   | ❌      | ✅           |
| Gestionar categorías | ✅    | ✅           |
| Gestionar usuarios | ❌      | ✅           |
| Ver dashboard      | ✅      | ✅           |

`usePermission(action)` devuelve boolean comparando `req.user.role` con la tabla anterior.

---

## 10. Variables de entorno

```env
# client/admin/.env
VITE_API_URL=http://localhost:3000
VITE_APP_TITLE=CDN Offline — Panel Administrativo
VITE_QUEUE_REFETCH_INTERVAL_MS=60000
```

---

## 11. Dependencias

```bash
npm create vite@latest admin -- --template react-ts
cd admin

npm install react-router-dom axios zod
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install react-hook-form @hookform/resolvers
npm install recharts
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
npm install react-hot-toast
npm install focus-trap-react
npm install zustand
npm install -D tailwindcss postcss autoprefixer
npm install -D vitest @testing-library/react @testing-library/user-event
```

---

## 12. Endpoints del servidor necesarios

| Método  | Path                          | Estado       | Notas                                 |
|---------|-------------------------------|--------------|---------------------------------------|
| `POST`  | `/api/auth/login`             | ✅ existe     |                                       |
| `GET`   | `/api/auth/me`                | ✅ existe     |                                       |
| `GET`   | `/api/upload/pending`         | ❌ pendiente  | Cola de status='pending', paginada    |
| `GET`   | `/api/upload/pending/count`   | ❌ pendiente  | Solo el número, para el badge         |
| `PATCH` | `/api/upload/:id/review`      | ❌ pendiente  | Body: `ReviewPayload` (ver schema)    |
| `GET`   | `/api/content`                | ✅ existe     |                                       |
| `PATCH` | `/api/content/:id`            | ❌ pendiente  |                                       |
| `DELETE`| `/api/upload/:id`             | ✅ existe     |                                       |
| `GET`   | `/api/categories/tree`        | ✅ existe     |                                       |
| `POST`  | `/api/categories`             | ❌ pendiente  |                                       |
| `PATCH` | `/api/categories/:id`         | ❌ pendiente  |                                       |
| `GET`   | `/api/users`                  | ❌ pendiente  |                                       |
| `POST`  | `/api/users`                  | ❌ pendiente  |                                       |
| `PATCH` | `/api/users/:id`              | ❌ pendiente  |                                       |
| `GET`   | `/api/stats`                  | ❌ pendiente  | Totales para dashboard                |
| `GET`   | `/api/stats/timeline`         | ❌ pendiente  | Accesos por día (gráfico)             |

---

## 13. Endpoints nuevos en el servidor — cambios necesarios

### `ContentStatus` enum

Añadir `pending` y `rejected`:
```ts
export enum ContentStatus {
  PENDING    = 'pending',     // ← nuevo
  PROCESSING = 'processing',
  ACTIVE     = 'active',
  REJECTED   = 'rejected',   // ← nuevo
  ARCHIVED   = 'archived',
  FAILED     = 'failed',
}
```

### `PATCH /api/upload/:id/review`

```ts
// Body (discriminated union)
{ action: 'approve' }
{ action: 'curate', title?, description?, category_id?, is_featured? }
{ action: 'reject', reason: string }

// Response 200
{ success: true, data: { id, status, updated_at } }
```

El campo `rejected_reason` debe añadirse a la tabla `content` en la DB.

---

## 14. Sprints

| Sprint | Entregable                                                  |
|--------|-------------------------------------------------------------|
| 1      | `lib/` base + feature `auth` + layout (sidebar + topbar)   |
| 2      | feature `review` — cola + detalle + formulario de decisión  |
| 3      | feature `content` — tabla completa + edición inline        |
| 4      | feature `categories` — árbol + CRUD                         |
| 5      | feature `dashboard` + feature `users` (superadmin)         |
| 6      | Tests unitarios + e2e flujo de revisión completo            |
