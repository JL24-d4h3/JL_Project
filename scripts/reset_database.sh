#!/usr/bin/env bash
# reset_database.sh — Borra y recrea la base de datos cdn_dev desde cero.
# Solo para desarrollo. NO ejecutar en producción.

set -e

DB_NAME="cdn_dev"
DB_USER="cdn_user"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  RESET BASE DE DATOS: $DB_NAME"
echo "  ADVERTENCIA: todos los datos se borrarán"
echo "============================================"
read -rp "¿Continuar? (s/N): " confirm
[[ "$confirm" =~ ^[sS]$ ]] || { echo "Cancelado."; exit 0; }

echo ""
echo "1/5  Terminando conexiones activas y eliminando base de datos..."
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "2/5  Creando base de datos (propietario: $DB_USER)..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "3/5  Aplicando schema v2 + datos iniciales..."
sudo -u postgres psql -d "$DB_NAME" < "$SCRIPTS_DIR/init_database_v2.sql"

echo "4/5  Habilitando tipo 'code'..."
sudo -u postgres psql -d "$DB_NAME" < "$SCRIPTS_DIR/add_code_type.sql"

echo "5/6  Cargando categorías educativas completas..."
sudo -u postgres psql -d "$DB_NAME" < "$SCRIPTS_DIR/seed_categories_v2.sql"

echo "6/6  Otorgando permisos a $DB_USER..."
sudo -u postgres psql -d "$DB_NAME" -c "
  GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $DB_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO $DB_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
"

echo ""
echo "============================================"
echo "  RESET COMPLETADO"
echo "  admin   / admin123   → superadmin (panel admin)"
echo "  docente / teacher123 → teacher    (sender/subida)"
echo "============================================"
