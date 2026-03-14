# Flujo de Aprobación de Contenido

## Roles y Permisos

### Roles del Sistema

| Rol | Descripción | Permisos |
|-----|-------------|----------|
| **student** | Estudiante | Solo lectura de contenido activo |
| **teacher** | Docente/Sender | Subir contenido, ver sus propios envíos |
| **admin** | Administrador | Aprobar/rechazar contenido, gestionar usuarios |
| **superadmin** | Superadministrador | Control total del sistema |

## Estados del Contenido

El contenido puede estar en los siguientes estados:

| Estado | Descripción | Visible para |
|--------|-------------|--------------|
| **pending** | Pendiente de revisión | Creador (teacher) y admins |
| **active** | Aprobado y publicado | Todos los usuarios |
| **rejected** | Rechazado | Solo creador (teacher) |
| **deleted** | Eliminado (soft delete) | Nadie (solo en BD) |

## Flujo de Trabajo

### 1. Subida de Contenido (Teacher/Sender)

```
┌───────────────┐
│ Teacher sube  │
│   archivo     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Validación   │
│  - Tipo       │
│  - Tamaño     │
│  - Duplicados │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Procesamiento │
│  - Hash       │
│  - Metadata   │
│  - Thumbnail  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Estado:       │
│  PENDING      │
│ (en temp/)    │
└───────────────┘
```

**Ubicación del archivo**: `storage/temp/{nombre_temporal}`

**Quién lo hace**: teacher, admin, superadmin

**Dónde se ve**:
- Teacher: En "Mis Envíos" (con estado "Pendiente")
- Admin: En "Cola de Revisión"

### 2. Revisión y Aprobación (Admin)

El administrador revisa el contenido pendiente y tiene **3 opciones**:

#### Opción A: APROBAR

```
┌───────────────┐
│  Admin hace   │
│    APPROVE    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Archivo se    │
│ mueve de      │
│ temp/ a       │
│ carpeta final │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Estado:       │
│  ACTIVE       │
└───────────────┘
```

**Resultado**: El contenido se publica y es visible para todos

**Ubicación final**:
- Videos: `storage/videos/{archivo}`
- Imágenes: `storage/images/{archivo}`
- Audio: `storage/audio/{archivo}`
- Código: `storage/code/{archivo}`
- Documentos: `storage/documents/{archivo}`

#### Opción B: CURAR (Curate)

```
┌───────────────┐
│  Admin hace   │
│    CURATE     │
│  (edita meta) │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Actualiza:    │
│ - Título      │
│ - Descripción │
│ - Categoría   │
│ - Featured    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Mueve archivo │
│ a carpeta     │
│ final         │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Estado:       │
│  ACTIVE       │
└───────────────┘
```

**Resultado**: El contenido se publica CON metadatos mejorados

#### Opción C: RECHAZAR

```
┌───────────────┐
│  Admin hace   │
│    REJECT     │
│ (con razón)   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Archivo se    │
│ ELIMINA de    │
│ temp/         │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Estado:       │
│  REJECTED     │
│ (solo en BD)  │
└───────────────┘
```

**Resultado**: El archivo se elimina del disco. El teacher ve el rechazo con la razón.

**Quién lo hace**: admin, superadmin

**Dónde se hace**: Panel Admin > Cola de Revisión > Click en ítem > Botones de acción

### 3. Visualización del Contenido

#### Para Teachers (Sender)

**Ubicación**: "Mis Envíos"

Pueden ver TODOS sus archivos con sus estados:
- ⏳ Pendiente (amarillo)
- ✅ Aprobado (verde)
- ❌ Rechazado (rojo) - incluye razón de rechazo

#### Para Admins

**Ubicación**: "Cola de Revisión"

Ven solo archivos en estado **pending** que requieren acción.

**Ubicación**: "Contenido"

Ven todos los archivos **active** (publicados).

#### Para Students

**Ubicación**: Interfaz del viewer/buscador

Ven solo archivos **active**.

## Matriz de Permisos

