# Preguntas Frecuentes (FAQ) Técnico

## 1. Decisiones de Arquitectura

### ¿Por qué PostgreSQL en lugar de MongoDB?

**Respuesta**: PostgreSQL es superior para este caso de uso por varias razones:

1. **Consistencia ACID**: Crítica para evitar corrupción de metadatos cuando múltiples usuarios suben contenido
2. **Relaciones complejas**: Permisos, categorías, tags requieren JOINs eficientes
3. **Full-text search nativo**: Búsqueda en español integrada
4. **Replicación madura**: Para expansión a múltiples nodos
5. **Backups confiables**: pg_dump es estándar de la industria

MongoDB sería útil si tuviéramos documentos completamente no estructurados, pero nuestro modelo es mayormente relacional.

### ¿Por qué separar metadatos (DB) y binarios (filesystem)?

**Respuesta**: Por eficiencia:
- **DB**: Excelente para búsquedas, filtros, consultas complejas
- **Filesystem**: Optimizado para streaming de grandes archivos
- Guardar videos en DB (BLOB) generaría queries lentas y backups gigantes
- Esta separación es la práctica estándar (YouTube, Netflix lo hacen así)

### ¿Por qué Node.js en lugar de Python/Django?

**Respuesta**: Ambos son válidos, pero Node.js tiene ventajas para streaming:
- **Non-blocking I/O**: Maneja múltiples streams concurrentes eficientemente
- **Ecosistema**: `express`, `sharp`, `fluent-ffmpeg` son maduros
- **TypeScript**: Type safety reduce bugs en producción
- **Single-threaded event loop**: Perfecto para I/O intensivo

Python/FastAPI sería igualmente válido y más rápido de desarrollar si ya tienes experiencia.

---

## 2. Almacenamiento y Eviction

### ¿Cómo sé qué contenido borrar si todo es importante?

**Respuesta**: Implementa un sistema de **prioridades**:

```
Prioridad 10 (Nunca borrar):
- Contenido curricular obligatorio
- Videos de introducción a matemáticas básicas
- Material de exámenes

Prioridad 5 (Normal):
- Contenido suplementario
- Videos de práctica adicional

Prioridad 1-3 (Borrar primero):
- Material antiguo reemplazado por nuevas versiones
- Contenido experimental
- Grabaciones de eventos pasados
```

Además, el algoritmo LRU respeta esto: borra primero lo menos usado de baja prioridad.

### ¿Qué pasa si los estudiantes solicitan contenido que ya fue eliminado?

**Respuestas:**

**Opción 1 - Restauración desde backup**:
```
1. Admin recibe notificación: "Video X solicitado pero no existe"
2. Admin restaura desde backup offline (disco externo)
3. Video vuelve a estar disponible en 10-30 minutos
```

**Opción 2 - Lista de espera**:
```
1. Sistema registra solicitud de contenido faltante
2. Si >=5 estudiantes solicitan el mismo video → auto-priorizar restauración
3. Notificar a estudiantes cuando esté disponible
```

**Opción 3 - Contenido bajo demanda**:
- Mantener versiones de menor calidad (240p) que ocupan 1/10 del espacio
- Si el original fue eliminado, servir la versión baja hasta restaurar el HD

### ¿Cuánto espacio necesito realmente?

**Cálculo estimado por estudiante/mes**:
```
Supuestos:
- 20 videos/mes por estudiante
- 5 minutos promedio por video
- 720p: ~50MB por video

Espacio = 20 videos × 50MB = 1GB/estudiante/mes
```

**Ejemplos**:
- 50 estudiantes: 50GB/mes
- 200 estudiantes: 200GB/mes
- 500 estudiantes: 500GB/mes

Con políticas de eviction, puedes mantener los últimos 3 meses de contenido activo y archivar el resto.

---

## 3. Rendimiento y Escalabilidad

### ¿Cuántos usuarios concurrentes puede soportar?

**Depende del hardware**, pero con el setup mínimo recomendado:

| Hardware | Streams Concurrentes | Usuarios Navegando |
|----------|---------------------|-------------------|
| i5, 8GB RAM, HDD | 10-15 | 50 |
| i7, 16GB RAM, SSD | 30-50 | 200 |
| Xeon, 32GB RAM, SSD + HDD | 100+ | 500+ |

