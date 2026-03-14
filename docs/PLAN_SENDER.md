# Plan de implementación — `client/sender`

> Fecha: 9 de marzo de 2026  
> Puerto de desarrollo: `5173`  
> Rol de usuario: `teacher` (puede ampliarse a `admin`)  
> Stack: Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · react-hook-form · zod

---

## 1. Propósito

`/client/sender` es la interfaz que usa un **docente** para enviar contenido a la CDN. El contenido no se publica directamente: queda en estado `pending` hasta que un administrador lo revise en `/client/admin`.

El sender NO es un panel de administración. Es una app de usuario final con flujo lineal:

```
Login → Dashboard personal → Subir contenido → Ver mis envíos → Ver estado / motivo de rechazo
```

---

## 2. Flujo completo

```
[Sender]                          [Server]                        [Admin]
   │                                  │                               │
   ├─ POST /api/auth/login ──────────►│                               │
   │◄─ JWT (role: teacher) ───────────┤                               │
   │                                  │                               │
   ├─ POST /api/upload ──────────────►│                               │
   │  multipart/form-data             │ status: 'pending'             │
   │  (archivo + metadata)            │ archivo en /storage/temp/     │
   │◄─ { id, status: 'pending' } ─────┤                               │
   │                                  │                               │
   │  [polling / refresco manual]     │                    Admin revisa│
   │                                  │                    y decide    │
   ├─ GET /api/upload/:id/status ────►│◄─ PATCH /api/upload/:id/review┤
   │◄─ { status: 'active' |           │                               │
   │         'rejected', reason } ────┤                               │
```

---

## 3. Páginas y rutas

| Ruta             | Componente        | Descripción                                    |
|------------------|-------------------|------------------------------------------------|
| `/`              | redirect          | → `/login` si no autenticado, → `/dashboard` si sí |
| `/login`         | `LoginPage`       | Formulario de acceso                           |
| `/dashboard`     | `DashboardPage`   | Resumen: enviados / pendientes / activos / rechazados |
| `/upload`        | `UploadPage`      | Formulario de envío de contenido               |
| `/submissions`   | `SubmissionsPage` | Historial de todos mis envíos con filtros      |
| `/submissions/:id` | `SubmissionDetail` | Detalle + estado actual + motivo si rechazado |

Todas las rutas excepto `/login` están protegidas por `AuthGuard`.

---

## 4. Estructura de archivos

