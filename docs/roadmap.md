# Roadmap y Hitos del Proyecto

## Resumen Ejecutivo

**Objetivo**: CDN offline funcional en 9 semanas
**Estado Actual**: 📋 Planificación completa
**Próximo Hito**: 🔨 Inicio de desarrollo (Semana 1)

---

## Timeline de Desarrollo

```
Mes 1: Setup y Prototipo
[████████████░░░░░░░░] 60% planeado

Mes 2: Features Core y Storage
[██████░░░░░░░░░░░░░░] 30% planeado

Mes 3: Testing y Deploy
[███░░░░░░░░░░░░░░░░░] 15% planeado

MVP: Final de Mes 2
Producción: Final de Mes 3
```

---

## FASE 0: Planificación ✅ COMPLETO

### Entregables
- [x] Documento de arquitectura
- [x] Diseño de base de datos
- [x] Plan de implementación
- [x] Estrategia de testing
- [x] Diagramas de arquitectura
- [x] FAQ técnico

**Duración**: 2 días
**Estado**: ✅ Completado

---

## FASE 1: Setup Inicial y Prototipo 🔨 PRÓXIMO

### Semana 1: Infraestructura Base

#### Objetivos
Set up del entorno de desarrollo y estructura del proyecto.

#### Tareas
- [ ] 1.1 Configurar servidor (Ubuntu Server)
  - Instalar PostgreSQL 14
  - Instalar Redis 7
  - Instalar Node.js 18 LTS
  - Instalar FFmpeg
  - Configurar firewall (ufw)

- [ ] 1.2 Inicializar proyecto
  - Crear repositorio Git
  - Setup estructura de directorios
  - Configurar TypeScript (backend)
  - Configurar ESLint + Prettier

- [ ] 1.3 Base de datos
  - Ejecutar scripts de schema
  - Crear migrations (Knex.js)
  - Seed data de prueba
  - Verificar conexión

- [ ] 1.4 Backend básico
  - Express server con TypeScript
  - Conexión a PostgreSQL
  - Conexión a Redis
  - Health check endpoint

**Criterio de éxito**:
```bash
curl http://localhost:3000/health
# Response: {"status": "ok", "db": "connected", "redis": "connected"}
```

**Duración**: 3-4 días
**Responsable**: Developer
**Bloqueadores potenciales**: Problemas con instalación de dependencias

---

### Semana 2: Streaming MVP

#### Objetivos
Demostrar streaming de video funcional de extremo a extremo.

#### Tareas
- [ ] 2.1 Backend - Content Service
  - Modelo de Content
  - GET /api/content (listar)
  - GET /api/content/:id (detalle)
  - GET /api/stream/:id (streaming con HTTP Range)

- [ ] 2.2 Frontend - Setup React
  - Crear proyecto con Vite
  - Configurar Tailwind CSS
  - Setup routing (React Router)

- [ ] 2.3 Frontend - UI Básica
  - Home page: Grid de videos
  - Player page: Reproductor simple
  - Video.js integration

- [ ] 2.4 Testing manual
  - Subir 3 videos manualmente a /storage/
  - Insertar metadata en DB
  - Verificar streaming funciona

**Demo Video**:
```
1. Abrir http://192.168.1.100:5173
2. Ver lista de 3 videos
3. Click en "Números Reales"
4. Video reproduce sin lag
5. Seeking funciona (saltar a minuto 5)
```

**Criterio de éxito**: Streaming fluido de video 720p sin buffering excesivo (<3s inicial)

**Duración**: 4-5 días
**Dependencias**: Fase 1.1-1.4 completas

---

## FASE 2: Features Core 🚧 PENDIENTE

### Semana 3: Autenticación y Permisos

#### Objetivos
Sistema seguro de login y control de acceso.

#### Tareas
- [ ] 3.1 Backend - Auth Service
  - POST /api/auth/register (solo admin puede crear users)
  - POST /api/auth/login (JWT tokens)
  - Middleware de autenticación
  - Middleware de autorización (RBAC)

