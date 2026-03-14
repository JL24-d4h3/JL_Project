# Sistema de Integridad y Sincronización

## Problema que Resuelve

El sistema almacena archivos en el **filesystem** (`storage/`) y mantiene referencias en la **base de datos** (PostgreSQL). Cuando se eliminan archivos manualmente del disco o quedan registros huérfanos en la BD, se produce una **inconsistencia**.

**Síntomas comunes:**
- ✅ Archivo existe en disco pero NO aparece en la interfaz → **problema de caché**
- ❌ Archivo aparece en la interfaz pero NO existe en disco → **registro huérfano**
- ❌ Archivos en disco sin registro en BD → **archivos huérfanos**

## Endpoints del Sistema de Integridad

Todos estos endpoints requieren autenticación como **admin**.

### 1. Verificar Integridad

```http
GET /api/system/integrity
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "orphanedRecords": [
      {
        "id": "uuid",
        "title": "Flor",
        "file_path": "images/b574972...jpg",
        "status": "active"
      }
    ],
    "orphanedFiles": [
      "videos/xyz123...mp4"
    ],
    "stats": {
      "totalRecords": 10,
      "validRecords": 8,
      "orphanedRecords": 2,
      "orphanedFiles": 1
    }
  },
  "message": "Se detectaron inconsistencias"
}
```

**Interpretación:**
- `orphanedRecords`: Registros en BD sin archivo en disco
- `orphanedFiles`: Archivos en disco sin registro en BD
- `validRecords`: Archivos que existen tanto en BD como en disco

### 2. Sincronización Completa

```http
POST /api/system/sync
Content-Type: application/json

{
  "dryRun": true
}
```

**Modo Simulación (`dryRun: true`):**
- NO realiza cambios
- Muestra qué se eliminaría
- **Recomendado ejecutar primero**

**Modo Real (`dryRun: false`):**
- Elimina registros huérfanos de la BD
- Elimina archivos huérfanos del disco
- Invalida caché de Redis

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "orphanedRecordsDeleted": [
      "Flor (images/b574972...jpg)",
      "Video Viejo (videos/abc123...mp4)"
    ],
    "orphanedFilesDeleted": [
      "videos/xyz789...mp4"
    ],
    "dryRun": false
  },
  "message": "Sincronización completada. Caché invalidado."
}
```

### 3. Reparar Solo Registros

```http
POST /api/system/repair-records
Content-Type: application/json

{
  "dryRun": false
}
```

Elimina **solo registros de BD** cuyos archivos ya no existen en disco.

**Uso:** Cuando eliminas archivos manualmente del disco y quieres limpiar la BD.

### 4. Limpiar Solo Archivos

```http
POST /api/system/clean-files
Content-Type: application/json

{
  "dryRun": false
}
```

Elimina **solo archivos del disco** que no tienen registro en la BD.

**Uso:** Cuando hay archivos residuales en `storage/` que no se crearon correctamente.

### 5. Limpiar Caché

```http
POST /api/system/clear-cache
Content-Type: application/json

{
  "pattern": "content:*"
}
```

Invalida el caché de Redis manualmente.

**Patrones comunes:**
- `content:*` - Todo el caché de contenido
- `content:list:*` - Solo listas de contenido
- `categories:*` - Caché de categorías

## Casos de Uso

### Caso 1: Archivo No Aparece Después de Subirlo

**Síntoma:** Subiste "Mask.jpg", está en `storage/images/` pero no aparece en la interfaz.

**Causa:** Caché de Redis desactualizado.

**Solución:**
```bash
curl -X POST http://localhost:3000/api/system/clear-cache \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "content:*"}'
```

**Alternativa:** Esperar 1 hora (TTL del caché) o reiniciar servidor.

### Caso 2: Eliminaste Archivos Manualmente del Disco

**Síntoma:** Borraste archivos de `storage/images/` o `storage/temp/` manualmente, pero siguen apareciendo en la interfaz.

**Solución:**

1. **Verificar qué se eliminará** (simulación):
```bash
curl -X POST http://localhost:3000/api/system/repair-records \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dryRun": true}'
```

2. **Aplicar cambios**:
```bash
curl -X POST http://localhost:3000/api/system/repair-records \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dryRun": false}'
```

3. **Limpiar caché**:
```bash
curl -X POST http://localhost:3000/api/system/clear-cache \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "content:*"}'
```

4. **Refrescar interfaz**: Hacer F5 o Ctrl+Shift+R

### Caso 3: Sincronización Completa (Recomendado)

**Síntoma:** Tienes inconsistencias múltiples y quieres limpiar todo.

**Solución:**

1. **Verificar estado actual**:
```bash
curl http://localhost:3000/api/system/integrity \
  -H "Authorization: Bearer $TOKEN"