| Acción | Student | Teacher | Admin | Superadmin |
|--------|---------|---------|-------|-----------|
| Ver contenido activo | ✅ | ✅ | ✅ | ✅ |
| Subir contenido | ❌ | ✅ | ✅ | ✅ |
| Ver mis envíos | ❌ | ✅ (propios) | ✅ (todos) | ✅ (todos) |
| Aprobar contenido | ❌ | ❌ | ✅ | ✅ |
| Rechazar contenido | ❌ | ❌ | ✅ | ✅ |
| Curar metadata | ❌ | ❌ | ✅ | ✅ |
| Eliminar contenido | ❌ | ✅ (propio) | ✅ (todo) | ✅ (todo) |
| Gestionar usuarios | ❌ | ❌ | ✅ | ✅ |
| Ver estadísticas | ❌ | ✅ (propias) | ✅ (todas) | ✅ (todas) |

## Preguntas Frecuentes

### ¿Por qué no veo mi archivo después de subirlo?

Los archivos subidos quedan en estado **pending** hasta que un administrador los apruebe.

- **Teacher**: Revisa "Mis Envíos" para ver el estado
- **Admin**: Ve a "Cola de Revisión" para aprobar

### ¿Cuánto demora la aprobación?

Depende de la disponibilidad del administrador. El proceso técnico es instantáneo, pero requiere revisión humana.

### ¿Qué pasa si mi archivo es rechazado?

El archivo se elimina del sistema y recibes una notificación con la razón del rechazo. Puedes volver a subirlo corrigiendo los problemas indicados.

### ¿Puedo editar mi contenido después de aprobado?

No directamente. El teacher debe contactar al administrador para solicitar cambios. El admin puede editar metadata desde el panel de administración.

### ¿Los administradores pueden ver todos los archivos?

Sí, los administradores pueden ver:
- Todos los archivos pendientes (Cola de Revisión)
- Todos los archivos activos (Contenido)
- Todos los envíos de todos los usuarios

## Diagrama Completo del Flujo

```
┌─────────────┐
│   TEACHER   │
│   sube      │
│  archivo    │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│   VALIDACIÓN     │
│ ¿tipo correcto?  │
│ ¿no duplicado?   │
│ ¿tamaño ok?      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  PROCESAMIENTO   │
│  - Calcular hash │
│  - Extraer meta  │
│  - Gen thumbnail │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  storage/temp/   │
│ Status: PENDING  │
└──────┬───────────┘
       │
       ├─────────────────────┐
       │                     │
       ▼                     ▼
┌──────────────┐     ┌──────────────┐
│   Teacher    │     │    Admin     │
│ ve en "Mis   │     │  ve en "Cola │
│   Envíos"    │     │  de Revisión"│
└──────────────┘     └──────┬───────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐
          │ APPROVE │ │  CURATE │ │ REJECT  │
          └────┬────┘ └────┬────┘ └────┬────┘
               │           │           │
               ▼           ▼           ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ Mueve a    │ │ Edita meta │ │ Elimina de │
       │storage/{t} │ │+ Mueve     │ │   temp/    │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │              │              │
             ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │  ACTIVE    │ │  ACTIVE    │ │  REJECTED  │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │              │              │
             ▼              ▼              ▼
       ┌────────────────────────┐    ┌────────────┐
       │ Visible para todos     │    │ Solo BD    │
       │ en Contenido/Búsqueda  │    │ Teacher ve │
       └────────────────────────┘    │  razón     │
                                     └────────────┘
```

## Consideraciones Técnicas

### Almacenamiento de Archivos

1. **Archivos temporales** (`temp/`):
   - Se guardan aquí durante la validación
   - Se eliminan después de aprobar o rechazar
   - Se limpian automáticamente si quedan huérfanos

2. **Archivos permanentes**:
   - Organizados por tipo en carpetas específicas
   - Nombrados por hash SHA-256 para evitar duplicados
   - Incluyen metadata en BD con referencia al archivo

### Base de Datos

El campo `status` en la tabla `content` puede ser:
- `'pending'`: Enviado, esperando revisión
- `'active'`: Aprobado y visible
- `'rejected'`: Rechazado (archivo eliminado del disco)

El campo `deleted_at`:
- `NULL`: Contenido existente
- `TIMESTAMP`: Soft delete (no se muestra pero se conserva registro)

---

**Última actualización**: 2026-03-13
