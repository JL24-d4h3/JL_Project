# Guía de Inicio Rápido (Quickstart)

Esta guía te ayudará a tener el proyecto funcionando en **menos de 1 hora**.

---

## Prerrequisitos

### Sistema Operativo
- Ubuntu Server 22.04 LTS (recomendado)
- Mínimo 8GB RAM, 4 CPU cores, 100GB disco libre

### Software Necesario
Todos estos se instalarán en los pasos siguientes:
- PostgreSQL 14+
- Redis 7+
- Node.js 18 LTS
- FFmpeg
- Git

---

## Paso 1: Preparar el Servidor (15 minutos)

### 1.1 Actualizar sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar PostgreSQL
```bash
# Instalar PostgreSQL 14
sudo apt install -y postgresql postgresql-contrib

# Verificar instalación
sudo systemctl status postgresql

# Debería mostrar: active (running)
```

### 1.3 Instalar Redis
```bash
sudo apt install -y redis-server

# Verificar instalación
redis-cli ping
# Respuesta esperada: PONG
```

### 1.4 Instalar Node.js 18 LTS
```bash
# Usando NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar instalación
node --version  # Debería mostrar: v18.x.x
npm --version   # Debería mostrar: 9.x.x
```

### 1.5 Instalar FFmpeg
```bash
sudo apt install -y ffmpeg

# Verificar instalación
ffmpeg -version  # Debería mostrar: version 4.4 o superior
```

### 1.6 Instalar herramientas adicionales
```bash
sudo apt install -y git curl wget vim htop
```

---

## Paso 2: Configurar Base de Datos (10 minutos)

### 2.1 Crear usuario y base de datos
```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Dentro de psql, ejecutar:
```
```sql
-- Crear usuario
CREATE USER cdn_user WITH PASSWORD 'tu_password_seguro_aqui';

-- Crear base de datos
CREATE DATABASE cdn_db OWNER cdn_user;

-- Habilitar extensiones
\c cdn_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Salir
\q
```

### 2.2 Verificar conexión
```bash
psql -U cdn_user -h localhost -d cdn_db
# Password: tu_password_seguro_aqui

# Si conecta correctamente, salir con \q
```

### 2.3 Configurar acceso remoto (opcional)
```bash
# Editar pg_hba.conf
sudo vim /etc/postgresql/14/main/pg_hba.conf

# Agregar esta línea (permite conexiones desde red local):
# host    cdn_db    cdn_user    192.168.1.0/24    md5

# Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

---

## Paso 3: Crear Estructura del Proyecto (5 minutos)

### 3.1 Clonar o crear proyecto
```bash
# Opción A: Si tienes el repo
cd ~
git clone https://github.com/tu-usuario/cdn-offline.git
cd cdn-offline

# Opción B: Si empiezas desde cero
cd /home/jleon/2026/PUCP/GTR/CDN
# (El código ya está aquí según tu workspace actual)
```

### 3.2 Crear estructura de directorios
```bash
# Crear directorios para almacenamiento
mkdir -p storage/{videos,documents,thumbnails,temp,archived}

# Crear directorio para backups
mkdir -p backups

# Crear directorio para logs
mkdir -p logs

# Verificar
tree -L 2
```

---

## Paso 4: Inicializar Backend (15 minutos)

### 4.1 Crear proyecto Node.js
```bash
# Ir al directorio del servidor
cd server
# (Si no existe, crearlo: mkdir server && cd server)

# Inicializar package.json
npm init -y

# Instalar dependencias principales
npm install express cors helmet dotenv
npm install pg redis ioredis
npm install bcrypt jsonwebtoken
npm install multer fluent-ffmpeg
npm install winston

# Instalar dependencias de desarrollo
npm install -D typescript @types/node @types/express
npm install -D ts-node nodemon
npm install -D eslint prettier
npm install -D jest @types/jest ts-jest supertest @types/supertest
```

### 4.2 Configurar TypeScript
```bash
# Crear tsconfig.json
npx tsc --init

# Copiar configuración recomendada (ver abajo)
```

Contenido de `tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### 4.3 Crear archivo de configuración
```bash
# Crear .env
cat > .env << 'EOF'
# Server
NODE_ENV=development
PORT=3000

# Database
DATABASE_URL=postgresql://cdn_user:tu_password_seguro_aqui@localhost:5432/cdn_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=cambia_esto_por_un_secret_aleatorio_largo
JWT_EXPIRES_IN=7d

# Storage
STORAGE_PATH=/home/jleon/2026/PUCP/GTR/CDN/storage
MAX_FILE_SIZE=524288000

# FFmpeg
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe
EOF

# ⚠️ IMPORTANTE: Cambiar password y JWT_SECRET
vim .env
```

