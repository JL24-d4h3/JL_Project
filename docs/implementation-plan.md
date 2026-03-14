# Plan de Implementación - CDN Offline

## Fases del Proyecto

### FASE 1: Setup Inicial y Prototipo Básico (Semana 1-2)

#### 1.1 Configuración del Entorno
```bash
# En el servidor local
□ Instalar PostgreSQL 14+
□ Instalar Redis 7+
□ Instalar Node.js 18+ LTS
□ Configurar estructura de directorios
```

#### 1.2 Base de Datos
```bash
□ Crear base de datos 'cdn_db'
□ Ejecutar scripts de schema (tables, indexes, triggers)
□ Poblar datos de prueba (usuarios, 5-10 videos de muestra)
□ Configurar pg_hba.conf para acceso local
```

#### 1.3 Backend Mínimo Viable
**Stack**: Node.js + Express + TypeScript

```
server/
├── src/
│   ├── index.ts              # Entry point
│   ├── config/
│   │   ├── database.ts       # PostgreSQL connection
│   │   └── redis.ts          # Redis connection
│   ├── routes/
│   │   ├── content.ts        # GET /api/content
│   │   └── stream.ts         # GET /api/stream/:id
│   ├── services/
│   │   ├── contentService.ts # Lógica de negocio
│   │   └── storageService.ts # Filesystem operations
│   ├── middleware/
│   │   └── auth.ts           # Autenticación básica
│   └── models/
│       ├── Content.ts
│       └── User.ts
├── storage/                   # Almacenamiento de archivos
└── package.json
```

**Endpoints Prioritarios**:
- `GET /api/content` - Listar contenido disponible
- `GET /api/content/:id` - Metadatos de contenido específico
- `GET /api/stream/:id` - Stream de video (HTTP Range requests)
- `GET /api/search?q=matematicas` - Búsqueda básica

#### 1.4 Frontend Básico
**Stack**: React + Vite + TypeScript

```
client/
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── Home.tsx          # Pantalla principal
│   │   ├── Search.tsx        # Búsqueda
│   │   └── Player.tsx        # Reproductor de video
│   ├── components/
│   │   ├── ContentCard.tsx   # Card de video/documento
│   │   ├── VideoPlayer.tsx   # Player con controles
│   │   └── SearchBar.tsx
│   ├── services/
│   │   └── api.ts            # Axios config
│   └── types/
│       └── content.ts
└── package.json
```

**Páginas Prioritarias**:
1. Home: Grid de contenido disponible
2. Player: Reproducir video con controles
3. Search: Búsqueda por título/categoría

#### 1.5 Prueba de Concepto
```bash
□ Subir 3 videos de prueba manualmente
□ Acceder desde laptop → buscar "Matemáticas"
□ Reproducir video sin interrupciones
□ Verificar logs de acceso en BD
```

**Criterio de éxito**: Streaming funcional de un video de 100MB a 720p sin buffering excesivo.

---

### FASE 2: Funcionalidades Core (Semana 3-4)

#### 2.1 Sistema de Autenticación
```bash
□ Implementar JWT tokens
□ Login/logout endpoints
□ Middleware de autorización por rol
□ Registro de usuarios (solo por admin)
```

#### 2.2 Upload de Contenido
```bash
□ POST /api/content/upload
□ Multipart form-data handling
□ Validación de tipos de archivo
□ Cálculo de hash (SHA-256)
□ Generación de thumbnail automática (ffmpeg)
□ Transcodificación a múltiples resoluciones
```

**Pipeline de Upload**:
```
1. Recibir archivo → /storage/temp/
2. Validar (tipo, tamaño, virus scan opcional)
3. Calcular hash → verificar duplicados
4. Generar thumbnail (00:05 del video)
5. Transcodificar a 720p, 480p (ffmpeg background job)
6. Insertar metadata en DB
7. Mover a /storage/videos/{id}/
8. Limpiar temp
```

#### 2.3 Sistema de Caché
```bash
□ Redis para metadatos frecuentes
□ Cache-aside pattern
□ TTL de 1 hora para listings
□ Invalidación en updates
```

