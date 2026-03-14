# Resumen del Proyecto CDN Offline

> **Contexto**: Proyecto de investigación del grupo GTR de la PUCP (Pontificia Universidad Católica del Perú). Fecha de revisión: febrero 2026.

---

## ¿Qué es?

Una **CDN (Content Delivery Network) offline** pensada para llevar contenido educativo digital (videos, PDFs, audios) a escuelas rurales de Perú donde Internet no es confiable o no existe.

La analogía más directa: es como tener **YouTube + Google Drive funcionando dentro de la escuela**, sin necesidad de salir a Internet. Un servidor físico en la institución entrega el contenido a través de la red WiFi local.

---

## El problema que resuelve

Las zonas rurales del Perú tienen acceso muy limitado o nulo a Internet. Los docentes no pueden usar plataformas educativas en línea (YouTube, Classroom, etc.) con sus alumnos. Este proyecto lleva esa infraestructura "adentro" de la escuela.

---

## Flujo de uso (simplificado)

```
Estudiante (laptop/tablet)
        ↓  WiFi local
   Access Point (router)
        ↓  Ethernet
  Servidor físico local
  └─ Videos, PDFs, BD, API
```

1. El estudiante busca "Números Reales" desde su navegador.
2. La petición viaja por WiFi al servidor local (no a Internet).
3. El servidor busca el video en su almacenamiento y lo transmite.
4. El video se reproduce en segundos. Todo dentro de la red de la escuela.

---

## Estado real del código

El proyecto está en **fase de desarrollo temprano**. Hay una separación clara entre lo que está construido y lo que es documentación/planificación:

### Backend (`server/`) — Avanzado
El servidor está implementado en **Node.js + Express + TypeScript** y ya tiene:

| Módulo | Estado | Descripción |
|--------|--------|-------------|
| `authController.ts` | Funcional | Login con JWT, bloqueo por intentos fallidos, sesiones en DB |
| `contentController.ts` | Funcional | Listado de contenido con filtros, paginación, full-text search en español |
| `streamController.ts` | Funcional | Streaming de video con HTTP Range Requests (como lo hace YouTube) |
| `uploadController.ts` | Funcional | Subida de archivos, detección de duplicados por hash, procesamiento asíncrono |
| `ffmpegService.ts` | Funcional | Extracción de metadata, generación de thumbnails, transcodificación |
| `storageService.ts` | Funcional | Gestión del sistema de archivos, cálculo de hashes |
| `auth.ts` (middleware) | Funcional | Verificación JWT + control de roles |

### Frontend (`client/`) — Solo boilerplate
El cliente es un proyecto **React + TypeScript + Vite + Tailwind CSS** recién inicializado. Actualmente solo muestra una pantalla con el nombre del proyecto y un contador de prueba. **La interfaz de usuario real aún no existe.**

---

## Stack tecnológico

| Capa | Tecnología | Para qué |
|------|-----------|----------|
| Frontend | React 18 + TypeScript + Vite | Interfaz de usuario (pendiente de desarrollar) |
| Backend | Node.js + Express + TypeScript | API REST, lógica de negocio |
| Base de datos | PostgreSQL | Usuarios, contenido, categorías, sesiones, logs |
| Caché | Redis | Acelerar consultas frecuentes (listas de contenido) |
| Procesamiento de video | FFmpeg | Transcodificación, thumbnails, extracción de metadata |
| Autenticación | JWT + bcrypt | Sesiones seguras, contraseñas hasheadas |
| Estilo | Tailwind CSS | UI responsiva |

Todo es **software libre, costo $0 en licencias**.

---

## Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────┐
│                    RED LOCAL (WiFi)                       │
│                                                           │
│  [Laptops/Tablets]  ──────►  [Access Points]             │
│                                      │                   │
│                              [SERVIDOR LOCAL]             │
│                              ┌───────────────┐            │
│                              │  React App    │ :5173     │
│                              │  Express API  │ :3000     │
│                              │  PostgreSQL   │ :5432     │
│                              │  Redis        │ :6379     │
│                              │  Storage      │ /storage  │
│                              └───────────────┘            │
└──────────────────────────────────────────────────────────┘
```

---

## Roles de usuario

El sistema maneja 4 niveles de acceso definidos en el código:

| Rol | Puede hacer |
|-----|-------------|
| `student` | Buscar y ver contenido |
| `teacher` | Subir y gestionar su propio contenido |
| `admin` | Gestionar usuarios y categorías |
| `superadmin` | Control total del sistema |

---

## Características técnicas destacadas

- **HTTP Range Requests**: el streaming de video funciona igual que en plataformas comerciales — el usuario puede saltar a cualquier punto sin descargar el archivo completo.
- **Full-text search en español**: la búsqueda usa `to_tsvector('spanish', ...)` de PostgreSQL, con soporte para tildes y variaciones del idioma.
- **Detección de duplicados**: al subir un archivo se calcula su hash SHA-256; si ya existe en el servidor, no se duplica.
- **Caché en Redis**: las listas de contenido se cachean automáticamente para respuestas más rápidas.
- **Procesamiento asíncrono**: los uploads no bloquean al usuario; el video se procesa en segundo plano y pasa de estado `processing` a `active`.
- **Logs de acceso**: cada vez que alguien reproduce un video se registra en `access_log` (para estadísticas de uso).
- **Seguridad básica**: bloqueo de cuenta tras 5 intentos fallidos (15 min), headers de seguridad con `helmet`, sesiones en DB verificadas en cada request.

---

## Estructura de almacenamiento

```
storage/
├── videos/        ← Videos subidos (mp4, mkv, etc.)
├── documents/     ← PDFs y documentos
├── thumbnails/    ← Imágenes de previsualización (generadas por FFmpeg)
├── temp/          ← Archivos en proceso de subida
└── archived/      ← Contenido archivado (no eliminado)
```

---

## Hardware destino

El sistema está diseñado para ejecutarse en hardware modesto:

| Item | Especificación mínima |
|------|-----------------------|
| CPU | 4 núcleos |
| RAM | 8 GB |
| Almacenamiento | 500 GB HDD |
| Red | 100 Mbps LAN |
| Costo estimado (hardware usado) | ~$450 USD |
| Costo operativo anual | ~$100 USD (electricidad + mantenimiento) |

---

## ¿A qué apunta el proyecto?

El objetivo final es tener un sistema **listo para desplegar en escuelas rurales** que:

1. Un técnico pueda instalar en 1–2 horas con una guía básica.
2. Los docentes puedan usar sin capacitación técnica (subir videos como si fuera Google Drive).
3. Los estudiantes puedan usar desde cualquier dispositivo con navegador web.
4. Funcione de forma autónoma: backups automáticos, limpieza de espacio, sin depender de soporte externo.

El plan de implementación divide el desarrollo en **9 semanas**, cubriendo desde la base de datos y API hasta el frontend completo y el despliegue en hardware real.

---

## Lo que falta por construir

- Interfaz de usuario completa (frontend está en blanco)
- Panel de administración
- Sistema de backups automáticos
- Sincronización entre múltiples servidores (para redes con más de un nodo)
- App móvil (mencionada en el roadmap como fase futura)
- Scripts de instalación automatizada

---

## En una línea

> Un servidor local que convierte cualquier escuela rural en un mini-YouTube educativo, sin necesidad de Internet, construido con tecnología web estándar y hardware de bajo costo.
