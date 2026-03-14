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
 * Maneja la eliminación de un archivo del filesystem.
 *
 * - pending → rejected  (el docente ve el rechazo en "Mis Envíos")
 * - active  → soft-delete (se retira de la publicación)
 */
async function handleFileDeleted(absolutePath: string): Promise<void> {
  const relativePath = toRelativePath(absolutePath);
  const filename = path.basename(absolutePath);

  // Ignorar .gitkeep y archivos ocultos
  if (filename.startsWith('.')) return;

  try {
    // Obtener el estado actual del registro
    const found = await query(
      `SELECT id, title, status FROM content
       WHERE file_path = $1 AND deleted_at IS NULL`,
      [relativePath]
    );

    if (!found.rowCount || found.rowCount === 0) return;

    const { id, title, status } = found.rows[0];

    if (status === 'pending') {
      // El docente esperaba revisión → rechazar con razón clara
      await query(
        `UPDATE content
         SET status          = 'rejected',
             rejected_reason = 'El archivo fue eliminado del sistema antes de ser revisado.',
             updated_at      = NOW()
         WHERE id = $1`,
        [id]
      );
      console.log(`[watcher] "${title}" (pending) → rejected (archivo eliminado)`);
    } else {
      // active u otro → soft-delete, ya no debe mostrarse
      await query(
        `UPDATE content
         SET deleted_at = NOW(), updated_at = NOW()
         WHERE id = $1`,
        [id]
      );
      console.log(`[watcher] "${title}" (${status}) → soft-deleted (archivo eliminado)`);
    }

    await cacheDelete('content:*');
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
