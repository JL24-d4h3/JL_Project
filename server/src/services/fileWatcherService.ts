import chokidar from 'chokidar';
import path from 'path';
import { query } from '../config/database.js';
import { cacheDelete } from '../config/redis.js';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';

// Carpetas que contienen archivos de contenido (no temp ni archived)
const WATCHED_FOLDERS = [
  path.join(STORAGE_BASE, 'videos'),
  path.join(STORAGE_BASE, 'audio'),
  path.join(STORAGE_BASE, 'images'),
  path.join(STORAGE_BASE, 'code'),
  path.join(STORAGE_BASE, 'documents'),
  path.join(STORAGE_BASE, 'temp'),
];

/**
 * Convierte una ruta absoluta a ruta relativa de storage
 * Ej: /storage/images/abc.jpg → images/abc.jpg
 */
function toRelativePath(absolutePath: string): string {
  return path.relative(STORAGE_BASE, absolutePath);
}

/**
 * Elimina (soft-delete) el registro en BD correspondiente al archivo borrado.
 * También invalida el caché.
 */
async function handleFileDeleted(absolutePath: string): Promise<void> {
  const relativePath = toRelativePath(absolutePath);
  const filename = path.basename(absolutePath);

  // Ignorar .gitkeep y archivos ocultos
  if (filename.startsWith('.')) return;

  try {
    const result = await query(
      `UPDATE content
       SET deleted_at = NOW(), updated_at = NOW()
       WHERE file_path = $1
         AND deleted_at IS NULL
       RETURNING id, title, status`,
      [relativePath]
    );

    if (result.rowCount && result.rowCount > 0) {
      const { id, title, status } = result.rows[0];
      console.log(`[watcher] Archivo eliminado: "${title}" (${relativePath}) [${status}] → marcado como deleted`);

      // Invalidar caché de contenido
      await cacheDelete('content:*');
      console.log(`[watcher] Caché invalidado para ${id}`);
    }
  } catch (err) {
    console.error(`[watcher] Error al procesar eliminación de ${relativePath}:`, err);
  }
}

/**
 * Inicia el watcher del filesystem.
 * Llama a esto una sola vez al arrancar el servidor.
 */
export function startFileWatcher(): void {
  const watcher = chokidar.watch(WATCHED_FOLDERS, {
    persistent: true,
    ignoreInitial: true,      // No procesar archivos existentes al iniciar
    awaitWriteFinish: false,
    ignored: /(^|[/\\])\../,  // Ignorar archivos ocultos (.gitkeep, etc.)
    depth: 1,                 // Solo un nivel de profundidad
  });

  watcher.on('unlink', (filePath) => {
    handleFileDeleted(filePath);
  });

  watcher.on('error', (err) => {
    console.error('[watcher] Error en file watcher:', err);
  });

  watcher.on('ready', () => {
    console.log('👁️  File watcher activo en storage/');
  });
}
