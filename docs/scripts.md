# Scripts de Utilidad

Colección de scripts bash para operaciones comunes del proyecto.

## Backup y Restore

### backup-daily.sh
Script para backup automático diario.

```bash
#!/bin/bash

# Configuración
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/jleon/2026/PUCP/GTR/CDN/backups"
DB_NAME="cdn_db"
DB_USER="cdn_user"
STORAGE_DIR="/home/jleon/2026/PUCP/GTR/CDN/storage"
RETENTION_DAYS=7

echo "=== CDN Backup Script ==="
echo "Started at: $(date)"

# Crear directorio de backup si no existe
mkdir -p "$BACKUP_DIR"

# 1. Backup de PostgreSQL
echo "[1/3] Backing up database..."
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    echo "✓ Database backup successful"
else
    echo "✗ Database backup failed!"
    exit 1
fi

# 2. Backup incremental de archivos
echo "[2/3] Backing up files (incremental)..."
rsync -av --link-dest="$BACKUP_DIR/latest" \
    "$STORAGE_DIR/" "$BACKUP_DIR/files_$DATE/"

if [ $? -eq 0 ]; then
    echo "✓ Files backup successful"
    # Actualizar symlink
    ln -sfn "$BACKUP_DIR/files_$DATE" "$BACKUP_DIR/latest"
else
    echo "✗ Files backup failed!"
    exit 1
fi

# 3. Limpiar backups antiguos
echo "[3/3] Cleaning old backups..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "files_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null

echo "✓ Cleanup complete"

# Calcular tamaño del backup
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Total backup size: $BACKUP_SIZE"

echo "=== Backup Complete ==="
echo "Finished at: $(date)"

# Opcional: Enviar notificación
# curl -X POST "http://localhost:3000/api/admin/notify" \
#   -H "Content-Type: application/json" \
#   -d "{\"message\": \"Backup completado: $BACKUP_SIZE\"}"
```

### restore.sh
Script para restaurar desde backup.

```bash
#!/bin/bash

# Configuración
BACKUP_DIR="/home/jleon/2026/PUCP/GTR/CDN/backups"
DB_NAME="cdn_db"
DB_USER="cdn_user"
STORAGE_DIR="/home/jleon/2026/PUCP/GTR/CDN/storage"

echo "=== CDN Restore Script ==="

# Listar backups disponibles
echo "Available backups:"
ls -lh "$BACKUP_DIR"/db_*.sql.gz | awk '{print $9}' | sort -r | head -5

# Solicitar fecha del backup
read -p "Enter backup date (YYYYMMDD_HHMMSS) or 'latest': " BACKUP_DATE

if [ "$BACKUP_DATE" == "latest" ]; then
    DB_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz | head -1)
    FILES_BACKUP="$BACKUP_DIR/latest"
else
    DB_BACKUP="$BACKUP_DIR/db_${BACKUP_DATE}.sql.gz"
    FILES_BACKUP="$BACKUP_DIR/files_${BACKUP_DATE}"
fi

# Verificar que existan los backups
if [ ! -f "$DB_BACKUP" ]; then
    echo "✗ Database backup not found: $DB_BACKUP"
    exit 1
fi

if [ ! -d "$FILES_BACKUP" ]; then
    echo "✗ Files backup not found: $FILES_BACKUP"
    exit 1
fi

echo "Will restore from:"
echo "  Database: $DB_BACKUP"
echo "  Files: $FILES_BACKUP"

# Confirmación
read -p "This will overwrite current data. Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Detener servicios
echo "[1/4] Stopping services..."
# Si usas PM2:
# pm2 stop cdn-server
# Si usas systemd:
# sudo systemctl stop cdn-server

# Restore database
echo "[2/4] Restoring database..."
dropdb -U "$DB_USER" "$DB_NAME"
createdb -U "$DB_USER" "$DB_NAME"
gunzip -c "$DB_BACKUP" | psql -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Database restored"
else
    echo "✗ Database restore failed!"
    exit 1
fi

# Restore files
echo "[3/4] Restoring files..."
rsync -av --delete "$FILES_BACKUP/" "$STORAGE_DIR/"

if [ $? -eq 0 ]; then
    echo "✓ Files restored"
else
    echo "✗ Files restore failed!"
    exit 1
fi

# Reiniciar servicios
echo "[4/4] Starting services..."
# pm2 start cdn-server
# sudo systemctl start cdn-server

echo "=== Restore Complete ==="
echo "Please verify the application is working correctly."
```

---

## Mantenimiento

### cleanup-storage.sh
Limpia archivos temporales y optimiza almacenamiento.

