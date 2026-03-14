# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planeado
- Motor de conversación (modo IA extendido)
- Quantización INT8 del modelo para mayor velocidad
- Panel de administración de contenido

---

## [0.9.0] - 2026-03-03

### Recuperación y Reconstrucción
- ✅ Recuperación completa del proyecto desde VS Code local history (~85 archivos)
- ✅ Inicialización de repositorio git con commit base
- ✅ Reconstrucción de `ai_env/` desde cero (Python 3.12.3)

### Motor IA (`ai_engine/`)
- ✅ Dependencias reinstaladas: torch (CPU), fastapi, uvicorn, chromadb, sentence-transformers, rank_bm25
- ✅ spaCy 3.7.4 + modelo `es_core_news_md`
- ✅ transformers actualizado a 4.57.6 (soporte Phi-3.5 longrope)
- ✅ Phi-3.5-mini-instruct cargando correctamente en CPU (`modo: hf`)
- ✅ Streaming SSE funcionando en puerto 8000

### Search UI (`search_ui/`)
- ✅ Dependencias npm restituidas incluyendo `react-markdown`, `remark-math`, `remark-gfm`, `rehype-katex`, `react-syntax-highlighter`
- ✅ `AIOverview.tsx` limpiado (eliminado código duplicado — 455 → 154 líneas)
- ✅ Renderizado de KaTeX para ecuaciones matemáticas
- ✅ Renderizado de tablas GFM

### Estilo de Código
- ✅ Tema `nightOwl` para syntax highlighting (morado/naranja/verde/blanco)
- ✅ Contenedor azul noche con transparencia (`rgba(11,16,40,0.93)`)
- ✅ Borde azul tenue con glow box-shadow
- ✅ Eliminadas líneas/decoraciones de tokens vía CSS
- ✅ Inline code con pill azul translúcido

### Servidor (`server/`)
- ✅ node_modules restituidos
- ✅ Todos los servicios operativos: puertos 8000 · 3000 · 5175 · 5432 · 6379

---

## [0.1.0] - 2026-02-16

### Agregado - Fase de Planificación Completa ✅

#### Documentación
- ✅ README.md con visión general del proyecto
- ✅ EXECUTIVE_SUMMARY.md con propuesta completa
- ✅ QUICKSTART.md con guía de setup en 1 hora
- ✅ CONTRIBUTING.md con guías de contribución
- ✅ LICENSE (MIT) para uso open-source

#### Documentación Técnica
- ✅ docs/architecture.md - Diseño detallado del sistema
- ✅ docs/database-design.md - Schema completo de PostgreSQL
- ✅ docs/implementation-plan.md - Plan de desarrollo (9 semanas)
- ✅ docs/roadmap.md - Timeline y hitos del proyecto
- ✅ docs/testing-strategy.md - Estrategia completa de tests
- ✅ docs/scripts.md - Scripts bash de utilidad
- ✅ docs/faq.md - Preguntas frecuentes técnicas
- ✅ docs/diagrams.md - Diagramas visuales con Mermaid
- ✅ docs/INDEX.md - Navegación completa de documentación

#### Estructura del Proyecto
- ✅ Estructura de directorios definida
- ✅ .gitignore configurado
- ✅ .gitkeep para directorios de storage y backups

#### Decisiones de Arquitectura
- ✅ Stack tecnológico: Node.js + PostgreSQL + React
- ✅ Modelo de datos completo
- ✅ Políticas de eviction (LRU)
- ✅ Sistema de backups
- ✅ Control de acceso (RBAC)

#### Diagramas
- ✅ Flujo de solicitud de contenido
- ✅ Flujo de upload
- ✅ Arquitectura de componentes
- ✅ Modelo ER de base de datos
- ✅ Flujo de eviction
- ✅ Arquitectura física de red

### Estimaciones
- **Costo Hardware**: $450 one-time
- **Costo Operación**: $100/año
- **Timeline**: 9 semanas hasta producción
- **MVP Demo**: Semana 2
- **MVP Final**: Semana 6
- **Producción**: Semana 9

---

