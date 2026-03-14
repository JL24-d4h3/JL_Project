import Redis from 'ioredis';
import dotenv from 'dotenv';

dotenv.config();

// Cliente Redis para cache
export const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
});

redis.on('connect', () => {
  console.log('✅ Conectado a Redis');
});

redis.on('error', (err) => {
  console.error('❌ Error en Redis:', err);
});

// Helper: cache con TTL
export const cacheSet = async (key: string, value: any, ttlSeconds = 3600) => {
  try {
    const serialized = JSON.stringify(value);
    await redis.setex(key, ttlSeconds, serialized);
    return true;
  } catch (error) {
    console.error('Cache set error:', error);
    return false;
  }
};

// Helper: obtener del cache
export const cacheGet = async (key: string) => {
  try {
    const cached = await redis.get(key);
    if (!cached) return null;
    return JSON.parse(cached);
  } catch (error) {
    console.error('Cache get error:', error);
    return null;
  }
};

// Helper: invalidar cache
export const cacheDelete = async (pattern: string) => {
  try {
    const keys = await redis.keys(pattern);
    if (keys.length > 0) {
      await redis.del(...keys);
    }
    return keys.length;
  } catch (error) {
    console.error('Cache delete error:', error);
    return 0;
  }
};

// Test de conexión
export const testRedisConnection = async () => {
  try {
    await redis.ping();
    console.log('🔴 Redis OK');
    return true;
  } catch (error) {
    console.error('❌ Redis connection failed:', error);
    return false;
  }
};

export default redis;