```bash
#!/bin/bash

STORAGE_DIR="/home/jleon/2026/PUCP/GTR/CDN/storage"
TEMP_DIR="$STORAGE_DIR/temp"
ARCHIVED_DIR="$STORAGE_DIR/archived"
DAYS_TO_KEEP=30

echo "=== Storage Cleanup Script ==="

# Limpiar directorio temporal
echo "[1/4] Cleaning temp directory..."
TEMP_SIZE_BEFORE=$(du -sh "$TEMP_DIR" 2>/dev/null | cut -f1)
find "$TEMP_DIR" -type f -mtime +1 -delete
TEMP_SIZE_AFTER=$(du -sh "$TEMP_DIR" 2>/dev/null | cut -f1)
echo "  Before: $TEMP_SIZE_BEFORE → After: $TEMP_SIZE_AFTER"

# Eliminar archivos archivados antiguos
echo "[2/4] Cleaning old archived files (>$DAYS_TO_KEEP days)..."
ARCHIVED_SIZE_BEFORE=$(du -sh "$ARCHIVED_DIR" 2>/dev/null | cut -f1)
find "$ARCHIVED_DIR" -type f -mtime +$DAYS_TO_KEEP -delete
ARCHIVED_SIZE_AFTER=$(du -sh "$ARCHIVED_DIR" 2>/dev/null | cut -f1)
echo "  Before: $ARCHIVED_SIZE_BEFORE → After: $ARCHIVED_SIZE_AFTER"

# Eliminar thumbnails huérfanos (sin contenido asociado)
echo "[3/4] Cleaning orphaned thumbnails..."
# Este script requerirá consultar la DB, ejemplo simplificado:
# find "$STORAGE_DIR/thumbnails" -type f -name "*.jpg" | while read thumb; do
#     id=$(basename "$thumb" .jpg)
#     psql -U cdn_user -d cdn_db -t -c "SELECT id FROM content WHERE id='$id'" | grep -q "$id"
#     if [ $? -ne 0 ]; then
#         echo "Removing orphaned thumbnail: $thumb"
#         rm "$thumb"
#     fi
# done

# Vacuum de PostgreSQL
echo "[4/4] Vacuuming database..."
psql -U cdn_user -d cdn_db -c "VACUUM ANALYZE;"

# Resumen
echo ""
echo "=== Storage Summary ==="
df -h "$STORAGE_DIR"

echo ""
echo "=== Cleanup Complete ==="
```

### monitor-system.sh
Monitorea el estado del sistema.

```bash
#!/bin/bash

echo "=== CDN System Monitor ==="
echo "Timestamp: $(date)"
echo ""

# 1. Servicios
echo "[Services Status]"
echo -n "PostgreSQL: "
systemctl is-active postgresql && echo "✓ Running" || echo "✗ Stopped"

echo -n "Redis: "
systemctl is-active redis-server && echo "✓ Running" || echo "✗ Stopped"

echo -n "CDN Server: "
# Si usas PM2:
# pm2 list | grep -q cdn-server && echo "✓ Running" || echo "✗ Stopped"
# Si usas systemd:
systemctl is-active cdn-server 2>/dev/null && echo "✓ Running" || echo "✗ Stopped"

echo ""

# 2. Uso de recursos
echo "[Resource Usage]"
echo "CPU:"
top -bn1 | grep "Cpu(s)" | awk '{print "  Usage: " $2 "%"}'

echo "Memory:"
free -h | awk 'NR==2{printf "  Used: %s / %s (%.2f%%)\n", $3, $2, $3*100/$2}'

echo "Disk:"
df -h / | awk 'NR==2{printf "  Used: %s / %s (%s)\n", $3, $2, $5}'

echo ""

# 3. Storage CDN
echo "[CDN Storage]"
STORAGE_DIR="/home/jleon/2026/PUCP/GTR/CDN/storage"
du -sh "$STORAGE_DIR"/* 2>/dev/null | sort -h

echo ""

# 4. Base de datos
echo "[Database Stats]"
psql -U cdn_user -d cdn_db -t -c "
SELECT 
    'Total Content: ' || COUNT(*) FROM content WHERE deleted_at IS NULL;
SELECT 
    'Total Users: ' || COUNT(*) FROM users WHERE is_active = true;
SELECT 
    'Total Storage: ' || pg_size_pretty(SUM(file_size)) FROM content WHERE deleted_at IS NULL;
SELECT 
    'Access Today: ' || COUNT(*) FROM access_log WHERE accessed_at > CURRENT_DATE;
"

echo ""

# 5. Logs recientes de error
echo "[Recent Errors (last 10)]"
if [ -f "/var/log/cdn/error.log" ]; then
    tail -10 /var/log/cdn/error.log
else
    echo "  No error log found"
fi

echo ""
echo "=== Monitor Complete ==="
```

---

## Instalación y Setup

### install-dependencies.sh
Instala todas las dependencias del sistema.

