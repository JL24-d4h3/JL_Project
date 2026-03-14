import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { testConnection } from './config/database.js';
import { testRedisConnection } from './config/redis.js';
import { errorHandler } from './types/express.js';

// Routes
import authRoutes from './routes/auth.js';
import categoryRoutes from './routes/categories.js';
import contentRoutes from './routes/content.js';
import uploadRoutes from './routes/upload.js';
import systemRoutes from './routes/system.js';
import { startFileWatcher } from './services/fileWatcherService.js';

// Cargar variables de entorno
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middlewares
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next();
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/categories', categoryRoutes);
app.use('/api/content', contentRoutes);
app.use('/api/upload', uploadRoutes);
app.use('/api/system', systemRoutes);

// Ruta de prueba
app.get('/health', async (req, res) => {
  const dbOk = await testConnection();
  const redisOk = await testRedisConnection();
  
  const status = dbOk && redisOk ? 'healthy' : 'degraded';
  const httpStatus = status === 'healthy' ? 200 : 503;
  
  res.status(httpStatus).json({
    status,
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
    services: {
      database: dbOk ? 'connected' : 'disconnected',
      redis: redisOk ? 'connected' : 'disconnected',
    },
  });
});

app.get('/', (req, res) => {
  res.json({
    message: 'CDN Offline - API Server',
    version: '0.2.0',
    endpoints: {
      health: '/health',
      auth: '/api/auth',
      categories: '/api/categories',
      content: '/api/content',
    },
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.method} ${req.path} not found`,
    status: 404,
  });
});

// Error handler (debe ser el último)
app.use(errorHandler);

// Iniciar servidor
const startServer = async () => {
  try {
    // Test de conexiones
    console.log('🔍 Verificando conexiones...');
    const dbOk = await testConnection();
    const redisOk = await testRedisConnection();
    
    if (!dbOk) {
      console.error('❌ No se pudo conectar a PostgreSQL');
      process.exit(1);
    }
    
    if (!redisOk) {
      console.warn('⚠️  Redis no disponible (continuando sin cache)');
    }
    
    app.listen(PORT, () => {
      console.log('');
      console.log('🚀 Servidor corriendo en http://localhost:' + PORT);
      console.log('📦 Entorno:', process.env.NODE_ENV);
      console.log('🗄️  PostgreSQL: ✅');
      console.log('🔴 Redis:', redisOk ? '✅' : '⚠️  (sin cache)');
      console.log('');
      startFileWatcher();
    });
  } catch (error) {
    console.error('❌ Error al iniciar servidor:', error);
    process.exit(1);
  }
};

startServer();

export default app;
