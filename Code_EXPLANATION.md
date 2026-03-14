# 💻 Code Explanation - Guía Técnica del Código

**Fecha**: 17 de febrero de 2026  
**Proyecto**: Sistema CDN Offline  
**Propósito**: Explicar las funciones principales del código

---

## 📋 ÍNDICE

1. [Patrones de TypeScript](#1-patrones-de-typescript)
2. [Configuración y Setup](#2-configuración-y-setup)
3. [Middleware Explicado](#3-middleware-explicado)
4. [Controllers en Detalle](#4-controllers-en-detalle)
5. [Services Layer](#5-services-layer)
6. [Base de Datos](#6-base-de-datos)
7. [Manejo de Errores](#7-manejo-de-errores)
8. [Utilidades Comunes](#8-utilidades-comunes)
9. [Motor IA — ai_engine](#9-motor-ia--ai_engine)
10. [Search UI — AIOverview](#10-search-ui--aioverviewtsx)

---

## 1. PATRONES DE TYPESCRIPT

### async/await vs Promises vs Callbacks

**Callbacks (Estilo antiguo - NO usar):**
```typescript
import fs from 'fs';

fs.readFile('file.txt', 'utf8', (err, data) => {
    if (err) {
        console.error(err);
        return;
    }
    
    fs.writeFile('output.txt', data, (err) => {
        if (err) {
            console.error(err);
            return;
        }
        console.log('Done');
    });
});
// ⚠️ Callback hell: difícil de leer
```

**Promises (Estilo intermedio):**
```typescript
import { readFile, writeFile } from 'fs/promises';

readFile('file.txt', 'utf8')
    .then(data => writeFile('output.txt', data))
    .then(() => console.log('Done'))
    .catch(err => console.error(err));
// ✅ Mejor, pero aún verboso
```

**async/await (Estilo moderno - USAR):**
```typescript
import { readFile, writeFile } from 'fs/promises';

async function processFile() {
    try {
        const data = await readFile('file.txt', 'utf8');
        await writeFile('output.txt', data);
        console.log('Done');
    } catch (err) {
        console.error(err);
    }
}
// ✅✅ Mejor: se lee como código síncrono
```

**En nuestro proyecto:**
```typescript
// authController.ts
export const login = async (req: Request, res: Response) => {
    try {
        // Esperar a que DB responda (asíncrono)
        const result = await query('SELECT * FROM users WHERE username = $1', [username]);
        
        // Esperar a bcrypt (asíncrono)
        const isValid = await bcrypt.compare(password, user.password_hash);
        
        // Múltiples awaits en secuencia
        const token = jwt.sign({ id, username, role }, JWT_SECRET);
        await query('INSERT INTO sessions ...');
        
        res.json({ token });
    } catch (error) {
        // Captura errores de cualquier await
        res.status(500).json({ error: error.message });
    }
};
```

### Tipos e Interfaces

**Interface (para objetos):**
```typescript
// models/index.ts
export interface User {
    id: string;
    username: string;
    email: string;
    role: UserRole;
    is_active: boolean;
    created_at: Date;
}

// Uso:
const user: User = {
    id: '123',
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    is_active: true,
    created_at: new Date()
};
```

**Type (para unions, aliases):**
```typescript
// Enum-like
export type UserRole = 'student' | 'teacher' | 'admin' | 'superadmin';

// Union types
export type ContentType = 'video' | 'pdf' | 'audio' | 'image' | 'document';

// Función type
export type QueryFunction = (sql: string, params?: any[]) => Promise<any>;
```

**Generics:**
```typescript
// API Response genérica
interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}

// Uso:
const userResponse: ApiResponse<User> = {
    success: true,
    data: { id: '123', username: 'admin', ... }
};

const contentResponse: ApiResponse<Content[]> = {
    success: true,
    data: [{ id: '1', title: 'Video 1', ... }]
};
```

### Import/Export (ES Modules)

**Named exports (múltiples por archivo):**
```typescript
// utils/cache.ts
export const cacheGet = async (key: string) => { ... };
export const cacheSet = async (key: string, value: any, ttl: number) => { ... };
export const cacheDelete = async (pattern: string) => { ... };

// Import:
import { cacheGet, cacheSet } from './utils/cache.js';
// ⚠️ Nota el .js aunque el archivo sea .ts (ES modules requirement)
```

**Default export (uno por archivo):**
```typescript
// config/database.ts
const pool = new Pool({ ... });
export default pool;

// Import:
import pool from './config/database.js';
```

**Mixed:**
```typescript
// controllers/authController.ts
export const login = async (req, res) => { ... };
export const logout = async (req, res) => { ... };
export const getMe = async (req, res) => { ... };

// Import:
import { login, logout, getMe } from '../controllers/authController.js';
```

**¿Por qué .js al importar archivos .ts?**
TypeScript compila a JavaScript:
```
src/controllers/authController.ts  →  dist/controllers/authController.js
```
Los imports en el código compilado buscan .js, no .ts.

---

## 2. CONFIGURACIÓN Y SETUP

### Database Connection Pool

**config/database.ts:**
```typescript
import { Pool } from 'pg';

// Pool de conexiones (reusa conexiones en lugar de crear/cerrar cada vez)
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,  // postgresql://user:pass@host:port/db
    max: 20,  // Máximo 20 conexiones simultáneas
    idleTimeoutMillis: 30000,  // Cierra conexiones inactivas después de 30s
    connectionTimeoutMillis: 2000,  // Timeout al conectar (2s)
});

// Función helper para queries
export const query = async (text: string, params?: any[]) => {
    const start = Date.now();
    
    try {
        const result = await pool.query(text, params);
        const duration = Date.now() - start;
        
        console.log('Executed query', { text, duration, rows: result.rowCount });
        return result;
    } catch (error) {
        console.error('Query error', { text, error: error.message });
        throw error;
    }
};

// Para transacciones (múltiples queries atómicas)
export const getClient = async () => {
    const client = await pool.connect();
    
    return {
        query: (text: string, params?: any[]) => client.query(text, params),
        release: () => client.release(),
        
        // Helper para transacciones
        transaction: async (callback: (query: any) => Promise<void>) => {
            try {
                await client.query('BEGIN');
                await callback(client.query.bind(client));
                await client.query('COMMIT');
            } catch (error) {
                await client.query('ROLLBACK');
                throw error;
            } finally {
                client.release();
            }
        }
    };
};

export default pool;
```

**¿Cómo usar?**

**Query simple:**
```typescript
const result = await query('SELECT * FROM users WHERE id = $1', [userId]);
const user = result.rows[0];
```

**Query con transacción:**
```typescript
const client = await getClient();
try {
    await client.transaction(async (query) => {
        // Todas estas queries son atómicas (todas o ninguna)
        await query('UPDATE users SET balance = balance - 100 WHERE id = $1', [userId]);
        await query('INSERT INTO transactions (user_id, amount) VALUES ($1, $2)', [userId, -100]);
        await query('UPDATE content SET access_count = access_count + 1 WHERE id = $1', [contentId]);
    });
} catch (error) {
    console.error('Transaction failed', error);
}
```

### Redis Cache Configuration

**config/redis.ts:**
```typescript
import Redis from 'ioredis';

// Cliente Redis
const redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
    db: 0,  // Database 0 (Redis tiene 16 DBs numeradas)
    retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;  // Retry con backoff exponencial
    },
    maxRetriesPerRequest: 3
});

// Event listeners
redis.on('connect', () => console.log('✅ Redis connected'));
redis.on('error', (err) => console.error('❌ Redis error:', err));

// Función helper: SET con TTL
export const cacheSet = async (key: string, value: any, ttl: number = 300) => {
    try {
        const serialized = JSON.stringify(value);
        await redis.setex(key, ttl, serialized);  // SET + EXPIRE en un comando
        return true;
    } catch (error) {
        console.error('Cache set error:', error);
        return false;
    }
};

// Función helper: GET con auto-parse JSON
export const cacheGet = async (key: string): Promise<any | null> => {
    try {
        const cached = await redis.get(key);
        if (!cached) return null;
        
        return JSON.parse(cached);
    } catch (error) {
        console.error('Cache get error:', error);
        return null;
    }
};

// Función helper: DELETE con pattern
export const cacheDelete = async (pattern: string) => {
    try {
        // SCAN + DELETE (KEYS * es peligroso en producción)
        const stream = redis.scanStream({ match: pattern });
        const keys: string[] = [];
        
        stream.on('data', (resultKeys: string[]) => {
            keys.push(...resultKeys);
        });
        
        await new Promise((resolve) => stream.on('end', resolve));
        
        if (keys.length > 0) {
            await redis.del(...keys);
            console.log(`Deleted ${keys.length} cache keys matching ${pattern}`);
        }
        
        return keys.length;
    } catch (error) {
        console.error('Cache delete error:', error);
        return 0;
    }
};

export default redis;
```

**¿Cómo usar cache?**

```typescript
// En contentController.ts
import { cacheGet, cacheSet, cacheDelete } from '../config/redis.js';

export const getContent = async (req: Request, res: Response) => {
    const { category, type, search } = req.query;
    const cacheKey = `content:${JSON.stringify(req.query)}`;
    
    // 1. Intentar leer de cache
    const cached = await cacheGet(cacheKey);
    if (cached) {
        console.log('📦 Cache hit');
        return res.json({ success: true, data: cached, source: 'cache' });
    }
    
    console.log('🔍 Cache miss, querying DB');
    
    // 2. Query DB
    const result = await query('SELECT * FROM content ...');
    const data = result.rows;
    
    // 3. Guardar en cache (5 minutos)
    await cacheSet(cacheKey, data, 300);
    
    res.json({ success: true, data, source: 'database' });
};

// Al crear/actualizar/eliminar contenido, invalidar cache
export const createContent = async (req: Request, res: Response) => {
    // ... crear contenido
    
    // Invalidar todo el cache de content
    await cacheDelete('content:*');
    
    res.json({ success: true });
};
```

### Environment Variables

**.env:**
```bash
# Database
DATABASE_URL=postgresql://cdn_user:password@localhost:5432/cdn_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET=your-super-secret-key-min-32-chars-long

# Upload
MAX_FILE_SIZE=524288000
STORAGE_PATH=/home/jleon/2026/PUCP/GTR/CDN/server/storage
FFMPEG_PATH=/usr/bin/ffmpeg

# Server
PORT=3000
NODE_ENV=development
```

**Cargar .env:**
```typescript
// index.ts (primero de todo)
import dotenv from 'dotenv';
dotenv.config();  // Lee .env y añade a process.env

// Ahora se puede usar:
const port = parseInt(process.env.PORT || '3000');
const jwtSecret = process.env.JWT_SECRET!;  // ! = non-null assertion
```

---

## 3. MIDDLEWARE EXPLICADO

### ¿Qué es Middleware?

Funciones que se ejecutan **entre** la petición y el controller.

```
Request → Middleware 1 → Middleware 2 → ... → Controller → Response
```

### Authenticate Middleware

**middleware/auth.ts:**
```typescript
import jwt from 'jsonwebtoken';
import { query } from '../config/database.js';
import crypto from 'crypto';

export const authenticate = async (
    req: Request, 
    res: Response, 
    next: NextFunction
) => {
    try {
        // 1. Extraer token del header
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ 
                error: 'No token provided' 
            });
        }
        
        const token = authHeader.substring(7);  // Remove "Bearer "
        
        // 2. Verificar firma del JWT
        const decoded = jwt.verify(token, process.env.JWT_SECRET!) as JWTPayload;
        // Si la firma no coincide o expiró, jwt.verify lanza error
        
        // 3. Hash del token para buscar sesión
        const tokenHash = crypto
            .createHash('sha256')
            .update(token)
            .digest('hex');
        
        // 4. Verificar sesión activa en DB
        const sessionResult = await query(`
            SELECT s.*, u.*
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token_hash = $1
              AND s.is_active = true
              AND s.expires_at > NOW()
        `, [tokenHash]);
        
        if (sessionResult.rows.length === 0) {
            return res.status(401).json({ 
                error: 'Invalid or expired session' 
            });
        }
        
        const user = sessionResult.rows[0];
        
        // 5. Verificar usuario activo
        if (!user.is_active) {
            return res.status(403).json({ 
                error: 'Account is inactive' 
            });
        }
        
        // 6. Actualizar last_activity (async, no await)
        query('UPDATE sessions SET last_activity = NOW() WHERE token_hash = $1', [tokenHash]);
        
        // 7. Adjuntar usuario al request (para usar en controller)
        req.user = {
            id: user.user_id,
            username: user.username,
            role: user.role,
            email: user.email
        };
        
        // 8. Continuar al siguiente middleware o controller
        next();
        
    } catch (error) {
        if (error.name === 'JsonWebTokenError') {
            return res.status(401).json({ error: 'Invalid token' });
        }
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({ error: 'Token expired' });
        }
        
        console.error('Auth middleware error:', error);
        return res.status(500).json({ error: 'Authentication failed' });
    }
};
```

**¿Cómo se usa?**

```typescript
// routes/upload.ts
import { authenticate } from '../middleware/auth.js';
import { uploadContent } from '../controllers/uploadController.js';

router.post('/upload', authenticate, uploadContent);
//                     ↑ Middleware ejecuta antes de controller
```

**Flujo:**
```
POST /api/upload
↓
authenticate middleware:
- Extrae token
- Verifica JWT
- Busca sesión
- Adjunta req.user
↓
uploadContent controller:
- Puede usar req.user.id
- Sabe quién está subiendo
```

### Authorize Middleware

**middleware/auth.ts:**
```typescript
export const authorize = (...allowedRoles: UserRole[]) => {
    return (req: Request, res: Response, next: NextFunction) => {
        // authenticate debe ejecutarse antes (req.user existe)
        if (!req.user) {
            return res.status(401).json({ 
                error: 'Authentication required' 
            });
        }
        
        // Verificar rol
        if (!allowedRoles.includes(req.user.role)) {
            return res.status(403).json({ 
                error: 'Insufficient permissions',
                required: allowedRoles,
                current: req.user.role
            });
        }
        
        next();
    };
};
```

**¿Cómo se usa?**

```typescript
// routes/upload.ts
router.post(
    '/upload',
    authenticate,  // Primero: verificar JWT
    authorize('superadmin', 'admin'),  // Segundo: verificar rol
    uploadContent  // Tercero: ejecutar lógica
);

// Solo superadmin y admin pueden subir videos
```

**Para modificar permisos:**
```typescript
// Permitir que teachers también suban:
authorize('superadmin', 'admin', 'teacher')

// Solo superadmin:
authorize('superadmin')
```

### Upload Middleware (Multer)

**middleware/upload.ts:**
```typescript
import multer from 'multer';
import path from 'path';
import crypto from 'crypto';

// Configuración de almacenamiento
const storage = multer.diskStorage({
    // Carpeta destino
    destination: (req, file, cb) => {
        const tempDir = path.join(process.env.STORAGE_PATH!, 'temp');
        cb(null, tempDir);
    },
    
    // Nombre del archivo
    filename: (req, file, cb) => {
        const basename = path.parse(file.originalname).name;
        const ext = path.extname(file.originalname);
        const timestamp = Date.now();
        const random = crypto.randomBytes(4).toString('hex');
        
        // Resultado: "video_1640995200_abc123.mp4"
        const filename = `${basename}_${timestamp}_${random}${ext}`;
        cb(null, filename);
    }
});

// Validación de archivos
const fileFilter = (
    req: Express.Request,
    file: Express.Multer.File,
    cb: multer.FileFilterCallback
) => {
    const ext = path.extname(file.originalname).toLowerCase();
    
    // Extensiones permitidas
    const allowedExtensions = [
        '.mp4', '.webm', '.ogg', '.mov',  // Videos
        '.pdf', '.doc', '.docx',  // Documentos
        '.jpg', '.jpeg', '.png', '.gif', '.webp',  // Imágenes
        '.mp3', '.wav', '.m4a'  // Audios
    ];
    
    // 1. Validar extensión
    if (!allowedExtensions.includes(ext)) {
        return cb(new Error(`File type ${ext} not allowed`));
    }
    
    // 2. Validar MIME type (menos restrictivo para curl)
    const allowedMimes = [
        'video/', 'application/pdf', 'application/msword',
        'image/', 'audio/', 'application/octet-stream'
    ];
    
    const mimeValid = allowedMimes.some(mime => 
        file.mimetype.startsWith(mime)
    );
    
    if (!mimeValid) {
        return cb(new Error(`MIME type ${file.mimetype} not allowed`));
    }
    
    // Todo OK
    cb(null, true);
};

// Middleware de Multer
export const uploadMiddleware = multer({
    storage,
    fileFilter,
    limits: {
        fileSize: parseInt(process.env.MAX_FILE_SIZE || '524288000'),  // 500 MB
        files: 1  // Solo 1 archivo por petición
    }
});

// Helpers para determinar tipo
export const getContentTypeFromMime = (mimeType: string, filename?: string): ContentType => {
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType === 'application/pdf') return 'pdf';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('image/')) return 'image';
    
    // Fallback por extensión si MIME es octet-stream
    if (filename && mimeType === 'application/octet-stream') {
        const ext = path.extname(filename).toLowerCase();
        if (['.mp4', '.webm', '.mov'].includes(ext)) return 'video';
        if (['.mp3', '.wav'].includes(ext)) return 'audio';
        if (['.jpg', '.png', '.gif'].includes(ext)) return 'image';
    }
    
    return 'document';
};

export const getStorageFolderFromMime = (mimeType: string, filename?: string): string => {
    const type = getContentTypeFromMime(mimeType, filename);
    
    switch (type) {
        case 'video': return 'videos';
        case 'audio': return 'audio';
        case 'image': return 'images';
        case 'pdf': return 'documents';
        default: return 'documents';
    }
};
```

**¿Cómo funciona Multer?**

1. **Cliente envía FormData:**
```javascript
const formData = new FormData();
formData.append('file', videoFile);
formData.append('title', 'Mi Video');

fetch('/api/upload', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer TOKEN' },
    body: formData
});
```

2. **Multer intercepta:**
```
POST /api/upload
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...

------WebKitFormBoundary...
Content-Disposition: form-data; name="file"; filename="video.mp4"
Content-Type: video/mp4

[binary data]
------WebKitFormBoundary...
Content-Disposition: form-data; name="title"

Mi Video
------WebKitFormBoundary...--
```

3. **Multer parsea y guarda:**
```
- Extrae file de multipart
- Ejecuta fileFilter (valida extensión y MIME)
- Guarda en temp/ con nombre único
- Añade req.file al request:
  {
    fieldname: 'file',
    originalname: 'video.mp4',
    mimetype: 'video/mp4',
    size: 50000000,
    filename: 'video_1640995200_abc123.mp4',
    path: '/storage/temp/video_1640995200_abc123.mp4'
  }
```

4. **Controller recibe req.file:**
```typescript
export const uploadContent = async (req: Request, res: Response) => {
    const file = req.file!;  // Multer garantiza que existe
    console.log(file.path);  // /storage/temp/video_1640995200_abc123.mp4
    
    // Procesar...
};
```

---

## 4. CONTROLLERS EN DETALLE

### authController.ts

#### login()

```typescript
export const login = async (req: Request, res: Response) => {
    try {
        // 1. Extraer credenciales
        const { username, password } = req.body;
        
        if (!username || !password) {
            return res.status(400).json({ 
                error: 'Username and password required' 
            });
        }
        
        // 2. Buscar usuario
        const userResult = await query(
            'SELECT * FROM users WHERE username = $1',
            [username]
        );
        
        if (userResult.rows.length === 0) {
            // No revelamos si usuario existe (seguridad)
            return res.status(401).json({ 
                error: 'Invalid credentials' 
            });
        }
        
        const user = userResult.rows[0];
        
        // 3. Verificar cuenta bloqueada
        if (user.locked_until && new Date(user.locked_until) > new Date()) {
            const remainingMinutes = Math.ceil(
                (new Date(user.locked_until).getTime() - Date.now()) / 60000
            );
            return res.status(423).json({ 
                error: `Account locked. Try again in ${remainingMinutes} minutes` 
            });
        }
        
        // 4. Verificar password
        const isValid = await bcrypt.compare(password, user.password_hash);
        
        if (!isValid) {
            // Incrementar intentos fallidos
            const newAttempts = user.login_attempts + 1;
            
            if (newAttempts >= 5) {
                // Bloquear cuenta 15 minutos
                await query(`
                    UPDATE users 
                    SET login_attempts = $1,
                        locked_until = NOW() + INTERVAL '15 minutes'
                    WHERE id = $2
                `, [newAttempts, user.id]);
                
                return res.status(423).json({ 
                    error: 'Account locked due to too many failed attempts. Try again in 15 minutes' 
                });
            }
            
            await query(
                'UPDATE users SET login_attempts = $1 WHERE id = $2',
                [newAttempts, user.id]
            );
            
            return res.status(401).json({ 
                error: `Invalid credentials. ${5 - newAttempts} attempts remaining` 
            });
        }
        
        // 5. Password válido: reset intentos y actualizar last_login
        await query(`
            UPDATE users 
            SET login_attempts = 0,
                last_login = NOW()
            WHERE id = $1
        `, [user.id]);
        
        // 6. Generar JWT
        const token = jwt.sign(
            {
                id: user.id,
                username: user.username,
                role: user.role
            },
            process.env.JWT_SECRET!,
            { expiresIn: '7d' }
        );
        
        // 7. Hash del token para guardar en DB
        const tokenHash = crypto
            .createHash('sha256')
            .update(token)
            .digest('hex');
        
        // 8. Crear sesión
        await query(`
            INSERT INTO sessions (
                user_id, 
                token_hash, 
                ip_address, 
                user_agent, 
                expires_at
            ) VALUES ($1, $2, $3, $4, NOW() + INTERVAL '7 days')
        `, [
            user.id,
            tokenHash,
            req.ip,
            req.headers['user-agent'] || 'unknown'
        ]);
        
        // 9. Responder
        res.json({
            success: true,
            data: {
                token,
                user: {
                    id: user.id,
                    username: user.username,
                    email: user.email,
                    role: user.role,
                    full_name: user.full_name
                },
                expires_in: 7 * 24 * 60 * 60  // 7 días en segundos
            }
        });
        
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ error: 'Login failed' });
    }
};
```

**Características de seguridad:**
- ✅ No revela si username existe
- ✅ Bloqueo después de 5 intentos fallidos
- ✅ bcrypt para comparar passwords (lento, protege brute force)
- ✅ JWT firmado (no se puede falsificar)
- ✅ Token hasheado en DB (si hackean DB, no tienen tokens reales)
- ✅ Tracking de IP y user agent

### contentController.ts

#### getContent()

```typescript
export const getContent = async (req: Request, res: Response) => {
    try {
        // 1. Extraer query params
        const {
            page = '1',
            limit = '20',
            category,
            type,
            search,
            featured,
            sort = 'created_at_desc'
        } = req.query;
        
        const pageNum = parseInt(page as string);
        const limitNum = parseInt(limit as string);
        const offset = (pageNum - 1) * limitNum;
        
        // 2. Cache key único para esta query
        const cacheKey = `content:${JSON.stringify(req.query)}`;
        const cached = await cacheGet(cacheKey);
        
        if (cached) {
            return res.json({ 
                success: true, 
                data: cached, 
                source: 'cache' 
            });
        }
        
        // 3. Construir WHERE dinámicamente
        const conditions: string[] = [
            'c.deleted_at IS NULL',
            "c.status = 'active'"
        ];
        const params: any[] = [];
        let paramIndex = 1;
        
        if (category) {
            conditions.push(`c.category_id = $${paramIndex++}`);
            params.push(category);
        }
        
        if (type) {
            conditions.push(`c.type = $${paramIndex++}`);
            params.push(type);
        }
        
        if (featured === 'true') {
            conditions.push(`c.is_featured = true`);
        }
        
        if (search) {
            // Full-text search en español + ILIKE fallback
            conditions.push(`(
                to_tsvector('spanish', c.title || ' ' || COALESCE(c.description, '')) 
                @@ plainto_tsquery('spanish', $${paramIndex})
                OR c.title ILIKE $${paramIndex + 1}
            )`);
            params.push(search, `%${search}%`);
            paramIndex += 2;
        }
        
        const whereClause = conditions.join(' AND ');
        
        // 4. Determinar ORDER BY
        const sortMap: Record<string, string> = {
            'created_at_desc': 'c.created_at DESC',
            'created_at_asc': 'c.created_at ASC',
            'title_asc': 'c.title ASC',
            'title_desc': 'c.title DESC',
            'access_count_desc': 'c.access_count DESC'
        };
        const orderBy = sortMap[sort as string] || 'c.created_at DESC';
        
        // 5. Contar total (para paginación)
        const countResult = await query(
            `SELECT COUNT(*) FROM content c WHERE ${whereClause}`,
            params
        );
        const totalItems = parseInt(countResult.rows[0].count);
        const totalPages = Math.ceil(totalItems / limitNum);
        
        // 6. Query principal
        params.push(limitNum, offset);
        const result = await query(`
            SELECT 
                c.*,
                cat.name as category_name,
                cat.slug as category_slug,
                u.username as created_by_username,
                u.full_name as created_by_name
            FROM content c
            LEFT JOIN categories cat ON c.category_id = cat.id
            LEFT JOIN users u ON c.created_by = u.id
            WHERE ${whereClause}
            ORDER BY ${orderBy}
            LIMIT $${paramIndex++} OFFSET $${paramIndex}
        `, params);
        
        // 7. Formatear respuesta
        const data = {
            items: result.rows,
            pagination: {
                page: pageNum,
                limit: limitNum,
                total_items: totalItems,
                total_pages: totalPages,
                has_next: pageNum < totalPages,
                has_prev: pageNum > 1
            }
        };
        
        // 8. Cachear (5 minutos)
        await cacheSet(cacheKey, data, 300);
        
        res.json({ 
            success: true, 
            data, 
            source: 'database' 
        });
        
    } catch (error) {
        console.error('Get content error:', error);
        res.status(500).json({ error: 'Failed to fetch content' });
    }
};
```

**Características:**
- ✅ Filtros dinámicos (WHERE construido en runtime)
- ✅ Full-text search con índice GIN
- ✅ Paginación completa
- ✅ Cache con key única por query
- ✅ JOIN con categorías y usuarios
- ✅ Query parameterizada (protege SQL injection)

### uploadController.ts

#### uploadContent()

```typescript
export const uploadContent = async (req: Request, res: Response) => {
    let tempPath: string | null = null;
    let finalPath: string | null = null;
    
    try {
        // 1. Validar archivo existe (Multer debe haberlo guardado)
        if (!req.file) {
            return res.status(400).json({ 
                error: 'No file uploaded' 
            });
        }
        
        const file = req.file;
        tempPath = file.path;
        
        // 2. Extraer metadata del request
        const { title, description, category_id, is_featured = false } = req.body;
        const userId = req.user!.id;  // authenticate garantiza que existe
        
        if (!title || !category_id) {
            await storageService.cleanupFile(tempPath);
            return res.status(400).json({ 
                error: 'Title and category_id required' 
            });
        }
        
        // 3. Calcular hash SHA-256 del archivo
        console.log('📊 Calculating file hash...');
        const fileHash = await storageService.calculateFileHash(tempPath);
        console.log(`✅ Hash: ${fileHash}`);
        
        // 4. Verificar duplicados
        const duplicate = await storageService.checkDuplicateHash(fileHash);
        if (duplicate) {
            await storageService.cleanupFile(tempPath);
            return res.status(409).json({
                error: 'File already exists',
                existing_content: duplicate
            });
        }
        
        // 5. Generar slug único
        const baseSlug = title
            .normalize('NFD')  // Descomponer acentos
            .replace(/[\u0300-\u036f]/g, '')  // Remover acentos
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')  // Espacios → guiones
            .replace(/^-+|-+$/g, '');  // Remover guiones al inicio/fin
        
        // Verificar unicidad
        let slug = baseSlug;
        let counter = 1;
        while (true) {
            const existing = await query(
                'SELECT id FROM content WHERE slug = $1',
                [slug]
            );
            if (existing.rows.length === 0) break;
            slug = `${baseSlug}-${counter++}`;
        }
        
        // 6. Mover archivo a storage permanente
        console.log('📁 Moving file to permanent storage...');
        finalPath = await storageService.moveToStorage(
            tempPath,
            fileHash,
            file.mimetype,
            file.originalname
        );
        console.log(`✅ Stored at: ${finalPath}`);
        
        // 7. Determinar content type
        const contentType = getContentTypeFromMime(file.mimetype, file.originalname);
        
        // 8. Extraer metadata de video (si aplica)
        let videoMetadata: VideoMetadata | null = null;
        if (contentType === 'video') {
            console.log('🎬 Extracting video metadata...');
            try {
                videoMetadata = await ffmpegService.extractVideoMetadata(finalPath);
                console.log('✅ Metadata extracted:', videoMetadata);
            } catch (error) {
                console.warn('⚠️ Failed to extract metadata:', error);
                // No bloqueamos el upload si falla FFmpeg
            }
        }
        
        // 9. Generar thumbnail (si es video)
        let thumbnailPath: string | null = null;
        if (contentType === 'video') {
            console.log('🖼️ Generating thumbnail...');
            try {
                thumbnailPath = await ffmpegService.generateThumbnail(
                    finalPath,
                    fileHash
                );
                console.log('✅ Thumbnail generated:', thumbnailPath);
            } catch (error) {
                console.warn('⚠️ Failed to generate thumbnail:', error);
                // No bloqueamos el upload si falla
            }
        }
        
        // 10. Insertar en base de datos
        const insertResult = await query(`
            INSERT INTO content (
                title, slug, description, type, category_id,
                file_path, file_size, file_hash, mime_type,
                duration_seconds, resolution, bitrate,
                thumbnail_path, is_featured, status,
                created_by, updated_by
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9,
                $10, $11, $12,
                $13, $14, 'active',
                $15, $15
            ) RETURNING *
        `, [
            title,
            slug,
            description || null,
            contentType,
            category_id,
            finalPath,
            file.size,
            fileHash,
            file.mimetype,
            videoMetadata?.duration_seconds || null,
            videoMetadata?.resolution || null,
            videoMetadata?.bitrate || null,
            thumbnailPath,
            is_featured === 'true',
            userId
        ]);
        
        const content = insertResult.rows[0];
        
        // 11. Invalidar cache de contenido
        await cacheDelete('content:*');
        
        // 12. Responder
        res.status(201).json({
            success: true,
            data: content,
            message: 'Content uploaded successfully'
        });
        
    } catch (error) {
        console.error('Upload error:', error);
        
        // Cleanup en caso de error
        if (tempPath) await storageService.cleanupFile(tempPath);
        if (finalPath) await storageService.cleanupFile(finalPath);
        
        res.status(500).json({ error: 'Upload failed' });
    }
};
```

**Características:**
- ✅ Cleanup automático en errores
- ✅ Detección de duplicados por hash
- ✅ Slug único auto-generado
- ✅ FFmpeg no bloqueante (continúa si falla)
- ✅ Thumbnail automático
- ✅ Metadata completa extraída
- ✅ Invalidación de cache

---

## 5. SERVICES LAYER

### storageService.ts

#### calculateFileHash()

```typescript
import crypto from 'crypto';
import fs from 'fs/promises';
import { createReadStream } from 'fs';

export const calculateFileHash = (filePath: string): Promise<string> => {
    return new Promise((resolve, reject) => {
        // SHA-256 hash
        const hash = crypto.createHash('sha256');
        
        // Stream del archivo (no carga todo en RAM)
        const stream = createReadStream(filePath);
        
        // Ir hasheando por chunks
        stream.on('data', (chunk) => {
            hash.update(chunk);
        });
        
        stream.on('end', () => {
            const fileHash = hash.digest('hex');  // 64 caracteres hex
            resolve(fileHash);
        });
        
        stream.on('error', (error) => {
            reject(error);
        });
    });
};
```

**¿Por qué streaming?**

**Método malo (carga todo en RAM):**
```typescript
const buffer = await fs.readFile(filePath);  // 500 MB en RAM
const hash = crypto.createHash('sha256').update(buffer).digest('hex');
```

**Método bueno (streaming):**
```typescript
// Lee por chunks de 64KB
// Uso de RAM: constante (~64 KB)
// Múltiples uploads simultáneos: no satura RAM
```

#### moveToStorage()

```typescript
import path from 'path';

export const moveToStorage = async (
    tempPath: string,
    hash: string,
    mimeType: string,
    originalFilename: string
): Promise<string> => {
    // 1. Determinar carpeta por tipo
    const folder = getStorageFolderFromMime(mimeType, originalFilename);
    // videos/, documents/, images/, audio/
    
    // 2. Determinar extensión
    const ext = path.extname(originalFilename);
    
    // 3. Nombre final: hash + extensión
    const filename = `${hash}${ext}`;
    // Ejemplo: "abc123def456...789.mp4"
    
    // 4. Path completo
    const storagePath = process.env.STORAGE_PATH!;
    const folderPath = path.join(storagePath, folder);
    const finalPath = path.join(folderPath, filename);
    
    // 5. Crear carpeta si no existe
    await fs.mkdir(folderPath, { recursive: true });
    
    // 6. Mover archivo (rename es atómico)
    await fs.rename(tempPath, finalPath);
    
    // 7. Retornar path relativo (para guardar en DB)
    const relativePath = path.join(folder, filename);
    // "videos/abc123...789.mp4"
    
    return relativePath;
};
```

**¿Por qué hash como nombre?**
- ✅ Nombres únicos garantizados
- ✅ Detectar duplicados fácil (mismo hash = mismo archivo)
- ✅ No conflictos con nombres originales repetidos
- ✅ Evita path traversal attacks

#### checkDuplicateHash()

```typescript
export const checkDuplicateHash = async (hash: string): Promise<Content | null> => {
    const result = await query(
        'SELECT * FROM content WHERE file_hash = $1 AND deleted_at IS NULL',
        [hash]
    );
    
    if (result.rows.length > 0) {
        return result.rows[0];
    }
    
    return null;
};
```

**Ventaja:**
- Si dos admins suben el mismo video, solo se guarda una copia
- Ahorro de espacio en disco

### ffmpegService.ts

#### extractVideoMetadata()

```typescript
import ffmpeg from 'fluent-ffmpeg';

export const extractVideoMetadata = (filePath: string): Promise<VideoMetadata> => {
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) return reject(err);
            
            // Extraer stream de video (el primero con codec_type = 'video')
            const videoStream = metadata.streams.find(
                s => s.codec_type === 'video'
            );
            
            if (!videoStream) {
                return reject(new Error('No video stream found'));
            }
            
            // Extraer metadata importante
            const duration = Math.floor(metadata.format.duration || 0);
            const width = videoStream.width || 0;
            const height = videoStream.height || 0;
            const bitrate = parseInt(metadata.format.bit_rate || '0');
            const codec = videoStream.codec_name || 'unknown';
            
            // Calcular FPS
            let fps = 0;
            if (videoStream.r_frame_rate) {
                const [num, den] = videoStream.r_frame_rate.split('/').map(Number);
                fps = Math.round(num / den);
            }
            
            resolve({
                duration_seconds: duration,
                width,
                height,
                resolution: `${width}x${height}`,
                bitrate,
                codec,
                fps
            });
        });
    });
};
```

**Ejemplo de metadata:**
```json
{
    "duration_seconds": 125,
    "width": 1920,
    "height": 1080,
    "resolution": "1920x1080",
    "bitrate": 5000000,
    "codec": "h264",
    "fps": 30
}
```

#### generateThumbnail()

```typescript
export const generateThumbnail = (
    videoPath: string,
    hash: string
): Promise<string> => {
    return new Promise((resolve, reject) => {
        const storagePath = process.env.STORAGE_PATH!;
        const thumbnailDir = path.join(storagePath, 'thumbnails');
        
        // Crear carpeta si no existe
        fs.mkdir(thumbnailDir, { recursive: true })
            .then(() => {
                const thumbnailFilename = `${hash}.jpg`;
                const thumbnailPath = path.join(thumbnailDir, thumbnailFilename);
                
                // FFmpeg command
                ffmpeg(videoPath)
                    .screenshots({
                        timestamps: [1],  // Segundo 1
                        filename: thumbnailFilename,
                        folder: thumbnailDir,
                        size: '1280x720'  // 720p
                    })
                    .on('end', () => {
                        // Path relativo para DB
                        const relativePath = path.join('thumbnails', thumbnailFilename);
                        resolve(relativePath);
                    })
                    .on('error', (err) => {
                        reject(err);
                    });
            })
            .catch(reject);
    });
};
```

**Comando FFmpeg equivalente:**
```bash
ffmpeg -i video.mp4 -ss 00:00:01 -vframes 1 -s 1280x720 thumbnail.jpg
```

---

## 6. BASE DE DATOS

### Query Parameterizada

**❌ VULNERABLE (SQL Injection):**
```typescript
const username = req.body.username;
const sql = `SELECT * FROM users WHERE username = '${username}'`;
const result = await query(sql);

// Attacker envía: username = "admin' OR '1'='1"
// SQL: SELECT * FROM users WHERE username = 'admin' OR '1'='1'
// ¡Retorna TODOS los usuarios!
```

**✅ SEGURO (Parameterized Query):**
```typescript
const username = req.body.username;
const sql = 'SELECT * FROM users WHERE username = $1';
const result = await query(sql, [username]);

// pg library escapa automáticamente
// username = "admin' OR '1'='1" se trata como STRING:
// SQL: SELECT * FROM users WHERE username = 'admin'' OR ''1''=''1'
// No coincide con ningún username real ✅
```

### Transacciones

**¿Cuándo usar transacciones?**
- Múltiples queries que deben ser atómicas (todas o ninguna)
- Ejemplo: transferencia de dinero entre cuentas

**Sin transacción (MALO):**
```typescript
// 1. Restar dinero de cuenta A
await query('UPDATE accounts SET balance = balance - 100 WHERE id = $1', [accountA]);

// 💥 ERROR aquí (servidor se cae)

// 2. Sumar dinero a cuenta B (NUNCA SE EJECUTA)
await query('UPDATE accounts SET balance = balance + 100 WHERE id = $1', [accountB]);

// Resultado: Dinero desaparece ❌
```

**Con transacción (BUENO):**
```typescript
const client = await getClient();

try {
    await client.transaction(async (query) => {
        // 1. Restar dinero de cuenta A
        await query('UPDATE accounts SET balance = balance - 100 WHERE id = $1', [accountA]);
        
        // 💥 ERROR aquí
        
        // 2. Sumar dinero a cuenta B
        await query('UPDATE accounts SET balance = balance + 100 WHERE id = $1', [accountB]);
    });
    // Si todo OK: COMMIT (guardar cambios)
} catch (error) {
    // Si hay error: ROLLBACK (deshacer todo)
    console.error('Transaction failed:', error);
}
// Resultado: Ambos updates o ninguno ✅
```

### Full-Text Search

**Problema con LIKE:**
```sql
SELECT * FROM content 
WHERE title LIKE '%matemática%' OR description LIKE '%matemática%';
-- ❌ Lento (no usa índices)
-- ❌ No busca palabras relacionadas (matemáticas, matemático)
-- ❌ No rankea por relevancia
```

**Solución con to_tsvector:**
```sql
-- Crear índice GIN
CREATE INDEX idx_content_search ON content 
USING GIN (
    to_tsvector('spanish', title || ' ' || COALESCE(description, ''))
);

-- Query
SELECT * FROM content
WHERE to_tsvector('spanish', title || ' ' || description) 
      @@ plainto_tsquery('spanish', 'matemática');
-- ✅ Rápido (usa índice GIN)
-- ✅ Busca "matemática", "matemáticas", "matemático"
-- ✅ Ignora acentos y stopwords ('el', 'la', 'de')
```

**¿Qué hace `to_tsvector`?**
```
"La matemática es importante" 
→ to_tsvector('spanish', ...) 
→ 'matemat':2 'import':4

// Convierte a raíces (stems):
// matemática → matemat
// matemáticas → matemat
// Ignora stopwords: la, es
```

---

## 7. MANEJO DE ERRORES

### Error Handling Pattern

#### AppError Class

```typescript
// types/express.ts
export class AppError extends Error {
    statusCode: number;
    isOperational: boolean;
    
    constructor(message: string, statusCode: number = 500) {
        super(message);
        this.statusCode = statusCode;
        this.isOperational = true;  // Error esperado (no bug)
        
        Error.captureStackTrace(this, this.constructor);
    }
}
```

#### asyncHandler Wrapper

```typescript
// Envuelve controllers async para capturar errores
export const asyncHandler = (fn: Function) => {
    return (req: Request, res: Response, next: NextFunction) => {
        Promise.resolve(fn(req, res, next)).catch(next);
    };
};

// Uso:
export const getContent = asyncHandler(async (req, res) => {
    // Si hay error, automáticamente va al error handler global
    const result = await query('SELECT ...');
    res.json(result);
});
```

#### Global Error Handler

```typescript
// index.ts
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    console.error('❌ Error:', err);
    
    // Error operacional (esperado)
    if (err instanceof AppError) {
        return res.status(err.statusCode).json({
            error: err.message,
            ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
        });
    }
    
    // Error de JWT
    if (err.name === 'JsonWebTokenError') {
        return res.status(401).json({ error: 'Invalid token' });
    }
    
    if (err.name === 'TokenExpiredError') {
        return res.status(401).json({ error: 'Token expired' });
    }
    
    // Error de Multer
    if (err instanceof multer.MulterError) {
        if (err.code === 'LIMIT_FILE_SIZE') {
            return res.status(413).json({ error: 'File too large' });
        }
        return res.status(400).json({ error: err.message });
    }
    
    // Error inesperado (bug)
    console.error('🐛 Unhandled error:', err);
    res.status(500).json({ 
        error: 'Internal server error',
        ...(process.env.NODE_ENV === 'development' && { 
            message: err.message,
            stack: err.stack 
        })
    });
});
```

**Uso en controllers:**
```typescript
// Lanzar error operacional
if (!title) {
    throw new AppError('Title is required', 400);
}

// El global error handler lo captura automáticamente
```

---

## 8. UTILIDADES COMUNES

### Generar Slug

```typescript
export const generateSlug = (text: string): string => {
    return text
        .normalize('NFD')  // Descomponer caracteres acentuados
        .replace(/[\u0300-\u036f]/g, '')  // Remover diacríticos
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')  // Reemplazar no-alfanuméricos con guiones
        .replace(/^-+|-+$/g, '');  // Remover guiones al inicio/fin
};

// Ejemplo:
generateSlug('Matemática Básica 101')
// → "matematica-basica-101"
```

### Hash SHA-256 de String

```typescript
import crypto from 'crypto';

export const hashString = (str: string): string => {
    return crypto
        .createHash('sha256')
        .update(str)
        .digest('hex');  // 64 caracteres hexadecimales
};

// Uso:
const tokenHash = hashString(jwtToken);
```

### Formatear Bytes

```typescript
export const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

// Ejemplos:
formatBytes(1024) // "1 KB"
formatBytes(1048576) // "1 MB"
formatBytes(50000000) // "47.68 MB"
```

### Formatear Duración

```typescript
export const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

// Ejemplos:
formatDuration(125) // "2:05"
formatDuration(3725) // "1:02:05"
```

---

## RESUMEN DE FUNCIONES PRINCIPALES

| Función | Archivo | Propósito |
|---------|---------|-----------|
| `authenticate()` | middleware/auth.ts | Verifica JWT y sesión activa |
| `authorize()` | middleware/auth.ts | Verifica rol del usuario |
| `uploadMiddleware` | middleware/upload.ts | Maneja upload con Multer |
| `login()` | authController.ts | Login con bcrypt + JWT |
| `logout()` | authController.ts | Invalida sesión |
| `getContent()` | contentController.ts | Lista contenido con filtros |
| `getContentById()` | contentController.ts | Detalle de un contenido |
| `streamContent()` | streamController.ts | Streaming HTTP Range |
| `uploadContent()` | uploadController.ts | Procesa upload completo |
| `deleteContent()` | uploadController.ts | Soft delete + cleanup físico |
| `calculateFileHash()` | storageService.ts | Hash SHA-256 streaming |
| `moveToStorage()` | storageService.ts | Mueve archivo a permanente |
| `checkDuplicateHash()` | storageService.ts | Detecta duplicados |
| `extractVideoMetadata()` | ffmpegService.ts | FFmpeg metadata |
| `generateThumbnail()` | ffmpegService.ts | Crea thumbnail con FFmpeg |
| `cacheGet/Set/Delete()` | config/redis.ts | Operaciones de cache |
| `query()` | config/database.ts | Ejecuta SQL con pool |
| `getClient()` | config/database.ts | Cliente para transacciones |

---

**Autor**: GitHub Copilot (Claude Sonnet 4.6)  
**Fecha**: 3 de marzo de 2026  
**Versión**: 1.1.0

---

## 9. MOTOR IA — `ai_engine`

### Estructura

```
ai_engine/
├── mock_main.py         ← FastAPI app principal con SSE streaming
├── services/
│   ├── llm_engine.py    ← Carga y genera con Phi-3.5-mini-instruct
│   ├── hybrid_retriever.py  ← BM25 + ChromaDB (búsqueda semántica)
│   └── stt.py           ← Speech-to-text (Whisper)
└── config/
    └── settings.py      ← Configuración por plataforma (laptop / orin_nx)
```

### `mock_main.py` — Endpoints principales

```python
# Endpoint de búsqueda con streaming SSE
@app.get("/search")
async def search(q: str, level: str = "L1"):
    async def event_stream():
        # 1. Recuperar documentos relevantes (BM25 + ChromaDB)
        docs = await retriever.search(q, top_k=5)
        # 2. Construir prompt en formato Phi chat
        prompt = _build_llm_prompt(q, docs, level)
        # 3. Streamear tokens via SSE
        async for token in llm.stream(prompt):
            yield f"data: {token}\n\n"
    return EventSourceResponse(event_stream())
```

### `_build_llm_prompt()` — Formato Phi-3.5

```python
def _build_llm_prompt(query: str, docs: list, level: str) -> str:
    context = "\n".join(d["text"] for d in docs[:3])
    return (
        f"<|system|>Eres un asistente educativo...<|end|>\n"
        f"<|user|>Contexto:\n{context}\n\nPregunta: {query}<|end|>\n"
        f"<|assistant|>"
    )
# El modelo genera hasta MAX_GENERATION_TOKENS (ajustable en .env)
```

### `settings.py` — Configuración multi-plataforma

```python
# Lee AI_PLATFORM (no PLATFORM) desde .env
PLATFORM = os.getenv("AI_PLATFORM", "orin_nx_16gb")

_PLATFORM_CONFIGS = {
    "laptop":       {"MAX_GEN": 512,  "BATCH": 1, "THREADS": 4},
    "orin_nx_16gb": {"MAX_GEN": 1024, "BATCH": 2, "THREADS": 8},
}
# ⚠️ En .env usar AI_PLATFORM=laptop, no PLATFORM=laptop
```

### Variables de entorno clave (`.env`)

| Variable | Valor actual | Efecto |
|---|---|---|
| `AI_PLATFORM` | `laptop` | Perfil de configuración |
| `MAX_GENERATION_TOKENS` | `1024` | Tokens máximos por respuesta |
| `TARGET_MODEL_DIR` | `/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct` | Ruta del modelo |
| `MAX_CONTEXT_TOKENS` | `2048` | Contexto máximo de entrada |

---

## 10. SEARCH UI — `AIOverview.tsx`

`search_ui/src/components/search/AIOverview.tsx`

### Responsabilidades

- Recibir tokens SSE del motor IA y renderizarlos en streaming
- Renderizar Markdown con: tablas GFM, ecuaciones KaTeX, bloques de código
- Mostrar/ocultar respuesta con degradado (expandir/colapsar)
- Indicador visual de streaming + cursor animado

### Flujo de datos

```
FastAPI (SSE) → EventSource JS → prop text (streaming) → ReactMarkdown → render
```

### `CodeRenderer` — Syntax highlighting

```tsx
function CodeRenderer({ inline, className, children }) {
  const lang = /language-(\w+)/.exec(className ?? '')?.[1] ?? 'text'

  if (inline) return <code>{children}</code>  // pill azul inline

  return (
    <div className="code-block-wrap">          {/* clase para CSS overrides */}
      <header>                                {/* barra azul noche con lang + copy */}
        <span>{lang}</span>
        <CopyButton />
      </header>
      <SyntaxHighlighter
        language={lang}
        style={nightOwl}                      {/* morado·naranja·verde·blanco */}
        customStyle={{ background: 'rgba(11,16,40,0.93)' }}
        showLineNumbers={false}
      />
    </div>
  )
}
```

### CSS relevante (`index.css`)

```css
/* Inline code — pill azul traslúcido */
.md-content code {
  background: rgba(99, 140, 255, 0.10);
  border: 1px solid rgba(99, 140, 255, 0.18);
  color: #3b5fc0;
}

/* Eliminar bordes/decoraciones de tokens Prism */
.code-block-wrap pre span {
  border: none !important;
  text-decoration: none !important;
  outline: none !important;
}
```

### Librerías utilizadas

| Librería | Versión | Uso |
|---|---|---|
| `react-markdown` | ^9 | Parser Markdown → React |
| `remark-gfm` | ^4 | Tablas, listas de tareas |
| `remark-math` | ^6 | Bloques `$...$` y `$$...$$` |
| `rehype-katex` | ^7 | Renderiza LaTeX → HTML |
| `react-syntax-highlighter` | ^15 | Highlighting con Prism |