```

2. **Simulación de sincronización**:
```bash
curl -X POST http://localhost:3000/api/system/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dryRun": true}'
```

3. **Revisar output** y confirmar que es correcto

4. **Aplicar sincronización**:
```bash
curl -X POST http://localhost:3000/api/system/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dryRun": false}'
```

## Validación Automática al Servir Archivos

El sistema **ya valida automáticamente** que los archivos existan al intentar servirlos:

**En `streamController.ts` (líneas 34-37):**
```typescript
if (!fs.existsSync(filePath)) {
  console.error(`File not found: ${filePath}`);
  throw new AppError('File not found on disk', 404);
}
```

**Resultado:** Si un archivo fue eliminado manualmente, al intentar reproducirlo se muestra error 404.

## Mantenimiento Preventivo

### Cron Job Recomendado

Ejecutar verificación de integridad **semanalmente**:

```bash
# /etc/cron.weekly/cdn-integrity-check
#!/bin/bash

TOKEN="tu_token_admin"
API_URL="http://localhost:3000"

# Verificar integridad
curl -s "$API_URL/api/system/integrity" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data.stats'

# Si hay inconsistencias, enviar alerta
# (implementar según tu sistema de notificaciones)
```

### Script de Sincronización Manual

Crear script auxiliar en `scripts/sync-system.sh`:

```bash
#!/bin/bash

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
API_URL="http://localhost:3000"
TOKEN_FILE="$HOME/.cdn-admin-token"

# Leer token
if [ -f "$TOKEN_FILE" ]; then
  TOKEN=$(cat "$TOKEN_FILE")
else
  echo -e "${RED}Error: No se encontró token en $TOKEN_FILE${NC}"
  exit 1
fi

echo -e "${YELLOW}=== Verificación de Integridad ===${NC}"
curl -s "$API_URL/api/system/integrity" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

echo ""
echo -e "${YELLOW}=== Simulación de Sincronización ===${NC}"
curl -s -X POST "$API_URL/api/system/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dryRun": true}' \
  | jq '.'

echo ""
read -p "¿Aplicar cambios? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${GREEN}Aplicando sincronización...${NC}"
  curl -s -X POST "$API_URL/api/system/sync" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"dryRun": false}' \
    | jq '.'

  echo -e "${GREEN}✓ Sincronización completada${NC}"
else
  echo -e "${YELLOW}Operación cancelada${NC}"
fi
```

**Uso:**
```bash
chmod +x scripts/sync-system.sh
./scripts/sync-system.sh
```

## Prevención de Inconsistencias

### ❌ NO Hacer:

- **NO eliminar archivos manualmente** con `rm`, `mv` o desde el explorador de archivos
- **NO modificar la BD directamente** sin actualizar el filesystem
- **NO copiar archivos** directamente a `storage/` sin crear el registro en BD

### ✅ SÍ Hacer:

- **Usar la interfaz de admin** para eliminar contenido
- **Usar endpoints de la API** para operaciones CRUD
- **Ejecutar sincronización** después de operaciones manuales de emergencia
- **Verificar integridad** regularmente

## Arquitectura de la Solución

```
┌─────────────────────────────────────────────┐
│         Interfaz de Usuario                 │
│  (Ve contenido desde caché/BD)              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│            Redis Cache                      │
│  TTL: 1 hora                                │
│  Keys: content:list:*, categories:*         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         PostgreSQL Database                 │
│  Tabla: content                             │
│  Campos: id, title, file_path, status       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│         Filesystem (storage/)               │
│  videos/, images/, documents/, etc.         │
│  Archivos nombrados por hash SHA-256        │
└─────────────────────────────────────────────┘
```

**Flujo de Validación:**

1. **Al listar contenido**: Cache → BD (no valida filesystem)
2. **Al servir archivo**: BD → Filesystem (valida que archivo existe)
3. **Al detectar error 404**: Se puede ejecutar sincronización manual

## Preguntas Frecuentes

### ¿Con qué frecuencia debo sincronizar?

En **uso normal, nunca**. El sistema mantiene consistencia automáticamente. Solo sincroniza si:
- Eliminaste archivos manualmente
- Migras contenido entre servidores
- Detectas inconsistencias

### ¿Es seguro ejecutar sincronización?

Sí, siempre usa `dryRun: true` primero para ver qué se eliminará. La sincronización **solo elimina** registros/archivos huérfanos, nunca contenido válido.

### ¿Qué pasa con los archivos en `temp/`?

Los archivos en `temp/` son **temporales** durante el upload. Se mueven a su carpeta final al aprobar. Si quedan residuales, `clean-files` los detecta como huérfanos.

### ¿Por qué mi contenido no aparece de inmediato?

**Caché de Redis**. El caché tiene TTL de 1 hora. Para ver cambios inmediatos:
1. Ejecuta `POST /api/system/clear-cache`
2. O espera 1 hora
3. O reinicia el servidor

---

**Última actualización**: 2026-03-13
