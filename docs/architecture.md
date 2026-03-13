# Arquitectura de CDN Offline

## 1. Visión General del Sistema

### 1.1 Concepto
Sistema distribuido para entrega de contenido educativo en redes locales WiFi sin conectividad a Internet. Similar a un sistema de archivos distribuido con capacidades de CDN.

### 1.2 Flujo Principal
```
Usuario (Laptop/Tablet) 
    → Request HTTP ("Números Reales")
    → WiFi AP / Router (mesh network)
    → Servidor Local (Content Server)
    → Almacenamiento Local (Media Storage)
    → Response: Stream de video/archivo
```

## 2. Componentes de la Arquitectura

### 2.1 Capa de Cliente (Frontend)
- **Tecnología**: React + React Router
- **Responsabilidades**:
  - Interfaz de búsqueda y navegación de contenido
  - Player de video integrado (Video.js o similar)
  - Visor de PDFs
  - Gestión de favoritos y progreso local (localStorage)
  - Manejo de desconexiones temporales
  
### 2.2 Capa de Red (Network Layer)
- **Access Points (APs)**: 
  - WiFi 802.11n/ac
  - DHCP para asignación de IPs
  - DNS local para resolver nombres
- **Router/Gateway**:
  - Ruteo interno entre subredes
  - Firewall local
  - QoS para priorizar streaming

### 2.3 Capa de Servidor (Backend)
- **Tecnología Recomendada**: Node.js + Express o Python + FastAPI
- **Componentes**:
  
  a) **API Server**:
     - REST API para búsqueda y entrega de contenido
     - WebSocket para estado en tiempo real
     - Rate limiting para controlar carga
  
  b) **Content Storage Service**:
     - Sistema de archivos estructurado
     - Metadatos en base de datos
     - Binarios en filesystem
  
  c) **Cache Layer** (Redis):
     - Caché de metadatos frecuentes
     - Caché de thumbnails
     - Lista de contenido disponible
  
  d) **Sync Service**:
     - Sincronización con otros nodos (futuro)
     - Replicación de contenido popular
     - Detección de conflictos

### 2.4 Capa de Almacenamiento

#### Base de Datos: **PostgreSQL** (recomendado)
Razones:
- ✅ ACID compliant (crucial para consistencia)
- ✅ Soporte robusto para JSON (metadatos flexibles)
- ✅ Replicación integrada (para expansión futura)
- ✅ Full-text search (búsqueda de contenido)
- ✅ Funciona bien offline
- ✅ Backups y restore probados

**Alternativa**: SQLite para deployments muy pequeños

#### Almacenamiento de Archivos
```
/storage/
├── videos/           # Videos (.mp4, .webm, .mkv, .avi, etc.)
│   └── {hash}.mp4
├── audio/            # Archivos de audio (.mp3, .wav, .flac, .aac, etc.)
│   └── {hash}.mp3
├── images/           # Imágenes (.jpg, .png, .gif, .webp, etc.)
│   └── {hash}.jpg
├── code/             # Código fuente (.py, .js, .java, .cpp, etc.)
│   └── {hash}.py
├── documents/        # Documentos (.pdf, .docx, .xlsx, .pptx, etc.)
│   └── {hash}.pdf
├── thumbnails/       # Miniaturas generadas automáticamente
│   └── {hash}.jpg
├── temp/             # Uploads temporales (pending approval)
│   └── {upload}.tmp
└── archived/         # Contenido archivado (soft delete)
    └── {hash}.bak

Nota: Los archivos se nombran por su hash SHA-256, no por su título.
Esto garantiza unicidad y permite detección de duplicados.
```

## 3. Modelo de Datos

### 3.1 Esquema Principal