### 4.4 Crear estructura básica
```bash
# Crear directorios
mkdir -p src/{config,routes,controllers,services,middleware,models,utils}

# Verificar
tree src/
```

---

## Paso 5: Inicializar Base de Datos (10 minutos)

### 5.1 Ejecutar scripts SQL
```bash
# Descargar o copiar el archivo database-design.md que creamos
# Extraer los scripts SQL y ejecutarlos

# Método 1: Desde archivo SQL completo (si lo tienes)
psql -U cdn_user -h localhost -d cdn_db -f scripts/schema.sql

# Método 2: Manualmente (copiar queries del doc database-design.md)
psql -U cdn_user -h localhost -d cdn_db

# Dentro de psql, copiar y pegar las secciones de:
# - Creación de tablas
# - Índices
# - Triggers
# - Vistas
```

### 5.2 Insertar datos de prueba
```sql
-- Conectar a la DB
psql -U cdn_user -h localhost -d cdn_db

-- Insertar usuario admin
INSERT INTO users (username, email, password_hash, full_name, role) VALUES
('admin', 'admin@cdn.local', '$2b$10$YourHashedPasswordHere', 'Administrador', 'admin');

-- Insertar categorías básicas
INSERT INTO categories (name, slug, description) VALUES
('Matemáticas', 'matematicas', 'Contenido de matemáticas'),
('Ciencias', 'ciencias', 'Contenido de ciencias'),
('Literatura', 'literatura', 'Contenido de literatura');

-- Salir
\q
```

---

## Paso 6: Crear Server Básico (5 minutos)

### 6.1 Crear index.ts
```bash
cat > src/index.ts << 'EOF'
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    version: '0.1.0'
  });
});

// Root
app.get('/', (req, res) => {
  res.json({ message: 'CDN Offline API' });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
EOF
```

### 6.2 Agregar scripts a package.json
```bash
# Editar package.json, agregar en "scripts":
```
```json
{
  "scripts": {
    "dev": "nodemon --exec ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "jest"
  }
}
```

### 6.3 Probar servidor
```bash
# Ejecutar en modo desarrollo
npm run dev

# En otra terminal, probar:
curl http://localhost:3000/health
# Respuesta esperada: {"status":"ok","timestamp":"...","version":"0.1.0"}
```

---

## Paso 7: Inicializar Frontend (10 minutos)

### 7.1 Crear proyecto React con Vite
```bash
# Volver al directorio raíz
cd ..

# Crear proyecto con Vite
npm create vite@latest client -- --template react-ts

# Entrar al directorio
cd client

# Instalar dependencias
npm install

# Instalar dependencias adicionales
npm install react-router-dom axios
npm install video.js
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 7.2 Configurar Tailwind
```bash
# Editar tailwind.config.js
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

# Editar src/index.css (agregar al inicio):
cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF
```

### 7.3 Probar frontend
```bash
# Ejecutar en modo desarrollo
npm run dev

# Abrir navegador en http://localhost:5173
```

---

## Paso 8: Prueba End-to-End (5 minutos)

### 8.1 Verificar todos los servicios
```bash
# Terminal 1: Backend
cd ~/cdn-offline/server
npm run dev
# Debería mostrar: 🚀 Server running on http://localhost:3000

# Terminal 2: Frontend
cd ~/cdn-offline/client
npm run dev
# Debería mostrar: Local: http://localhost:5173

# Terminal 3: Verificaciones
# PostgreSQL
sudo systemctl status postgresql
# Debería mostrar: active (running)

# Redis
redis-cli ping
# Debería mostrar: PONG

# FFmpeg
ffmpeg -version
# Debería mostrar versión
```

### 8.2 Verificar conectividad
```bash
# Test backend
curl http://localhost:3000/health

# Test frontend
curl http://localhost:5173

# Test base de datos desde backend (crear endpoint temporal)
psql -U cdn_user -h localhost -d cdn_db -c "SELECT COUNT(*) FROM categories;"
```

---

## Paso 9: Configuración de Red Local (Opcional, 10 minutos)

### 9.1 Configurar IP estática del servidor
```bash
# Ver interfaces de red
ip a