**Bottleneck principal**: Disco (I/O). Un HDD puede hacer ~100 MB/s secuencial pero sufre con muchos accesos aleatorios.

**Solución**: SSD para OS + DB + archivos populares, HDD para archivo de largo plazo.

### ¿Cómo optimizo para más usuarios?

**Optimizaciones progresivas**:

1. **Caché agresivo** (gratis):
   - Redis para metadatos: reduce queries a DB en 80%
   - Nginx reverse proxy con caché de contenido estático

2. **Compresión** (gratis):
   - Videos ya están comprimidos (H.264)
   - Comprimir API responses (gzip): reduce tráfico 70%

3. **CDN interno** (bajo costo):
   - Segundo servidor barato que replica videos populares
   - Load balancing entre servidores

4. **Calidad adaptativa** (medio esfuerzo):
   - Detectar ancho de banda del user
   - Servir 480p a usuarios con WiFi débil (reduce carga 60%)

### Mi WiFi es lento (2.4 GHz, pared gruesas), ¿funcionará?

**Sí, pero con ajustes**:

WiFi 2.4 GHz típicamente da **20-30 Mbps** real (aunque dice 150 Mbps).

**Para streaming 720p necesitas ~5 Mbps**, entonces:
- 1 AP puede servir ~5 usuarios simultáneos
- Si tienes 30 estudiantes, necesitas 6 APs o usar 480p (2 Mbps) para soportar 12 usuarios/AP

**Recomendaciones**:
- Usa WiFi 5 GHz (802.11ac) si es posible: ~100 Mbps real
- Coloca APs estratégicamente (cada 15-20 metros)
- Implementa QoS: priorizar streaming sobre descargas

---

## 4. Seguridad y Privacidad

### ¿Necesito HTTPS si la red es local?

**Recomendado pero no crítico para MVP**:

**Sin HTTPS**:
- ✅ Funciona perfectamente en red local cerrada
- ⚠️ Contraseñas viajan en texto plano
- ⚠️ Tokens JWT pueden ser interceptados

**Con HTTPS** (certificado self-signed):
```bash
# Generar certificado con mkcert (para testing)
mkcert -install
mkcert cdn.local localhost 192.168.1.100
```
- ✅ Comunicación encriptada
- ✅ Buenas prácticas
- ⚠️ Navegadores mostrarán advertencia (aceptable en red local)

**Para producción**: Si la escuela tiene múltiples redes o acceso público, HTTPS es obligatorio.

### ¿Cómo prevenir que estudiantes borren contenido?

**Control de acceso basado en roles (RBAC)**:

```typescript
// Middleware de autorización
app.delete('/api/content/:id', authorize('admin'), deleteContent);

function authorize(requiredRole) {
  const roleHierarchy = {
    student: 1,    // Solo lectura
    teacher: 2,    // Lectura + subir sus propios videos
    admin: 3,      // Todo excepto configuración del sistema
    superadmin: 4  // Todo
  };
  
  return (req, res, next) => {
    if (req.user.role >= requiredRole) next();
    else res.status(403).json({ error: 'Forbidden' });
  };
}
```

**Además**:
- Soft delete: archivos "borrados" van a papelera por 30 días
- Audit log: registro de quién borró qué y cuándo
- Confirmación doble para borrados permanentes

### ¿Qué pasa si alguien sube contenido inapropiado?

**Estrategia de moderación**:

1. **Prevención**:
   - Solo teachers/admins pueden subir
   - Validar tipos de archivo (solo video/pdf/audio)
   - Límite de tamaño: 500MB por archivo

2. **Detección**:
   - Admin revisa contenido antes de activarlo (status='pending')
   - Opción: OCR en thumbnails para detectar texto inapropiado

3. **Reacción**:
   - Botón de reporte para estudiantes
   - Admin puede ocultar contenido instantáneamente
   - Suspender cuenta del uploader

---

## 5. Backup y Recuperación

### ¿Con qué frecuencia debo hacer backups?

**Recomendación por nivel de criticidad**:

| Dato | Frecuencia | Razón |
|------|------------|-------|
| Database | Diario | Metadatos cambian frecuentemente |
| Videos populares | Semanal | Se acceden a diario, recuperación crítica |
| Videos antiguos | Mensual | Baja prioridad, consumo de espacio |
| Configuración | Al cambiar | Archivo pequeño, crítico para restore |