```sql
-- Usuarios del sistema
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student', -- student, teacher, admin
    created_at TIMESTAMP DEFAULT NOW(),
    last_access TIMESTAMP
);

-- Contenido educativo
CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL, -- video, audio, image, pdf, document, code
    category VARCHAR(100), -- matematicas, ciencias, etc.
    tags TEXT[], -- array de tags para búsqueda
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64), -- SHA-256 para verificar integridad
    duration_seconds INT, -- para videos y audio
    thumbnail_path VARCHAR(1000),
    quality_versions JSONB, -- {720p: path, 480p: path}
    metadata JSONB, -- flexibilidad para datos adicionales
    access_count INT DEFAULT 0,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_content_category ON content(category);
CREATE INDEX idx_content_tags ON content USING GIN(tags);
CREATE INDEX idx_content_type ON content(type);
CREATE INDEX idx_content_search ON content USING GIN(to_tsvector('spanish', title || ' ' || description));

-- Historial de acceso
CREATE TABLE access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id),
    user_id UUID REFERENCES users(id),
    accessed_at TIMESTAMP DEFAULT NOW(),
    device_info JSONB,
    duration_watched INT -- segundos vistos
);

-- Permisos detallados
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    content_id UUID REFERENCES content(id),
    can_read BOOLEAN DEFAULT true,
    can_update BOOLEAN DEFAULT false,
    can_delete BOOLEAN DEFAULT false,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW()
);

-- Cache de replicación (para nodos múltiples)
CREATE TABLE replication_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id),
    node_id VARCHAR(100),
    status VARCHAR(50), -- pending, synced, failed
    last_sync TIMESTAMP,
    priority INT DEFAULT 0
);
```

## 4. Políticas de Borrado y Gestión de Espacio

### 4.1 Estrategias de Eviction (Borrado)

**LRU (Least Recently Used)** - Recomendado para fase inicial
```
Borra contenido menos accedido recientemente cuando:
- Disco > 80% capacidad
- Necesitas espacio para nuevo contenido prioritario
```

**LFU (Least Frequently Used)** - Para fase madura
```
Borra contenido menos popular basado en:
- access_count
- ponderado por fecha
```

**TTL (Time To Live)** - Para contenido temporal
```
Contenido con fecha de expiración automática
Ej: avisos, eventos específicos
```

### 4.2 Implementación
```javascript
// Algoritmo híbrido sugerido
function evictContent(requiredSpace) {
  const candidates = db.query(`
    SELECT id, file_size, access_count, 
           EXTRACT(EPOCH FROM NOW() - MAX(accessed_at)) as seconds_since_access
    FROM content c
    LEFT JOIN access_log al ON c.id = al.content_id
    WHERE is_active = true AND priority < 5
    GROUP BY c.id
    ORDER BY 
      (access_count / (seconds_since_access / 86400.0)) ASC -- score
    LIMIT 100
  `);
  
  let freedSpace = 0;
  for (let content of candidates) {
    if (freedSpace >= requiredSpace) break;
    archiveToBackup(content.id);
    deleteContent(content.id);
    freedSpace += content.file_size;
  }
}
```

## 5. Manejo de Conflictos

### 5.1 Tipos de Conflictos

1. **Escritura Concurrente**: 
   - Dos admins actualizan el mismo contenido
   - **Solución**: Versioning + Last-Write-Wins con timestamp

2. **Conflicto de Espacio**: 
   - Múltiples cargas agotando espacio
   - **Solución**: Queue + validación previa de espacio

3. **Sincronización Entre Nodos**:
   - Mismo contenido diferente versión en nodos
   - **Solución**: Vector clocks o hashes de contenido

### 5.2 Estrategia de Resolución

```
1. Optimistic Locking:
   UPDATE content 
   SET ... , updated_at = NOW(), version = version + 1
   WHERE id = ? AND version = ?
   
2. Si falla → conflict detectado
3. Aplicar política: merge, user-choice, o LWW
```

## 6. Sistema de Backups

### 6.1 Niveles de Backup

**Tier 1: Hot Backup** (inmediato)
- PostgreSQL WAL streaming
- Réplica en segundo disco/servidor
- RTO: minutos