```
client/sender/
  src/
    features/
      auth/
        components/
          LoginForm.tsx          → react-hook-form + zod, manejo de 423 (bloqueo)
          AuthGuard.tsx          → verifica token, redirige a /login
        hooks/
          useAuth.ts             → login(), logout(), usuario actual
        queries/
          authQueries.ts         → useLoginMutation, useMeQuery
        types.ts
        index.ts
      submissions/
        components/
          SubmissionTable.tsx    → tabla con estado visual por badge
          SubmissionCard.tsx     → card para vista móvil
          StatusBadge.tsx        → pending/active/rejected con color
          RejectionAlert.tsx     → banner con motivo de rechazo
          SubmissionDetail.tsx   → vista completa de un envío
        hooks/
          useSubmissionStatus.ts → polling cada 10s mientras status='pending'
        queries/
          submissionQueries.ts   → useMySubmissions, useSubmissionById
        types.ts
        index.ts
      upload/
        components/
          UploadForm.tsx         → dropzone + campos + validación
          FilePreview.tsx        → preview de video/PDF/imagen antes de enviar
          UploadProgress.tsx     → barra real con XHR onprogress
          UploadSuccess.tsx      → confirmación con link a detalle
        hooks/
          useUpload.ts           → XHR con progreso, manejo de 409 (duplicado)
        queries/
          uploadMutations.ts     → useUploadMutation
        schemas/
          uploadSchema.ts        → zod: title(3-200), category_id(uuid), etc.
        types.ts
        index.ts
      dashboard/
        components/
          StatsRow.tsx           → 4 contadores: total / pendiente / activo / rechazado
          RecentSubmissions.tsx  → últimos 5 envíos
        queries/
          dashboardQueries.ts    → useMyStats (derivado de useMySubmissions)
        index.ts
    shared/
      ui/
        Button.tsx
        Input.tsx
        Select.tsx
        Badge.tsx
        Modal.tsx               → focus trap + aria-modal
        Skeleton.tsx
        ErrorBoundary.tsx
        Toast.tsx               → react-hot-toast wrapper
        ProgressBar.tsx
      hooks/
        useDebounce.ts
        useLocalStorage.ts
      utils/
        formatBytes.ts
        formatDuration.ts
        formatDate.ts
    lib/
      apiClient.ts              → axios + interceptor 401 → logout
      queryClient.ts            → TanStack Query con stale times
      router.tsx                → rutas con lazy loading
    types/
      api.ts                    → tipos compartidos (ContentStatus, UserRole, etc.)
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

## 5. Componente clave: `UploadForm`

```
┌─────────────────────────────────────────────────┐
│  Subir contenido                                 │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │   Arrastra tu archivo aquí              │    │
│  │   o haz clic para seleccionar           │    │
│  │   Video · PDF · Audio · Imagen          │    │
│  └─────────────────────────────────────────┘    │
│  [preview del archivo si es video/imagen]        │
│                                                  │
│  Título *          [____________________]        │
│  Descripción       [____________________]        │
│  Categoría *       [Seleccionar ▼      ]        │
│  ¿Destacar?        [ ] Sí                        │
│                                                  │
│  ████████████░░░░░░░  67%  Subiendo...           │
│                                                  │
│                    [Cancelar] [Enviar]           │
└─────────────────────────────────────────────────┘
```

Validación con zod antes de abrir el XHR. Si el servidor responde `409` (duplicado), muestra mensaje específico sin lanzar error genérico.

---

## 6. Estados de un envío y su representación visual

| `status`     | Badge color | Descripción para el usuario                    |
|--------------|-------------|------------------------------------------------|
| `pending`    | Amarillo    | "En revisión — un administrador lo revisará pronto" |
| `active`     | Verde       | "Publicado — ya está disponible en la CDN"     |
| `rejected`   | Rojo        | "Rechazado" + motivo expandible                |
| `processing` | Azul        | "Procesando — extrayendo metadata..."          |

El hook `useSubmissionStatus` hace polling cada 10 segundos mientras `status === 'pending'` y detiene el polling al llegar a `active` o `rejected`.

---

## 7. Gestión de estado

| Tipo           | Herramienta          | Qué maneja                              |
|----------------|----------------------|-----------------------------------------|
| Server state   | TanStack Query v5    | submissions, upload mutation, me query  |
| UI state       | Zustand (mínimo)     | sidebar (móvil), modal abierto          |
| Form state     | react-hook-form + zod| UploadForm, LoginForm                   |

No hay `contentStore` ni `authStore` — el usuario autenticado viene de `useMeQuery`.

---

## 8. Capa de API

```ts
// lib/apiClient.ts
apiClient.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('cdn_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
```

Queries relevantes:

```ts
// features/submissions/queries/submissionQueries.ts
export const useMySubmissions = (filters?) =>
  useQuery({
    queryKey: ['submissions', 'mine', filters],
    queryFn: () => apiClient.get('/api/upload/mine', { params: filters }),
    staleTime: 30_000,
  })

export const useSubmissionById = (id: string) =>
  useQuery({
    queryKey: ['submissions', id],
    queryFn: () => apiClient.get(`/api/upload/${id}/status`),
    staleTime: 10_000,
  })
```

---

## 9. Accesibilidad

- `LoginForm`: `aria-describedby` en inputs con error, `aria-live="polite"` en el mensaje de error global
- `UploadForm`: dropzone accesible por teclado (`role="button"`, `tabIndex=0`)
- Modales con `focus-trap-react` + `aria-modal="true"`
- `StatusBadge` incluye siempre texto visible, no solo color
- WCAG AA en todos los colores de estado

---

## 10. Variables de entorno

```env
# client/sender/.env
VITE_API_URL=http://localhost:3000
VITE_APP_TITLE=CDN Offline — Enviar Contenido
VITE_POLL_INTERVAL_MS=10000
```

---

## 11. Dependencias

```bash
npm create vite@latest sender -- --template react-ts
cd sender

npm install react-router-dom axios zod
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install react-hook-form @hookform/resolvers
npm install react-dropzone
npm install react-hot-toast
npm install focus-trap-react
npm install zustand
npm install -D tailwindcss postcss autoprefixer
npm install -D vitest @testing-library/react @testing-library/user-event
```

---

## 12. Endpoints del servidor necesarios

| Método | Path                       | Estado    | Notas                              |
|--------|----------------------------|-----------|------------------------------------|
| `POST` | `/api/auth/login`          | ✅ existe  |                                    |
| `GET`  | `/api/auth/me`             | ✅ existe  |                                    |
| `POST` | `/api/upload`              | ✅ existe  | Solo `superadmin` hoy → ampliar a `teacher` |
| `GET`  | `/api/upload/:id/status`   | ✅ existe  |                                    |
| `GET`  | `/api/upload/mine`         | ❌ pendiente | Mis envíos filtrados por `created_by` |
| `GET`  | `/api/categories`          | ✅ existe  | Para el select de categoría        |

El único endpoint nuevo requerido es `GET /api/upload/mine`. El resto ya existe.

---

## 13. Sprints

| Sprint | Entregable                                    |
|--------|-----------------------------------------------|
| 1      | `lib/` base + feature `auth` completo         |
| 2      | feature `upload` con progreso real            |
| 3      | feature `submissions` (lista + detalle + polling) |
| 4      | feature `dashboard` con stats personales      |
| 5      | Responsive móvil + a11y audit + tests unitarios |
