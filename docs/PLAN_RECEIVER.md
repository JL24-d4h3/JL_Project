# Plan de implementación — `client/receiver`

> Fecha: 9 de marzo de 2026  
> Puerto de desarrollo: `5175`  
> Ubicación actual: `/search_ui` (se moverá a `/client/receiver` cuando corresponda)  
> Rol de usuario: `student` (y usuarios no autenticados para exploracion)  
> Stack: Vite · React 18 · TypeScript · Tailwind CSS · TanStack Query v5 · react-hook-form · zod

---

## 1. Propósito

`/client/receiver` (actualmente `search_ui`) es la **interfaz de consumo educativo** de la CDN. Es la app que usan los estudiantes para buscar, descubrir y reproducir el contenido publicado.

Es la única app de las tres que admite **usuarios no autenticados** en modo exploración. El inicio de sesión desbloquea funciones adicionales (historial, favoritos, calificaciones).

```
Explorar contenido (sin login)
  ├── Búsqueda con IA (motor en ai_engine, puerto 8000)
  ├── Navegar por categorías
  ├── Ver detalle de contenido
  └── Reproducir video / ver PDF

Con login (student):
  ├── Todo lo anterior +
  ├── Historial de visualizaciones
  ├── Calificar contenido (⭐)
  └── Guardar favoritos
```

---

## 2. Estado actual (`search_ui`)

Lo que ya está implementado y funciona:

| Componente              | Estado | Notas                                              |
|-------------------------|--------|----------------------------------------------------|
| Búsqueda con streaming IA | ✅   | `AIOverview.tsx` con tema dracula, sin bordes      |
| Renderizado Markdown    | ✅     | ReactMarkdown + remark-gfm + rehype-katex          |
| Bloques de código       | ✅     | react-syntax-highlighter, píldora para línea única |
| Resultados de búsqueda  | ✅     | `SearchResults.tsx`                               |
| Conexión al motor IA    | ✅     | SSE streaming desde `ai_engine` puerto 8000        |
| Diseño base             | ✅     | Tailwind, fondo blanco, cards de resultado         |

Lo que falta por construir:

| Feature                    | Sprint |
|----------------------------|--------|
| Navegación por categorías  | 2      |
| Detalle de contenido       | 2      |
| Reproductor de video       | 2      |
| Visor de PDF               | 3      |
| Login / sesión de estudiante | 3    |
| Historial de visualizaciones | 4    |
| Calificaciones (⭐)        | 4      |
| Favoritos                  | 4      |
| Modo offline / PWA         | 5      |

---

## 3. Páginas y rutas

| Ruta               | Componente          | Auth   | Descripción                                    |
|--------------------|---------------------|--------|------------------------------------------------|
| `/`                | `SearchPage`        | no     | Búsqueda principal con IA (ya existe)          |
| `/browse`          | `BrowsePage`        | no     | Explorar por categorías                        |
| `/browse/:slug`    | `CategoryPage`      | no     | Contenido de una categoría                     |
| `/content/:id`     | `ContentDetailPage` | no     | Detalle, player, info, calificación            |
| `/login`           | `LoginPage`         | no     | Login estudiante                               |
| `/history`         | `HistoryPage`       | sí     | Historial de visualizaciones                   |
| `/favorites`       | `FavoritesPage`     | sí     | Contenido guardado                             |

---

## 4. Estructura de archivos