**Tier 2: Warm Backup** (diario)
- Snapshot completo de DB
- Rsync de archivos a storage externo
- RTO: horas

**Tier 3: Cold Backup** (semanal)
- Backup completo comprimido
- Storage offline (disco externo)
- RTO: días

### 6.2 Implementación

```bash
# Script de backup diario
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)

# Database
pg_dump cdn_db | gzip > /backups/db_$DATE.sql.gz

# Files (incremental)
rsync -av --link-dest=/backups/latest \
  /storage/ /backups/files_$DATE/

# Actualizar symlink
ln -sfn /backups/files_$DATE /backups/latest

# Limpiar backups antiguos (>30 días)
find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

## 7. Control de Acceso (RBAC)

### 7.1 Roles

| Rol | Permisos |
|-----|----------|
| **Student** | Leer contenido autorizado, marcar favoritos |
| **Teacher** | Student + subir contenido, editar sus uploads |
| **Admin** | Teacher + gestionar usuarios, borrar cualquier contenido, backups |
| **SuperAdmin** | Admin + configuración de sistema, gestión de nodos |

### 7.2 Middleware de Autorización

```javascript
function authorize(requiredRole) {
  return async (req, res, next) => {
    const user = await getUserFromToken(req.headers.authorization);
    
    const roleHierarchy = {
      student: 1,
      teacher: 2,
      admin: 3,
      superadmin: 4
    };
    
    if (roleHierarchy[user.role] >= roleHierarchy[requiredRole]) {
      req.user = user;
      next();
    } else {
      res.status(403).json({ error: 'Insufficient permissions' });
    }
  };
}

// Uso
app.delete('/api/content/:id', authorize('admin'), deleteContent);
```

## 8. Similitud con Sistema de Archivos

**Sí, es muy similar a un explorador de archivos distribuido**:

| Concepto | Explorador de Archivos | Nuestra CDN |
|----------|----------------------|-------------|
| Carpetas | Directorios jerárquicos | Categorías y tags |
| Archivos | Files en disco | Contenido (videos, PDFs) |
| Metadatos | Fecha, tamaño, permisos | Título, descripción, duración, tags |
| Búsqueda | Buscar por nombre | Full-text search + filtros |
| Permisos | rwx por usuario/grupo | RBAC con roles |
| Cache | OS file cache | Redis + CDN cache |
| Papelera | Carpeta temp antes de borrar | Soft delete (is_active=false) |

**Diferencias clave**:
- CDN tiene streaming optimizado
- Múltiples versiones de calidad
- Analytics de uso
- Priorización de contenido popular
- Replicación entre nodos

## 9. Arquitectura Física de Red

```
                    ┌─────────────────┐
                    │  Servidor Local │
                    │   (PC Linux)    │
                    │                 │
                    │  - PostgreSQL   │
                    │  - Redis        │
                    │  - Node.js API  │
                    │  - File Storage │
                    └────────┬────────┘
                             │ eth0/WiFi
                             │
                    ┌────────┴────────┐
                    │  Router/Gateway │
                    │  192.168.1.1    │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────┴─────┐     ┌─────┴─────┐     ┌─────┴─────┐
    │  AP #1    │     │  AP #2    │     │  AP #3    │
    │ Zona A    │     │ Zona B    │     │ Zona C    │
    └─────┬─────┘     └─────┬─────┘     └─────┬─────┘
          │                 │                   │
    ┌─────┴─────┐     ┌─────┴─────┐     ┌─────┴─────┐
    │ Clientes  │     │ Clientes  │     │ Clientes  │
    │ Laptops   │     │ Tablets   │     │ Phones    │
    └───────────┘     └───────────┘     └───────────┘
```

**Consideraciones**:
- Subnet: 192.168.1.0/24
- DNS local: Resolver nombres como `cdn.local`
- DHCP: Asignación automática de IPs
- QoS: Priorizar streaming sobre descargas

## 10. Próximos Pasos

Ver [implementation-plan.md](implementation-plan.md) para el plan detallado de desarrollo.
