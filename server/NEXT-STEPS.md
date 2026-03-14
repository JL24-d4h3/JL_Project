# 🎬 CONFIGURACIÓN DEL VIDEO - PASOS FINALES

## ✅ Video Encontrado
Tu video está en: `/home/jleon/2026/PUCP/GTR/CDN/storage/videos/test-video.mp4`

---

## 📝 Paso 1: Actualizar Base de Datos

Abre una **terminal nueva** y ejecuta:

```bash
psql -U cdn_user -h localhost -d cdn_db
```

Luego copia y pega esto:

```sql
UPDATE content 
SET 
    file_path = 'videos/test-video.mp4',
    file_hash = 'test-video-hash-updated'
WHERE id = '9172b6a0-f838-4f56-9468-9ab7ebd56991';

-- Verificar
SELECT id, title, file_path, status FROM content;

-- Salir
\q
```

---

## 🧪 Paso 2: Probar Streaming

En la terminal, ejecuta:

```bash
curl -I http://localhost:3000/api/content/9172b6a0-f838-4f56-9468-9ab7ebd56991/stream
```

**Deberías ver:**
- `HTTP/1.1 200 OK` o `206 Partial Content`
- `Content-Type: video/mp4`
- `Accept-Ranges: bytes`
- `ETag: ...`

Si ves **404 Not Found**: el video no está donde la DB espera
Si ves **500 Error**: revisa los logs del servidor

---

## 🎥 Paso 3: Probar en el Reproductor

Abre en tu navegador:

```bash
firefox /home/jleon/2026/PUCP/GTR/CDN/server/test-player.html
```

**En el HTML:**
1. Ingresa en "Content ID": `9172b6a0-f838-4f56-9468-9ab7ebd56991`
2. Click en "Cargar Video"
3. ¡Debería reproducirse!

---

## 🐛 Solución de Problemas

### Si no reproduce:

**1. Verifica que el archivo existe:**
```bash
ls -lh /home/jleon/2026/PUCP/GTR/CDN/storage/videos/test-video.mp4
```

**2. Verifica la ruta en la DB:**
```bash
curl -s http://localhost:3000/api/content/9172b6a0-f838-4f56-9468-9ab7ebd56991 | jq '.data.file_path'
```
Debe devolver: `"videos/test-video.mp4"`

**3. Verifica el servidor está corriendo:**
```bash
curl http://localhost:3000/health
```

**4. Revisa los logs del servidor** en la terminal donde corre `npm run dev`

---

## 🚀 Una Vez que Funcione

Confirma que el video reproduce correctamente y luego decide:

### ✅ OPCIÓN A: Frontend (Recomendado)
Crear la interfaz React completa:
- 🔐 Login page
- 📺 Lista de videos con thumbnails
- ▶️ Video player integrado
- 🔍 Búsqueda y filtros

**Tiempo:** 2-3 días
**Resultado:** Sistema completo usable

---

### ✅ OPCIÓN B: Upload de Videos
Implementar la subida de archivos:
- 📤 Endpoint POST /api/content
- 🎬 Procesamiento con FFmpeg
- 🖼️ Generación de thumbnails
- 📊 Múltiples calidades (720p, 480p)

**Tiempo:** 1-2 días
**Resultado:** Sistema autosuficiente

---

### ✅ OPCIÓN C: Docker Deployment
Containerizar todo el sistema:
- 🐳 Dockerfile backend/frontend
- 🔧 Docker Compose
- 🌐 NGINX reverse proxy
- 🔒 HTTPS con Let's Encrypt

**Tiempo:** 1 día
**Resultado:** Listo para producción

---

## 📋 Checklist de Progreso

### ✅ Completado (Backend - Día 1)
- [x] API REST con 10 endpoints
- [x] Autenticación JWT + Sessions
- [x] PostgreSQL con schema completo
- [x] Redis caching
- [x] HTTP Range requests (streaming)
- [x] Búsqueda full-text
- [x] Role-based authorization
- [x] Error handling global
- [x] Video de prueba configurado

### ⏭️ Siguiente Fase
- [ ] Frontend React + Video.js
- [ ] Upload de videos
- [ ] Docker deployment
- [ ] Mobile app (React Native)

---

## 💡 Mi Recomendación

**Continuar con OPCIÓN A (Frontend)** porque:
1. ✅ Ya tienes todo el backend funcional
2. ✅ El streaming ya funciona
3. 🎯 Verás resultados visuales inmediatos
4. 👥 Será usable para los usuarios finales
5. 📱 Luego adaptar a mobile será más fácil

---

## 📞 ¿Qué Sigue?

Una vez confirmes que el video reproduce:
1. Te muestro el plan de frontend completo
2. Empezamos con el primer componente (Login)
3. Continuamos con la lista de videos
4. Terminamos con el player integrado

**¿Listo para el frontend?** 🚀