- [ ] 3.2 Frontend - Auth UI
  - Login page
  - Manejo de tokens (localStorage)
  - Protected routes
  - Logout

- [ ] 3.3 Permissions
  - Implementar checks de permisos en endpoints
  - Admin puede: subir, editar, borrar
  - Teacher puede: subir, editar sus propios videos
  - Student puede: solo ver

- [ ] 3.4 Testing
  - Unit tests para auth middleware
  - Integration tests para login flow
  - E2E test: login → ver video → logout

**Criterio de éxito**: Student no puede acceder a /admin, Teacher no puede borrar videos de otros

**Duración**: 4-5 días

---

### Semana 4: Upload y Búsqueda

#### Objetivos
Teachers pueden subir contenido; usuarios pueden buscar eficientemente.

#### Tareas
- [ ] 4.1 Backend - Upload
  - POST /api/content/upload (multipart)
  - Validación de archivos
  - Cálculo de hash (SHA-256)
  - Almacenamiento en /storage/temp/

- [ ] 4.2 Backend - Transcode Worker
  - Setup Bull queue
  - Worker: FFmpeg transcoding (720p, 480p)
  - Generación de thumbnail
  - Actualización de DB al completar

- [ ] 4.3 Backend - Search
  - GET /api/search?q=query
  - Full-text search con PostgreSQL
  - Filtros: category, type, tags
  - Paginación

- [ ] 4.4 Frontend
  - Upload page (admin/teacher only)
  - Progress bar para upload
  - Search bar en header
  - Search results page

**Demo Video**:
```
1. Login como teacher
2. Ir a /upload
3. Subir video "Geometría.mp4"
4. Ver progreso de transcoding
5. Buscar "geometría"
6. Ver resultado, reproducir video
```

**Criterio de éxito**: Upload de video de 100MB completa en <5 min; búsqueda retorna resultados en <200ms

**Duración**: 5-6 días

---

## FASE 3: Gestión de Almacenamiento ⏳ PENDIENTE

### Semana 5: Eviction y Monitoreo

#### Objetivos
Sistema automático de gestión de espacio en disco.

#### Tareas
- [ ] 5.1 Storage Monitoring
  - GET /api/system/storage (uso actual)
  - Service para monitorear disco cada hora
  - Alertas cuando > 80%

- [ ] 5.2 Eviction Service
  - Implementar algoritmo LRU
  - Query de candidatos (v_eviction_candidates)
  - Archive antes de delete
  - Logging en eviction_log

- [ ] 5.3 Soft Delete
  - UPDATE deleted_at en lugar de DELETE
  - Mover archivo a /storage/archived/
  - Garbage collector (cron job)

- [ ] 5.4 Frontend - Admin Dashboard
  - Mostrar uso de disco (chart)
  - Lista de contenido a eliminar
  - Botón "Ejecutar Eviction"
  - Logs de evictions recientes

**Criterio de éxito**: 
- Cuando disco > 80%, eviction libera espacio automáticamente
- Archivos de alta prioridad nunca se eliminan

**Duración**: 4 días

---

## FASE 4: Backups y Seguridad 🔒 PENDIENTE

### Semana 6: Backups

#### Objetivos
Sistema robusto de backups y recuperación.

#### Tareas
- [ ] 6.1 Backup Automation
  - Script: backup-daily.sh
  - PostgreSQL: pg_dump con gzip
  - Files: rsync incremental
  - Rotación (mantener 7 días)

- [ ] 6.2 Restore Process
  - Script: restore.sh
  - Documentación del proceso
  - Testing de restore completo

- [ ] 6.3 Configurar Cron
  - Backup diario a las 2 AM
  - Monitoreo de éxito/falla
  - Notificación a admin si falla

- [ ] 6.4 (Opcional) Replicación
  - Setup PostgreSQL streaming replication
  - Servidor standby en segunda máquina

