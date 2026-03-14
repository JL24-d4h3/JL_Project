import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pg;

// Pool de conexiones para PostgreSQL
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20, // Máximo de conexiones
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Evento: conexión exitosa
pool.on('connect', () => {
  console.log('✅ Conectado a PostgreSQL');
});

// Evento: error
pool.on('error', (err) => {
  console.error('❌ Error inesperado en PostgreSQL:', err);
  process.exit(-1);
});

// Helper: ejecutar query con manejo de errores
export const query = async (text: string, params?: any[]) => {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log('Executed query', { text, duration, rows: res.rowCount });
    return res;
  } catch (error) {
    console.error('Query error:', { text, error });
    throw error;
  }
};

// Helper: obtener una conexión del pool
export const getClient = async () => {
  const client = await pool.connect();
  const query = client.query.bind(client);
  const release = client.release.bind(client);
  
  // Timeout de 5 segundos
  const timeout = setTimeout(() => {
    console.error('Client checkout timeout');
  }, 5000);
  
  client.release = () => {
    clearTimeout(timeout);
    release();
  };
  
  return { client, query, release: client.release };
};

// Test de conexión
export const testConnection = async () => {
  try {
    const result = await query('SELECT NOW(), current_database(), current_user');
    console.log('🗄️  Database:', result.rows[0]);
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    return false;
  }
};

export default pool;