```bash
#!/bin/bash

echo "=== Installing CDN Dependencies ==="

# Verificar que estamos en Ubuntu/Debian
if [ ! -f /etc/debian_version ]; then
    echo "✗ This script is for Ubuntu/Debian only"
    exit 1
fi

# Actualizar sistema
echo "[1/6] Updating system..."
sudo apt update && sudo apt upgrade -y

# PostgreSQL
echo "[2/6] Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql

# Redis
echo "[3/6] Installing Redis..."
sudo apt install -y redis-server
sudo systemctl enable redis-server

# Node.js
echo "[4/6] Installing Node.js 18..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# FFmpeg
echo "[5/6] Installing FFmpeg..."
sudo apt install -y ffmpeg

# Herramientas adicionales
echo "[6/6] Installing additional tools..."
sudo apt install -y git curl wget vim htop build-essential

# Verificar instalaciones
echo ""
echo "=== Verification ==="
echo -n "PostgreSQL: "
psql --version

echo -n "Redis: "
redis-server --version

echo -n "Node.js: "
node --version

echo -n "npm: "
npm --version

echo -n "FFmpeg: "
ffmpeg -version | head -1

echo ""
echo "=== Installation Complete ==="
echo "Next steps:"
echo "1. Run ./setup-database.sh to configure the database"
echo "2. Run ./setup-project.sh to initialize the project"
```

### setup-database.sh
Configura la base de datos.

```bash
#!/bin/bash

DB_NAME="cdn_db"
DB_USER="cdn_user"
DB_PASSWORD="changeme123"

echo "=== Database Setup ==="

# Solicitar password
read -sp "Enter password for database user '$DB_USER': " DB_PASSWORD
echo ""
read -sp "Confirm password: " DB_PASSWORD_CONFIRM
echo ""

if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
    echo "✗ Passwords don't match!"
    exit 1
fi

# Crear usuario y database
echo "Creating database and user..."
sudo -u postgres psql <<EOF
-- Crear usuario
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Crear database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Conectar a la nueva database
\c $DB_NAME

-- Habilitar extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Dar permisos
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

if [ $? -eq 0 ]; then
    echo "✓ Database setup successful"
    
    # Guardar configuración en .env
    cat > .env.db << EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
EOF
    
    echo "✓ Database configuration saved to .env.db"
    echo "  Copy contents to your .env file"
else
    echo "✗ Database setup failed!"
    exit 1
fi

# Ejecutar schema
read -p "Run database schema now? (y/n): " RUN_SCHEMA
if [ "$RUN_SCHEMA" == "y" ]; then
    if [ -f "scripts/schema.sql" ]; then
        psql -U "$DB_USER" -h localhost -d "$DB_NAME" -f scripts/schema.sql
        echo "✓ Schema applied"
    else
        echo "⚠ schema.sql not found. Please create it manually."
    fi
fi

echo "=== Database Setup Complete ==="
```

---

## Cron Jobs

### crontab-example
Ejemplo de configuración de cron jobs.

```bash
# CDN Offline - Cron Jobs
# Editar con: crontab -e

# Backup diario a las 2 AM
0 2 * * * /home/jleon/2026/PUCP/GTR/CDN/scripts/backup-daily.sh >> /var/log/cdn/backup.log 2>&1

# Cleanup semanal (domingos a las 3 AM)
0 3 * * 0 /home/jleon/2026/PUCP/GTR/CDN/scripts/cleanup-storage.sh >> /var/log/cdn/cleanup.log 2>&1

# Monitor cada hora
0 * * * * /home/jleon/2026/PUCP/GTR/CDN/scripts/monitor-system.sh >> /var/log/cdn/monitor.log 2>&1

# Verificar eviction cada 4 horas
0 */4 * * * curl -X POST http://localhost:3000/api/admin/eviction/check >> /var/log/cdn/eviction.log 2>&1
```

---

## Uso de los Scripts

### Instalar scripts
```bash
# Crear directorio de scripts
mkdir -p scripts

# Copiar scripts desde este documento
# (Crear cada archivo script desde las secciones anteriores)

# Dar permisos de ejecución
chmod +x scripts/*.sh

# Crear directorio de logs
sudo mkdir -p /var/log/cdn
sudo chown $USER:$USER /var/log/cdn
```

### Ejecutar manualmente
```bash
# Backup
./scripts/backup-daily.sh

# Restore
./scripts/restore.sh

# Cleanup
./scripts/cleanup-storage.sh

# Monitor
./scripts/monitor-system.sh
```

### Configurar cron
```bash
# Editar crontab
crontab -e

# Copiar las líneas de crontab-example
# Guardar y salir

# Verificar
crontab -l

# Ver logs de cron
tail -f /var/log/cdn/*.log
```

---

Estos scripts te ayudarán a automatizar las operaciones comunes del proyecto.