```
client/receiver/            (actualmente search_ui/)
  src/
    features/
      search/               ← ya implementado
        components/
          SearchBar.tsx
          SearchResults.tsx
          AIOverview.tsx     → motor IA con streaming SSE
          ResultCard.tsx
        hooks/
          useSearch.ts
          useAIStream.ts
        queries/
          searchQueries.ts
        index.ts
      browse/               ← nuevo
        components/
          CategoryGrid.tsx   → grid de categorías con ícono y color
          CategoryBreadcrumb.tsx
          ContentGrid.tsx    → grid de cards de contenido
          ContentCard.tsx    → thumbnail + título + tipo + duración
          FeaturedBanner.tsx → carrusel de contenido destacado
        hooks/
          useBrowse.ts
        queries/
          browseQueries.ts   → useCategoriesTree, useContentByCategory
        index.ts
      player/               ← nuevo
        components/
          ContentDetail.tsx  → layout: player/visor + info lateral
          VideoPlayer.tsx    → <video> nativo + Range requests + controls custom
          PDFViewer.tsx      → <iframe> o react-pdf
          AudioPlayer.tsx    → <audio> con controls
          ImageViewer.tsx    → lightbox simple
          RatingStars.tsx    → 1-5 estrellas, requiere login
          RelatedContent.tsx → otros contenidos de la misma categoría
          TagList.tsx
        hooks/
          useVideoPlayer.ts   → lógica de reproducción aislada
          useContentDetail.ts → fetch + registrar acceso
        queries/
          playerQueries.ts    → useContentById, useRelatedContent, useRateMutation
        index.ts
      auth/                  ← nuevo (login de estudiantes)
        components/
          LoginForm.tsx
          AuthGuard.tsx       → para rutas de historial/favoritos
        hooks/
          useAuth.ts
        queries/
          authQueries.ts
        index.ts
      history/               ← nuevo
        components/
          HistoryList.tsx
          HistoryCard.tsx    → con fecha y duración vista
        queries/
          historyQueries.ts  → useMyHistory
        index.ts
      favorites/             ← nuevo
        components/
          FavoritesList.tsx
          FavoriteButton.tsx → corazón toggle, requiere login
        queries/
          favoriteQueries.ts → useMyFavorites, useToggleFavorite
        index.ts
    shared/
      ui/
        Button.tsx
        Badge.tsx
        Skeleton.tsx
        ErrorBoundary.tsx
        Toast.tsx
        Modal.tsx
        Thumbnail.tsx        → imagen con fallback a ícono por tipo
        DurationBadge.tsx    → "45:00" o "8 MB"
        TypeIcon.tsx         → ícono según tipo (video/pdf/audio)
      hooks/
        useDebounce.ts
        useIntersectionObserver.ts  → infinite scroll
      utils/
        formatDuration.ts
        formatBytes.ts
        formatDate.ts
    lib/
      apiClient.ts           → axios, sin interceptor de redirección (no-auth OK)
      aiClient.ts            → fetch SSE al ai_engine puerto 8000
      queryClient.ts
      router.tsx
    types/
      api.ts
    App.tsx
    main.tsx
    index.css
```

---

## 5. Reproductor de video

Usa `<video>` nativo — el navegador maneja Range requests automáticamente:

```tsx
// features/player/components/VideoPlayer.tsx
<video
  src={`${API_URL}/api/content/${id}/stream`}
  poster={`${API_URL}/api/content/${id}/thumbnail`}
  controls
  preload="metadata"
  style={{ width: '100%', borderRadius: '0.5rem' }}
  onPlay={() => trackView(id)}           // registra acceso
  onEnded={() => markCompleted(id)}      // historial
/>
```

No se necesita HLS ni DASH para este contexto offline. El Range request nativo del navegador da seek funcional sobre el endpoint `/stream` existente.

---

## 6. Integración con el motor IA

El motor IA corre en `ai_engine` puerto `8000`. La búsqueda usa SSE (Server-Sent Events):

```
GET http://localhost:8000/api/v1/search?q=...&stream=true
Content-Type: text/event-stream

data: {"type":"token","content":"Para crear..."}
data: {"type":"token","content":" una lista..."}
data: {"type":"sources","sources":[{"id":"uuid","title":"..."}]}
data: {"type":"done"}
```

`AIOverview.tsx` ya consume este stream correctamente. Los `sources` devueltos por el motor IA se cruzan con `GET /api/content/:id` del server para mostrar cards de resultado con thumbnail y metadata real.

---

## 7. Modo sin autenticación

A diferencia de sender y admin, receiver funciona sin login para la mayoría de features. La filosofía es: **no pedir login para consumir, solo para participar**.

| Feature              | Sin login | Con login |
|----------------------|-----------|-----------|
| Buscar               | ✅        | ✅        |
| Navegar categorías   | ✅        | ✅        |
| Ver detalle          | ✅        | ✅        |
| Reproducir video     | ✅        | ✅        |
| Ver PDF              | ✅        | ✅        |
| Calificar (⭐)       | ❌        | ✅        |
| Historial            | ❌        | ✅        |
| Favoritos            | ❌        | ✅        |