**Criterio de éxito**: Restore completo de 100GB en < 4 horas

**Duración**: 3 días

---

### Semana 7: Seguridad y Robustez

#### Objetivos
Hardening del sistema para producción.

#### Tareas
- [ ] 7.1 Security Hardening
  - HTTPS con certificados self-signed
  - Helmet.js (security headers)
  - Rate limiting (express-rate-limit)
  - Input validation (zod)
  - CORS configurado

- [ ] 7.2 Logging
  - Winston para logs estructurados
  - Rotación de logs (diaria)
  - Niveles: error, warn, info, debug

- [ ] 7.3 Error Handling
  - Global error handler middleware
  - Retry logic para uploads
  - Graceful shutdown (SIGTERM)

- [ ] 7.4 Monitoring
  - Health check avanzado
  - Metrics endpoint (Prometheus-compatible)
  - Custom admin dashboard

**Duración**: 4 días

---

## FASE 5: Testing Exhaustivo 🧪 PENDIENTE

### Semana 8: Tests y Optimización

#### Objetivos
Asegurar calidad y performance antes de producción.

#### Tareas
- [ ] 8.1 Unit Tests
  - Services: contentService, storageService, evictionService
  - Utils: hash, validation
  - Coverage target: >70%

- [ ] 8.2 Integration Tests
  - API endpoints con DB de test
  - Auth flow completo
  - Upload flow completo
  - Eviction algorithm

- [ ] 8.3 Load Testing
  - Artillery o K6 setup
  - Test: 50 usuarios concurrentes
  - Test: 10 streams simultáneos
  - Identificar bottlenecks

- [ ] 8.4 Optimizaciones
  - Índices de DB (EXPLAIN ANALYZE)
  - Connection pooling
  - Compresión gzip
  - Lazy loading en frontend
  - Video seeking optimization

- [ ] 8.5 E2E Tests
  - Playwright setup
  - Tests críticos:
    * Login → search → play video
    * Upload video → verify playback
    * Admin delete → student can't access

**Criterio de éxito**: 
- All tests pass
- Coverage > 70%
- Response time p95 < 500ms
- 0% error rate bajo carga normal

**Duración**: 5-6 días

---

## FASE 6: Deploy y Lanzamiento 🚀 PENDIENTE

### Semana 9: Producción

#### Objetivos
Despliegue en servidor local y puesta en marcha.

#### Tareas
- [ ] 9.1 Dockerización (opcional)
  - Dockerfile para backend
  - Dockerfile para frontend
  - docker-compose.yml
  - Testing de containers

- [ ] 9.2 Deploy en Servidor
  - Configurar systemd services
  - Nginx reverse proxy
  - SSL certificates
  - Variables de entorno

- [ ] 9.3 Red Local
  - Configurar DHCP
  - DNS local (cdn.local)
  - Configurar APs
  - QoS en router

- [ ] 9.4 Documentación Final
  - Manual de usuario (estudiantes/teachers)
  - Manual de admin (operación)
  - Troubleshooting guide
  - Video tutorial

- [ ] 9.5 Testing con Usuarios Reales
  - 5-10 estudiantes piloto
  - Recoger feedback
  - Ajustes finales

**Criterio de éxito**: 
- 10 estudiantes pueden usar el sistema simultáneamente sin problemas
- Admin puede operar el sistema sin soporte técnico

**Duración**: 5 días

---

## POST-LANZAMIENTO: Mantenimiento y Mejoras 🔧

### Mes 4+: Operación Continua

#### Tareas Recurrentes
- Monitoreo diario de logs y errores
- Verificación semanal de backups
- Actualización de contenido (agregar/remover)
- Responder a reportes de usuarios

#### Mejoras Futuras (Backlog)

**Alto Prioridad** (Mes 4-5):
- [ ] Sistema de favoritos para estudiantes
- [ ] Tracking de progreso de video (marcadores)
- [ ] Subtítulos/closed captions
- [ ] Descarga offline a dispositivos móviles
- [ ] Notificaciones de nuevo contenido

