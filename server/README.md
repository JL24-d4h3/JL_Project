# CDN Offline - Backend Server

Servidor backend Node.js + Express + TypeScript para el sistema de distribución de contenido educativo offline.

## 🚀 Inicio Rápido

### 1. Instalar dependencias faltantes

```bash
npm install
```

### 2. Configurar variables de entorno

Edita el archivo `.env` con tus credenciales:

```bash
vim .env
```

**⚠️ IMPORTANTE:** Cambia estos valores:
- `JWT_SECRET`: Genera un string aleatorio largo (mínimo 32 caracteres)
- `DATABASE_URL`: Actualiza la contraseña de PostgreSQL

### 3. Ejecutar en desarrollo

```bash
npm run dev
```

El servidor estará disponible en: http://localhost:3000

### 4. Probar que funciona

```bash
curl http://localhost:3000/health
```

Deberías ver:
```json
{
  "status": "ok",
  "timestamp": "2026-02-16T...",
  "environment": "development"
}
```

## 📜 Scripts Disponibles

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Inicia el servidor en modo desarrollo con recarga automática |
| `npm run build` | Compila TypeScript a JavaScript en `dist/` |
| `npm start` | Ejecuta el servidor compilado (producción) |
| `npm test` | Ejecuta las pruebas con Jest |
| `npm run test:watch` | Ejecuta las pruebas en modo watch |
| `npm run lint` | Verifica el código con ESLint |
| `npm run lint:fix` | Corrige automáticamente problemas de linting |

## 📁 Estructura de Directorios (Próxima)

```
server/
├── src/
│   ├── config/         # Configuración (DB, Redis, etc.)
│   ├── controllers/    # Controladores de rutas
│   ├── middleware/     # Middleware personalizado
│   ├── models/         # Modelos de datos
│   ├── routes/         # Definición de rutas
│   ├── services/       # Lógica de negocio
│   ├── utils/          # Utilidades
│   └── index.ts        # Punto de entrada ✅
├── dist/               # Código compilado (generado)
├── .env                # Variables de entorno ✅
├── .env.example        # Ejemplo de variables ✅
├── tsconfig.json       # Configuración TypeScript ✅
├── jest.config.js      # Configuración Jest ✅
└── package.json        # Dependencias ✅
```

## 🔧 Próximos Pasos

1. **Configurar base de datos**: Ejecutar scripts SQL de `docs/database-design.md`
2. **Crear estructura**: Carpetas `config/`, `controllers/`, `routes/`, etc.
3. **Implementar autenticación**: JWT + bcrypt según `docs/architecture.md`
4. **Implementar streaming**: Rutas de video con HTTP Range requests
5. **Implementar upload**: Multer + FFmpeg para procesamiento

## 🐛 Troubleshooting

### Error: "Cannot find module 'express'"
```bash
npm install
```

### Error: TypeScript compilation errors
```bash
npm run lint:fix
npx tsc --noEmit  # Verificar errores sin compilar
```

### Puerto 3000 en uso
Cambia `PORT=3001` en `.env`