## Versiones Futuras [PLANEADO]

### [0.2.0] - Fase 1: Setup y Prototipo (Semanas 1-2)
#### Planeado
- [ ] Instalación de dependencias (PostgreSQL, Redis, Node.js, FFmpeg)
- [ ] Estructura básica del backend
- [ ] Estructura básica del frontend
- [ ] Base de datos inicializada con schema
- [ ] Health check endpoint funcional
- [ ] Streaming básico de 3 videos de prueba

### [0.3.0] - Fase 2: Features Core (Semanas 3-4)
#### Planeado
- [ ] Sistema de autenticación con JWT
- [ ] Permisos basados en roles (RBAC)
- [ ] Upload de contenido
- [ ] Transcodificación de video (FFmpeg)
- [ ] Búsqueda full-text
- [ ] Sistema de caché con Redis

### [0.4.0] - Fase 3: Storage Management (Semana 5)
#### Planeado
- [ ] Monitoreo de espacio en disco
- [ ] Algoritmo de eviction (LRU)
- [ ] Soft delete
- [ ] Archiving de contenido eliminado

### [0.5.0] - Fase 4: Backups y Seguridad (Semanas 6-7)
#### Planeado
- [ ] Backups automáticos (cron)
- [ ] Scripts de restore
- [ ] HTTPS con certificados
- [ ] Rate limiting
- [ ] Input validation
- [ ] Logging estructurado (Winston)

### [0.6.0] - Fase 5: Testing (Semana 8)
#### Planeado
- [ ] Unit tests (>70% coverage)
- [ ] Integration tests
- [ ] E2E tests (Playwright)
- [ ] Load testing (Artillery)
- [ ] Security testing
- [ ] Performance optimization

### [1.0.0] - Fase 6: Producción (Semana 9)
#### Planeado
- [ ] Dockerización
- [ ] Deploy en servidor local
- [ ] Configuración de red local
- [ ] Documentación de usuario final
- [ ] Testing con usuarios reales
- [ ] Launch oficial

---

## Versiones Post-Launch [BACKLOG]

### [1.1.0] - Mejoras Inmediatas
- [ ] Sistema de favoritos
- [ ] Tracking de progreso de video
- [ ] Subtítulos/closed captions
- [ ] Descarga offline a móviles
- [ ] Notificaciones de nuevo contenido

### [1.2.0] - Analytics
- [ ] Dashboard para teachers
- [ ] Reportes de uso por estudiante
- [ ] Heatmaps de viewing
- [ ] Exportación de reportes

### [1.3.0] - Colaboración
- [ ] Sistema de comentarios
- [ ] Discusiones por video
- [ ] Integración con LMS

### [1.4.0] - Mobile
- [ ] React Native app
- [ ] Descarga offline
- [ ] Sincronización automática

### [2.0.0] - IA y ML
- [ ] Recomendaciones personalizadas
- [ ] Generación de subtítulos (Whisper)
- [ ] Búsqueda semántica
- [ ] Resúmenes automáticos

### [3.0.0] - Escalabilidad
- [ ] Multi-nodo (red mesh)
- [ ] Replicación entre escuelas
- [ ] Sincronización con servidor central
- [ ] Live streaming de clases

---

## Tipos de Cambios

- **Added**: Nuevas funcionalidades
- **Changed**: Cambios en funcionalidades existentes
- **Deprecated**: Funcionalidades que serán removidas
- **Removed**: Funcionalidades removidas
- **Fixed**: Bug fixes
- **Security**: Mejoras de seguridad

---

## Contribuidores

### v0.1.0 (Planificación)
- [Tu nombre] - Diseño de arquitectura, documentación completa

---

**Formato del Changelog**:
```markdown
## [Version] - YYYY-MM-DD

### Added
- Nueva funcionalidad X
- Nueva funcionalidad Y

### Changed
- Cambio en funcionalidad Z

### Fixed
- Bug fix para issue #123

### Security
- Parche de seguridad para vulnerabilidad CVE-XXXX
```

---

**Última actualización**: 16 de Febrero de 2026