**Setup mínimo viable**:
```bash
# Cron job diario a las 2 AM
0 2 * * * /opt/cdn/scripts/backup-daily.sh
```

### ¿Cuánto tiempo toma restaurar desde backup?

**Ejemplo con 500GB de contenido**:

| Escenario | Tiempo |
|-----------|--------|
| Solo DB (100MB) | 1-2 minutos |
| DB + 10 videos prioritarios | 10-15 minutos |
| Restore completo desde disco USB 3.0 | 2-4 horas |
| Restore completo desde disco USB 2.0 | 8-12 horas |

**Optimización**: 
- Mantener "hot" backup en segundo disco interno (restore en minutos)
- "Cold" backup semanal en disco externo (solo para desastres)

### ¿Qué pasa si se corrompe la base de datos?

**Plan de contingencia**:

1. **Detección automática**:
   ```bash
   # Health check cada 5 minutos
   */5 * * * * pg_isready || /opt/cdn/scripts/alert-admin.sh
   ```

2. **Restore desde último backup**:
   ```bash
   # Detener servicio
   systemctl stop cdn-server
   
   # Restore DB
   dropdb cdn_db
   createdb cdn_db
   pg_restore -d cdn_db /backups/latest.dump
   
   # Reiniciar
   systemctl start cdn-server
   ```

3. **Validación**:
   - Comprobar que contenido es accesible
   - Verificar counts: número de videos, usuarios, etc.

**Prevención**:
- PostgreSQL es extremadamente robusto
- Usar replicación streaming para redundancia
- Monitorear logs: `tail -f /var/log/postgresql/postgresql-14-main.log`

---

## 6. Integración con IA (Futuro)

### ¿Cómo integraría IA después?

**Casos de uso viables offline**:

1. **Recomendaciones personalizadas**:
   ```python
   # Modelo simple: Collaborative filtering
   # Basado en "usuarios que vieron X también vieron Y"
   # Se entrena con access_log local
   
   from surprise import SVD
   model = SVD()
   model.fit(access_log_data)
   recommendations = model.predict(user_id, n=10)
   ```

2. **Generación automática de subtítulos**:
   ```python
   # Whisper de OpenAI (offline)
   import whisper
   
   model = whisper.load_model("base")
   result = model.transcribe("video.mp4", language="es")
   generate_srt(result["text"])
   ```

3. **Búsqueda semántica**:
   ```python
   # Sentence transformers para embeddings
   from sentence_transformers import SentenceTransformer
   
   model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
   # Generar embeddings de titles/descriptions
   # Búsqueda por similitud coseno en lugar de full-text
   ```

4. **Resúmenes automáticos de videos**:
   - Extraer frames clave cada 30 segundos
   - Usar CLIP para entender contenido visual
   - Generar "mapa de contenido" del video

**Importante**: Modelos deben correr localmente (sin internet). Usar modelos pequeños optimizados.

---

## 7. Troubleshooting Común

### Error: "Cannot read property 'mp4' of undefined"

**Causa**: FFmpeg no instalado o versión incorrecta.

**Solución**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Verificar
ffmpeg -version  # Debe ser >= 4.4
```

### Error: "ENOSPC: System limit for number of file watchers reached"

**Causa**: Node.js excede límite de archivos monitoreados.

**Solución**:
```bash
# Aumentar límite (temporal)
sudo sysctl fs.inotify.max_user_watches=524288

# Permanente
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Videos no se reproducen en Safari/iOS

**Causa**: Safari requiere MP4 con moov atom al inicio.

**Solución**:
```bash
# Al transcodificar, usar -movflags faststart
ffmpeg -i input.mp4 -movflags faststart output.mp4
```

### Búsqueda no encuentra contenido con acentos

**Causa**: PostgreSQL no configurado con unaccent.

**Solución**:
```sql
CREATE EXTENSION unaccent;

-- Usar en búsqueda
SELECT * FROM content 
WHERE to_tsvector('spanish', unaccent(title)) @@ to_tsquery('spanish', unaccent('Matematicas'));
```

### Upload se queda en "Processing" indefinidamente

**Causa**: Worker de transcodificación crasheó.

**Solución**:
```bash
# Ver logs del worker
pm2 logs transcode-worker

# Reintentar job manualmente
npm run retry-job <content_id>
```