```javascript
// Ejemplo de caché
async function getContentList(category) {
  const cacheKey = `content:list:${category}`;
  
  // Try cache first
  let data = await redis.get(cacheKey);
  if (data) return JSON.parse(data);
  
  // Cache miss → DB
  data = await db.query('SELECT * FROM content WHERE category = $1', [category]);
  
  // Store in cache
  await redis.setex(cacheKey, 3600, JSON.stringify(data));
  return data;
}
```

#### 2.4 Búsqueda Avanzada
```bash
□ Full-text search con PostgreSQL
□ Filtros: categoría, tipo, tags
□ Ordenamiento: relevancia, fecha, popularidad
□ Paginación
```

#### 2.5 Analytics Básicos
```bash
□ Tracking de vistas (access_log table)
□ Dashboard simple: contenido más visto
□ Estadísticas por categoría
```

---

### FASE 3: Gestión de Almacenamiento (Semana 5)

#### 3.1 Monitoreo de Espacio
```bash
□ Endpoint: GET /api/system/storage
□ Retorna: usado, disponible, total
□ Alertas cuando > 80%
```

#### 3.2 Políticas de Eviction
```bash
□ Implementar LRU algorithm
□ Configuración de threshold (80% por defecto)
□ Dry-run mode para testing
□ Logs detallados de borrados
```

```javascript
// Servicio de eviction
class EvictionService {
  async checkAndEvict() {
    const { used, total } = await getStorageStats();
    const usagePercent = (used / total) * 100;
    
    if (usagePercent > this.threshold) {
      const requiredSpace = total * 0.2; // Libera hasta 60% uso
      await this.evictLRU(requiredSpace);
    }
  }
  
  async evictLRU(targetSpace) {
    // Implementación LRU
    const candidates = await this.getCandidates();
    let freed = 0;
    
    for (let content of candidates) {
      if (freed >= targetSpace) break;
      await this.archiveContent(content.id);
      freed += content.fileSize;
    }
    
    logger.info(`Evicted ${candidates.length} items, freed ${freed} bytes`);
  }
}
```

#### 3.3 Soft Delete
```bash
□ Marcar is_active = false en lugar de DELETE
□ Mover archivo a /storage/archived/
□ Garbage collector para purga final después de 30 días
```

---

### FASE 4: Backups y Recuperación (Semana 6)

#### 4.1 Backup Automático
```bash
□ Script de backup diario (cron)
□ PostgreSQL: pg_dump con compresión
□ Files: rsync incremental
□ Rotación de backups (mantener últimos 7 días)
```

**Cron Job**:
```bash
# /etc/cron.d/cdn-backup
0 2 * * * /opt/cdn/scripts/backup.sh >> /var/log/cdn-backup.log 2>&1
```

#### 4.2 Restore Testing
```bash
□ Script de restore
□ Prueba mensual de restore completo
□ Documentación del proceso
```

#### 4.3 Replicación (Opcional pero recomendado)
```bash
□ PostgreSQL streaming replication
□ Standby server en segunda máquina
□ Automatic failover (Patroni/repmgr)
```

---

### FASE 5: Seguridad y Robustez (Semana 7)

#### 5.1 Seguridad
```bash
□ HTTPS con certificados self-signed (mkcert)
□ Rate limiting (express-rate-limit)
□ Input validation (joi/zod)
□ SQL injection prevention (prepared statements)
□ XSS protection (helmet.js)
□ CORS configurado apropiadamente
```

#### 5.2 Logging y Monitoring
```bash
□ Winston para logs estructurados
□ Rotación de logs diaria
□ Monitoreo de errores (niveles: error, warn, info)
□ Health check endpoint: GET /health
```

#### 5.3 Manejo de Errores
```bash
□ Error handling middleware
□ Retry logic para operaciones I/O
□ Graceful shutdown (SIGTERM/SIGINT)
□ Circuit breaker para dependencias externas
```

---

### FASE 6: Testing y Optimización (Semana 8)

#### 6.1 Testing
Ver [testing-strategy.md](testing-strategy.md) para detalles completos.

**Tests Unitarios**:
- Services: contentService, storageService
- Utilities: hash calculation, validation

**Tests de Integración**:
- API endpoints con DB de test
- Upload flow completo
- Eviction algorithm

