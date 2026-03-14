# CDN Offline para Contenido Educativo en Zonas Rurales

<div align="center">

**Sistema de distribución de contenido educativo que opera completamente offline usando redes WiFi locales**

[![Status](https://img.shields.io/badge/status-planning-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Version](https://img.shields.io/badge/version-0.1.0-orange)]()

[Quickstart](./QUICKSTART.md) • [Resumen Ejecutivo](./EXECUTIVE_SUMMARY.md) • [Documentación](./docs/INDEX.md) • [Roadmap](./docs/roadmap.md)

</div>

---

## 🎯 ¿Qué es esto?

Una **CDN (Content Delivery Network) offline** diseñada para llevar contenido educativo digital (videos, PDFs, interactivos) a zonas rurales sin acceso confiable a Internet.

**Think**: "YouTube + Google Drive" funcionando completamente offline en tu escuela 🏫

### Caso de Uso
1. Estudiante busca "Números Reales" desde su laptop → WiFi local
2. Servidor local encuentra el video y lo transmite
3. Video se reproduce instantáneamente sin necesidad de Internet
4. Todo sucede en la red local de la escuela 🚀

---

## ✨ Características Principales

### Para Estudiantes 👨‍🎓
- 🔍 Búsqueda de contenido por título, categoría o tema
- 📹 Streaming de videos en HD (múltiples calidades)
- 📄 Visualización de documentos PDF
- ⚡ Experiencia rápida similar a Netflix
- 🌐 **100% offline** - no requiere Internet

### Para Profesores 👩‍🏫
- 📤 Subir videos y documentos fácilmente
- 📊 Ver estadísticas de uso (contenido más visto)
- 🏷️ Organizar contenido con categorías y tags
- ✏️ Editar o eliminar su contenido

### Para Administradores 👨‍💼
- 👥 Gestión de usuarios y permisos (roles)
- 💾 Políticas automáticas de gestión de espacio
- 🔄 Backups automáticos diarios
- 📈 Dashboard de analytics y monitoring
- 🛡️ Control total del sistema

---

## 🚀 Inicio Rápido

### Para Usuarios

**¿Solo quieres entender el proyecto?**
→ Lee el **[Resumen Ejecutivo](./EXECUTIVE_SUMMARY.md)** (20 min de lectura)

### Para Developers

**¿Quieres implementarlo?**
→ Sigue la **[Guía Quickstart](./QUICKSTART.md)** (sistema funcionando en 1 hora)

**¿Quieres entender cómo funciona?**
→ Lee la **[Documentación Técnica](./docs/INDEX.md)**

---

## 📚 Documentación

### 📖 Documentos Clave

| Documento | Descripción | Para quién |
|-----------|-------------|------------|
| **[Resumen Ejecutivo](./EXECUTIVE_SUMMARY.md)** ⭐ | Propuesta completa, costos, beneficios | Stakeholders, directores |
| **[Quickstart](./QUICKSTART.md)** 🔥 | Setup en 1 hora con comandos exactos | Developers, SysAdmins |
| **[Índice de Docs](./docs/INDEX.md)** 📚 | Navegación por toda la documentación | Todos |

### 🏗️ Documentación Técnica

| Documento | Qué contiene |
|-----------|--------------|
| [Architecture](./docs/architecture.md) | Diseño del sistema, decisiones técnicas |
| [Database Design](./docs/database-design.md) | Schema completo de PostgreSQL con scripts |
| [Implementation Plan](./docs/implementation-plan.md) | Plan de desarrollo fase por fase (9 semanas) |
| [Roadmap](./docs/roadmap.md) | Timeline, hitos, métricas de éxito |
| [Testing Strategy](./docs/testing-strategy.md) | Unit, integration, E2E, load testing |
| [Scripts](./docs/scripts.md) | Scripts bash para operación y mantenimiento |
| [FAQ](./docs/faq.md) | Preguntas frecuentes con respuestas detalladas |
| [Diagrams](./docs/diagrams.md) | Diagramas visuales (Mermaid) |

---

## 🏗️ Arquitectura Simplificada

```
┌─────────────────────────────────────────────────────┐
│               ESTUDIANTES                           │
│  🧑‍💻 Laptops  📱 Tablets  📱 Phones                 │
└──────────────┬──────────────────────────────────────┘
               │ WiFi Local
               ↓
┌──────────────────────────────────────────────────────┐
│           ACCESS POINTS / ROUTER                     │
│  📡 AP #1 (Aula 101)  📡 AP #2 (Aula 102)           │
└──────────────┬───────────────────────────────────────┘
               │ Ethernet
               ↓
┌──────────────────────────────────────────────────────┐
│              SERVIDOR LOCAL (PC)                     │
│  ┌────────────────────────────────────────────────┐ │
│  │  ⚡ Node.js API Server                         │ │
│  │  💾 PostgreSQL Database                        │ │
│  │  🚀 Redis Cache                                │ │
│  │  📁 File Storage (Videos/PDFs)                 │ │
│  │  🎬 FFmpeg (Transcoding)                       │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**[Ver diagramas detallados →](./docs/diagrams.md)**

---

## 💻 Stack Tecnológico

| Capa | Tecnología | ¿Por qué? |
|------|-----------|-----------|
| **Frontend** | React + TypeScript + Vite | Moderno, rápido, type-safe |
| **Backend** | Node.js + Express | Excelente para streaming y I/O |
| **Base de Datos** | PostgreSQL 14+ | Robusta, ACID, full-text search |
| **Cache** | Redis 7+ | Ultra-rápido para metadatos |
| **Storage** | Filesystem (ext4) | Optimizado para archivos grandes |
| **Processing** | FFmpeg | Transcodificación de video |
| **Testing** | Jest, Playwright | Unit, integration, E2E |

**Todo es open-source** 🆓

---

## 💰 Costos

### Inversión Inicial
- **Hardware**: ~$450 (PC servidor + APs + cables)
- **Software**: $0 (todo open-source)
- **Setup**: 1-3 meses de desarrollo

### Operación Anual
- **Electricidad**: ~$50/año
- **Mantenimiento**: ~$50/año
- **Total**: ~$100/año

**ROI**: Más barato 10-20x que alternativas con Internet 📊

**[Ver análisis detallado de costos →](./EXECUTIVE_SUMMARY.md#-costos-estimados)**

---

## 📅 Timeline

```
┌────────────┬────────────┬────────────┐
│   Mes 1    │   Mes 2    │   Mes 3    │
├────────────┼────────────┼────────────┤
│ Setup      │ Features   │ Testing &  │
│ Prototipo  │ Core       │ Deploy     │
└────────────┴────────────┴────────────┘
     ↑            ↑             ↑
  Semana 2    Semana 6      Semana 9
  MVP Demo    MVP Final     Producción
```

### Hitos Clave
- **Semana 2**: Demo de streaming (3 videos) 🎬
- **Semana 6**: MVP completo con todas las features ✅
- **Semana 9**: Sistema en producción con 50+ usuarios 🚀

**[Ver roadmap detallado →](./docs/roadmap.md)**

---

## 📊 Estado del Proyecto

```
FASE ACTUAL: 📋 PLANIFICACIÓN COMPLETA

Completado:
  ✅ Documento de arquitectura
  ✅ Diseño de base de datos  
  ✅ Plan de implementación
  ✅ Estrategia de testing
  ✅ Documentación completa
  ✅ Scripts de utilidad

Próximo:
  🔨 FASE 1: Desarrollo (Setup + Prototipo)
```

**Última actualización**: 16 de Febrero de 2026

---

## 🛠️ Para Contribuidores

### Prerequisitos del Sistema
- Ubuntu Server 22.04 LTS (recomendado)
- 8GB RAM mínimo, 16GB recomendado
- 100GB disco libre (500GB+ para producción)
- Node.js 18 LTS
- PostgreSQL 14+
- Redis 7+
- FFmpeg 4.4+

### Setup de Desarrollo

```bash
# 1. Clonar el repo
git clone https://github.com/tu-usuario/cdn-offline.git
cd cdn-offline

# 2. Seguir la guía quickstart
# Ver: QUICKSTART.md

# 3. Instalar dependencias
cd server && npm install
cd ../client && npm install

# 4. Setup de base de datos
# Ver: docs/database-design.md

# 5. Ejecutar en desarrollo
# Terminal 1: Backend
cd server && npm run dev

# Terminal 2: Frontend  
cd client && npm run dev
```

**[Guía completa de setup →](./QUICKSTART.md)**

---

## 🧪 Testing

```bash
# Unit tests
cd server && npm test

# Integration tests
npm run test:integration

# E2E tests
cd client && npm run test:e2e

# Load testing
artillery run tests/load-test.yml
```

**[Estrategia completa de testing →](./docs/testing-strategy.md)**

---

## 📈 Métricas de Éxito

### KPIs Técnicos
- ✅ Uptime > 99%
- ✅ Response time (p95) < 500ms
- ✅ Error rate < 1%
- ✅ 10+ concurrent video streams

### KPIs de Negocio
- ✅ 50+ estudiantes activos/mes
- ✅ 20+ videos disponibles
- ✅ 10+ horas de contenido visto/día
- ✅ Satisfacción > 4/5

---

## 🤝 Contribuir

Este es un proyecto **educativo y open-source**. Contribuciones son bienvenidas:

1. **Documentación**: Mejora o corrige docs
2. **Código**: Implementa features o arregla bugs
3. **Testing**: Agrega tests
4. **Ideas**: Abre issues con sugerencias

### Áreas donde necesitamos ayuda
- [ ] Implementación del backend (Node.js)
- [ ] Implementación del frontend (React)
- [ ] Testing exhaustivo
- [ ] Mejoras de UI/UX
- [ ] Documentación de usuario final
- [ ] Video tutoriales

---

## 📞 Contacto

**Autor**: [Tu nombre]  
**Email**: [tu-email@example.com]  
**GitHub**: [github.com/tu-usuario/cdn-offline]  

**Para preguntas**: Abre un Issue en GitHub  
**Para contribuir**: Fork + Pull Request

---

## 📜 Licencia

Este proyecto está bajo licencia **MIT**.

- ✅ Uso gratuito para educación
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso comercial permitido

Ver [LICENSE](./LICENSE) para más detalles.

---

## 🌟 Agradecimientos

Este proyecto está inspirado en el desafío de llevar educación digital de calidad a zonas rurales donde el acceso a Internet es limitado o inexistente.

**Dedicado a todos los estudiantes que merecen acceso a educación de calidad, sin importar dónde vivan.** 🎓

---

## 🔗 Links Útiles

- 📖 [Documentación Completa](./docs/INDEX.md)
- 🚀 [Guía de Inicio Rápido](./QUICKSTART.md)
- 📊 [Resumen Ejecutivo](./EXECUTIVE_SUMMARY.md)
- 🗺️ [Roadmap del Proyecto](./docs/roadmap.md)
- ❓ [Preguntas Frecuentes](./docs/faq.md)
- 🏗️ [Arquitectura](./docs/architecture.md)
- 🗄️ [Diseño de Base de Datos](./docs/database-design.md)

---

<div align="center">

**¿Listo para comenzar?** 

[Quickstart](./QUICKSTART.md) • [Docs](./docs/INDEX.md) • [Roadmap](./docs/roadmap.md)

**Hecho con ❤️ para la educación rural**

</div>