---

## 8. Comparación con Soluciones Existentes

### ¿Por qué no usar Moodle + plugin de video?

**Moodle es excelente para cursos, pero**:
- ❌ No optimizado para streaming offline
- ❌ Interfaz compleja para estudiantes jóvenes
- ❌ Consume ~2GB de RAM solo para la plataforma
- ✅ Nuestra CDN: enfocada solo en entrega de contenido, ligera

**Cuándo usar Moodle**: Si necesitas quizzes, tareas, calificaciones, foros.

### ¿Por qué no usar Plex/Jellyfin?

**Plex/Jellyfin son para entretenimiento, no educación**:
- ❌ No tiene sistema de permisos educativos (teacher/student)
- ❌ No tiene búsqueda por tags educativos (nivel, materia)
- ❌ No tiene analytics de progreso de estudiantes
- ✅ Nuestra CDN: diseñada para contexto educativo

**Cuándo usar Plex**: Si solo quieres compartir videos sin control granular.

### ¿Por qué no usar Nextcloud?

**Nextcloud es genial para file sharing general**:
- ⚠️ Streaming no es su fuerte (es para descargas)
- ⚠️ No tiene sistema de eviction inteligente
- ⚠️ No optimizado para múltiples calidades de video
- ✅ Podrías usar Nextcloud + nuestra CDN: Nextcloud para documentos, CDN para videos

---

## 9. Expansión Futura

### ¿Puedo conectar múltiples escuelas en una red?

**Sí, con arquitectura mesh**:

```
Escuela A (Nodo 1)      Escuela B (Nodo 2)
     |                        |
     +-------- VPN/Link ------+
     |                        |
Contenido local          Contenido local
+ Cache del otro nodo    + Cache del otro nodo
```

**Implementación**:
- Cada escuela tiene su servidor CDN
- Replicación asíncrona de contenido popular
- Búsqueda federada: si Escuela A no tiene un video, busca en Escuela B
- Sincronización cuando hay internet disponible (opcional)

### ¿Funciona con conexión a internet intermitente?

**Sí, está diseñada para offline-first**:

**Con internet ocasional**:
- ✅ Sistema funciona 100% offline
- ✅ Cuando hay internet: sincroniza con servidor central (opcional)
- ✅ Download de contenido nuevo del MoE (Ministerio de Educación)
- ✅ Upload de analytics/logs para monitoring central

**Sin internet nunca**:
- ✅ Todo funciona igual
- Manual content updates: admin trae USB con videos nuevos

---

## 10. Costos

### ¿Cuánto cuesta implementar esto?

**Estimación de costos (Perú, 2026)**:

| Item | Costo (USD) | Notas |
|------|------------|-------|
| PC Servidor (usado) | $200-300 | i5, 16GB RAM, 500GB HDD |
| Disco adicional 1TB | $40 | Backup |
| Router | $30-50 | Incluido si ya tienes |
| Access Points (x3) | $90 | TP-Link ~$30 c/u |
| Ethernet cables | $20 | 50m total |
| UPS (opcional) | $80 | Protege contra apagones |
| **Total Hardware** | **$460-580** | |
| | | |
| Desarrollo (si contratas) | $1500-3000 | 3-6 semanas dev |
| Desarrollo (tú mismo) | $0 | 8-12 semanas aprendiendo |
| Mantenimiento/año | $0-100 | Electricidad ~$50/año |

**Más barato que**:
- Tablets para todos los estudiantes: $200 × 50 = $10,000
- Conexión a internet satelital: $100-200/mes = $1200-2400/año

### ¿Es más barato que soluciones comerciales?

**Comparación (para 100 estudiantes)**:

| Solución | Costo Setup | Costo Anual | Requiere Internet |
|----------|-------------|-------------|-------------------|
| Nuestra CDN | $500 | $50 | ❌ No |
| Google Workspace for Education | Gratis | $0 | ✅ Sí (crítico) |
| Microsoft Teams + OneDrive | $1-3/estudiante/mes | $1200-3600 | ✅ Sí |
| Vimeo for Business | $50-75/mes | $600-900 | ✅ Sí |

**Conclusión**: Para zonas sin internet, nuestra CDN es la única opción viable económicamente.

---

¿Tienes más preguntas? Agrégalas a este documento conforme surjan durante el desarrollo.