**Tests de Carga**:
- 50 usuarios concurrentes
- Streaming simultáneo de 10 videos
- Upload de múltiples archivos

#### 6.2 Optimizaciones
```bash
□ Índices de BD (EXPLAIN ANALYZE queries)
□ Connection pooling (pg-pool)
□ Compresión de responses (gzip)
□ Lazy loading en frontend
□ CDN cache headers apropiados
□ Video seeking optimization (MP4 moov atom)
```

---

### FASE 7: Despliegue y Documentación (Semana 9)

#### 7.1 Dockerización (Opcional pero recomendado)
```dockerfile
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:14
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    
  server:
    build: ./server
    ports:
      - "3000:3000"
    volumes:
      - ./storage:/app/storage
    depends_on:
      - db
      - redis
  
  client:
    build: ./client
    ports:
      - "5173:80"
```

#### 7.2 Documentación
```bash
□ README completo con setup instructions
□ API documentation (Swagger/OpenAPI)
□ Guía de usuario final
□ Troubleshooting guide
□ Diagramas de arquitectura actualizados
```

#### 7.3 Deploy en Servidor Local
```bash
□ Configurar systemd services
□ Configurar nginx reverse proxy
□ Setup de red local (DHCP, DNS)
□ Pruebas end-to-end con dispositivos reales
```

---

## Stack Tecnológico Recomendado

### Backend
- **Runtime**: Node.js 18 LTS
- **Framework**: Express.js
- **Language**: TypeScript
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **ORM**: Knex.js o TypeORM (opcional)
- **Video Processing**: ffmpeg
- **Testing**: Jest + Supertest

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Router**: React Router v6
- **State**: Zustand o Context API
- **HTTP Client**: Axios
- **Video Player**: Video.js o react-player
- **UI**: Tailwind CSS + shadcn/ui

### DevOps
- **Containerization**: Docker + Docker Compose
- **Process Manager**: PM2
- **Reverse Proxy**: Nginx
- **Monitoring**: Custom dashboard + logs

---

## Estimación de Recursos

### Hardware Mínimo (Servidor Local)
- **CPU**: 4 cores (Intel i5 o equivalente)
- **RAM**: 8 GB (16 GB recomendado)
- **Almacenamiento**: 
  - 500 GB HDD para contenido
  - 50 GB SSD para OS + DB
- **Network**: Gigabit ethernet + WiFi AC

### Software
- **OS**: Ubuntu Server 22.04 LTS
- Todo el software es gratuito y open-source

---

## Prioridades y MVP

**Definición de MVP** (Mínimo Producto Viable):
1. ✅ Streaming de video funcional
2. ✅ Búsqueda básica por título
3. ✅ Upload de contenido (admin)
4. ✅ Autenticación básica (roles)
5. ✅ Listado de contenido por categoría

**Post-MVP** (priorizados):
1. Analytics y estadísticas
2. Sistema de backups automático
3. Eviction policies
4. Frontend pulido (UX mejorado)
5. Tests automatizados

---

## Cronograma Visual

```
Semana 1-2: [████████████████] Setup + Prototipo
Semana 3-4: [████████████████] Features Core
Semana 5:   [███████████████░] Gestión Storage
Semana 6:   [██████████░░░░░░] Backups
Semana 7:   [█████████░░░░░░░] Seguridad
Semana 8:   [████████░░░░░░░░] Testing
Semana 9:   [███████░░░░░░░░░] Deploy

MVP: Semana 4
Producción: Semana 9
```

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Espacio en disco insuficiente | Alta | Alto | Eviction policies + monitoreo |
| Problemas de red WiFi | Media | Alto | QoS + múltiples APs |
| Corrupción de archivos | Baja | Alto | Checksums + backups |
| Sobrecarga del servidor | Media | Medio | Rate limiting + cache |
| Complejidad de ffmpeg | Media | Medio | Usar presets probados |

---

## Siguiente Paso Inmediato

**Comenzar con Setup Inicial**:
1. Preparar servidor (instalar PostgreSQL, Node.js, Redis)
2. Crear estructura de directorios del proyecto
3. Inicializar repositorio Git
4. Setup base de datos (schema)

¿Deseas que genere los scripts de inicialización y la estructura del proyecto?