# Editar Netplan (Ubuntu 22.04)
sudo vim /etc/netplan/00-installer-config.yaml

# Configuración ejemplo:
```
```yaml
network:
  version: 2
  ethernets:
    eth0:  # Cambiar por tu interfaz
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

```bash
# Aplicar configuración
sudo netplan apply

# Verificar
ip a show eth0
```

### 9.2 Permitir acceso externo
```bash
# Configurar firewall
sudo ufw allow 3000/tcp  # Backend
sudo ufw allow 5173/tcp  # Frontend (desarrollo)
sudo ufw allow 80/tcp    # Nginx (producción)
sudo ufw allow 22/tcp    # SSH
sudo ufw enable

# Verificar
sudo ufw status
```

### 9.3 Probar desde otro dispositivo
```bash
# Desde tu laptop, probar:
curl http://192.168.1.100:3000/health

# O abrir en navegador:
# http://192.168.1.100:5173
```

---

## Paso 10: Próximos Pasos

¡Felicidades! Tu entorno de desarrollo está listo. Ahora puedes:

### Desarrollo Inmediato
1. **Implementar conexión a DB** en backend
   - Ver: `docs/database-design.md` para el schema completo
   - Crear `src/config/database.ts`

2. **Crear endpoints básicos**
   - GET /api/content
   - GET /api/content/:id
   - GET /api/stream/:id

3. **Diseñar UI en React**
   - Home page con lista de videos
   - Player page

### Seguir el Plan
Continuar con **Fase 1 - Semana 2** del roadmap:
- Ver: `docs/roadmap.md`
- Ver: `docs/implementation-plan.md`

### Recursos
- [Architecture](./docs/architecture.md)
- [Database Design](./docs/database-design.md)
- [Implementation Plan](./docs/implementation-plan.md)
- [Testing Strategy](./docs/testing-strategy.md)
- [FAQ](./docs/faq.md)

---

## Troubleshooting

### Error: "PostgreSQL connection refused"
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Si no está corriendo:
sudo systemctl start postgresql

# Ver logs de error:
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Error: "Redis connection refused"
```bash
# Verificar Redis
sudo systemctl status redis-server

# Iniciar si es necesario:
sudo systemctl start redis-server
```

### Error: "Permission denied" en /storage
```bash
# Dar permisos al usuario actual
sudo chown -R $USER:$USER /home/jleon/2026/PUCP/GTR/CDN/storage
chmod -R 755 /home/jleon/2026/PUCP/GTR/CDN/storage
```

### Error: "FFmpeg not found"
```bash
# Reinstalar FFmpeg
sudo apt install --reinstall ffmpeg

# Verificar path
which ffmpeg
# Actualizar FFMPEG_PATH en .env si es necesario
```

### Frontend no conecta con Backend
```bash
# Verificar CORS está habilitado en backend
# En src/index.ts debe haber:
app.use(cors());

# O configurar explícitamente:
app.use(cors({
  origin: 'http://localhost:5173',
  credentials: true
}));
```

---

## Comandos Útiles de Referencia

### Database
```bash
# Conectar a DB
psql -U cdn_user -h localhost -d cdn_db

# Backup
pg_dump -U cdn_user cdn_db > backup.sql

# Restore
psql -U cdn_user -d cdn_db < backup.sql

# Ver tablas
\dt

# Describir tabla
\d content
```

### Servicios
```bash
# Ver logs de PostgreSQL
sudo journalctl -u postgresql -f

# Ver logs de Redis
sudo journalctl -u redis-server -f

# Reiniciar servicios
sudo systemctl restart postgresql
sudo systemctl restart redis-server
```

### Desarrollo
```bash
# Backend (hot reload)
cd server && npm run dev

# Frontend (hot reload)
cd client && npm run dev

# Tests
cd server && npm test

# Build para producción
cd server && npm run build
cd client && npm run build
```

---

## ¿Necesitas Ayuda?

- 📖 Revisa la [FAQ](./docs/faq.md) para problemas comunes
- 📋 Consulta el [Roadmap](./docs/roadmap.md) para el plan completo
- 🏗️ Lee la [Architecture](./docs/architecture.md) para entender el diseño

---

**Última actualización**: 16 de Febrero de 2026
**Tiempo estimado total**: 60-90 minutos
**Nivel de dificultad**: Intermedio

¡Suerte con tu CDN offline! 🚀