---

## 8. Búsqueda: flujo completo

```
Usuario escribe query
  │
  ├── useDebounce(300ms)
  │
  ├── GET /ai_engine/api/v1/search?q=... (SSE stream)
  │     → AIOverview muestra respuesta progresiva
  │
  └── GET /api/content?search=... (TanStack Query)
        → SearchResults muestra cards de contenido real
             con thumbnail, tipo, duración, categoría
```

Ambas peticiones van en paralelo. El AI Overview llega primero (stream) y las cards de resultado llegan cuando completa la query a PostgreSQL.

---

## 9. Variables de entorno

```env
# client/receiver/.env  (actualmente search_ui/.env)
VITE_API_URL=http://localhost:3000
VITE_AI_URL=http://localhost:8000
VITE_APP_TITLE=CDN Offline — Búsqueda Educativa
```

---

## 10. Dependencias actuales (`search_ui/package.json`)

Ya instaladas y funcionando:
- `react-markdown`, `remark-gfm`, `remark-math`, `rehype-katex`
- `react-syntax-highlighter`
- `tailwindcss`

A instalar para los sprints siguientes:

```bash
npm install react-router-dom axios
npm install @tanstack/react-query
npm install react-hot-toast
npm install react-pdf              # visor de PDF
npm install -D vitest @testing-library/react
```

---

## 11. Endpoints del servidor necesarios

| Método | Path                        | Estado    | Notas                                   |
|--------|-----------------------------|-----------|-----------------------------------------|
| `GET`  | `/api/content`              | ✅ existe  | Para búsqueda + browse                  |
| `GET`  | `/api/content/:id`          | ✅ existe  | Para detalle                            |
| `GET`  | `/api/content/:id/stream`   | ✅ existe  | Para video/audio                        |
| `GET`  | `/api/content/:id/thumbnail`| ✅ existe  | Para poster del video y cards           |
| `GET`  | `/api/categories/tree`      | ✅ existe  | Para navegar por categorías             |
| `GET`  | `/api/categories/:id`       | ✅ existe  | Contenido de una categoría              |
| `POST` | `/api/auth/login`           | ✅ existe  | Login de estudiante                     |
| `GET`  | `/api/auth/me`              | ✅ existe  |                                         |
| `POST` | `/api/content/:id/rate`     | ❌ pendiente | Calificación 1-5                      |
| `GET`  | `/api/history`              | ❌ pendiente | Historial del usuario autenticado      |
| `POST` | `/api/history/:id`          | ❌ pendiente | Registrar visualización                |
| `GET`  | `/api/favorites`            | ❌ pendiente | Favoritos del usuario                  |
| `POST/DELETE` | `/api/favorites/:id` | ❌ pendiente | Toggle favorito                     |

La mayoría del receiver funciona **con endpoints que ya existen**. Historial, favoritos y calificaciones son las únicas adiciones.

---

## 12. Migración `search_ui` → `client/receiver`

Cuando sea moment de mover (coordinar con el compañero que trabaja en esta app):

```bash
# Desde la raíz del proyecto CDN/
mkdir -p client
mv search_ui client/receiver
# Actualizar VITE_API_URL en .env si cambia el puerto
# Actualizar docker-compose.dev.yml si existe referencia a search_ui
# Actualizar README.md
git add -A
git commit -m "refactor: mover search_ui → client/receiver"
```

No hay cambios de código — solo cambia la ubicación física.

---

## 13. Sprints

| Sprint | Entregable                                              | Responsable  |
|--------|---------------------------------------------------------|--------------|
| 1      | Búsqueda IA + resultados (ya hecho)                     | compañero    |
| 2      | Browse por categorías + ContentDetail básico            | compañero    |
| 2      | VideoPlayer nativo funcional                            | compañero    |
| 3      | PDFViewer + AudioPlayer + Login de estudiante           | compañero    |
| 4      | Historial + Favoritos + Calificaciones                  | compañero    |
| 5      | Infinite scroll en browse + skeleton loading + PWA base | compañero    |