**Media Prioridad** (Mes 6-8):
- [ ] Analytics dashboard para teachers
- [ ] Reportes de uso por estudiante
- [ ] Sistema de comentarios/discusiones
- [ ] Integración con LMS existente
- [ ] Mobile app (React Native)

**Baja Prioridad** (Mes 9-12):
- [ ] Recomendaciones personalizadas (ML)
- [ ] Generación automática de subtítulos (Whisper)
- [ ] Live streaming de clases
- [ ] Multicast para reducir ancho de banda
- [ ] Blockchain para certificados de completitud

---

## Métricas de Éxito

### KPIs Técnicos
| Métrica | Objetivo | Actual |
|---------|----------|--------|
| Uptime | > 99% | - |
| Response time (p95) | < 500ms | - |
| Error rate | < 1% | - |
| Concurrent streams | >= 10 | - |
| Storage efficiency | < 80% usado | - |

### KPIs de Negocio
| Métrica | Objetivo | Actual |
|---------|----------|--------|
| Estudiantes activos/mes | 50+ | - |
| Videos subidos/mes | 20+ | - |
| Horas de video visto/día | 10+ | - |
| Satisfacción usuarios | > 4/5 | - |
| Costo por estudiante/mes | < $1 | - |

---

## Riesgos y Plan de Contingencia

| Riesgo | Probabilidad | Impacto | Mitigación | Plan B |
|--------|--------------|---------|------------|--------|
| Hardware insuficiente | Media | Alto | Testear con carga antes de launch | Comprar RAM/SSD adicional |
| FFmpeg transcoding lento | Media | Medio | Usar presets fast | Reducir a solo 480p |
| WiFi congestionado | Alta | Alto | QoS + múltiples APs | Limitar usuarios/AP |
| Disco lleno crítico | Media | Alto | Monitoreo + alertas tempranas | Agregar disco externo |
| Corrupción de datos | Baja | Muy Alto | Backups diarios + validación | Restore desde backup |
| Developer enfermo | Media | Alto | Documentación detallada | Contratar freelancer temporal |

---

## Decisiones Pendientes

🤔 Decisiones que requieren input:

1. **Docker vs. PM2**: ¿Usar Docker para despliegue o PM2 tradicional?
   - Docker: más portable, fácil de replicar
   - PM2: más simple, menos overhead

2. **Certificados SSL**: ¿Implementar HTTPS desde el inicio?
   - Pros: buenas prácticas, seguridad
   - Cons: complejidad adicional, warnings en navegadores

3. **Mobile app**: ¿Priorizar PWA o native app?
   - PWA: más rápido de desarrollar
   - Native: mejor UX, funciona totalmente offline

4. **Replicación**: ¿Setup de servidor secundario desde el inicio?
   - Pros: alta disponibilidad
   - Cons: costo doble de hardware

**Recomendación**: Decidir en Semana 2 después de MVP funcional.

---

## Recursos y Referencias

### Documentación del Proyecto
- [Architecture](./architecture.md)
- [Database Design](./database-design.md)
- [Implementation Plan](./implementation-plan.md)
- [Testing Strategy](./testing-strategy.md)
- [FAQ](./faq.md)

### Referencias Externas
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Express.js Best Practices](https://expressjs.com/en/advanced/best-practice-performance.html)
- [React Video Player](https://videojs.com/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

---

## Actualizaciones del Roadmap

### 2026-02-16
- ✅ Documentación completa de planificación
- 📌 Listo para comenzar Fase 1

### 2026-XX-XX
- [Actualizaciones futuras aquí]

---

## Contacto y Soporte

**Project Lead**: [Tu nombre]
**Email**: [Tu email]
**GitHub**: [Link al repo cuando esté listo]
**Estado del Proyecto**: https://github.com/tu-user/cdn-offline/projects/1

---

**Última actualización**: 16 de Febrero de 2026
**Próxima revisión**: Al completar cada FASE
