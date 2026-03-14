import { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';
import { query } from '../config/database.js';
import { asyncHandler, AppError } from '../types/express.js';
import { cacheDelete } from '../config/redis.js';

// GET /api/content/:id/stream - Streaming de video con HTTP Range requests
export const streamContent = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;

  // Obtener información del contenido
  const result = await query(
    `SELECT file_path, file_size, mime_type, type, title, etag, cache_control
     FROM content 
     WHERE id = $1 AND deleted_at IS NULL AND status = 'active'`,
    [id]
  );

  if (result.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = result.rows[0];

  // Verificar que es un archivo de video/audio
  if (!['video', 'audio'].includes(content.type)) {
    throw new AppError('Content is not streamable', 400);
  }

  // Construir ruta completa al archivo
  const filePath = path.resolve(process.env.STORAGE_PATH || './storage', content.file_path);

  // Verificar que el archivo existe
  if (!fs.existsSync(filePath)) {
    // Auto-reparar: marcar como eliminado en BD e invalidar caché
    query(
      `UPDATE content SET deleted_at = NOW(), updated_at = NOW() WHERE id = $1 AND deleted_at IS NULL`,
      [id]
    ).then(() => cacheDelete('content:*')).catch(console.error);

    throw new AppError('File not found on disk', 404);
  }

  const fileSize = content.file_size;
  const range = req.headers.range;

  // Registrar acceso (sin await para no bloquear)
  query(
    `INSERT INTO access_log (content_id, user_id, ip_address, user_agent, cache_hit)
     VALUES ($1, $2, $3, $4, false)`,
    [id, req.user?.id || null, req.ip, req.get('user-agent')]
  ).catch(err => console.error('Error logging access:', err));

  // Si hay Range header (streaming parcial)
  if (range) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
    const chunkSize = end - start + 1;

    // Validar rango
    if (start >= fileSize || end >= fileSize) {
      res.status(416).set({
        'Content-Range': `bytes */${fileSize}`,
      });
      return res.end();
    }

    const file = fs.createReadStream(filePath, { start, end });

    res.status(206).set({
      'Content-Range': `bytes ${start}-${end}/${fileSize}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunkSize.toString(),
      'Content-Type': content.mime_type || 'video/mp4',
      'Cache-Control': content.cache_control || 'public, max-age=31536000',
      'ETag': content.etag || '',
    });

    file.pipe(res);

    // Manejar errores de lectura
    file.on('error', (error) => {
      console.error('Stream error:', error);
      if (!res.headersSent) {
        res.status(500).end();
      }
    });
  } else {
    // Streaming completo (sin Range)
    const file = fs.createReadStream(filePath);

    res.status(200).set({
      'Content-Length': fileSize.toString(),
      'Content-Type': content.mime_type || 'video/mp4',
      'Accept-Ranges': 'bytes',
      'Cache-Control': content.cache_control || 'public, max-age=31536000',
      'ETag': content.etag || '',
    });

    file.pipe(res);

    file.on('error', (error) => {
      console.error('Stream error:', error);
      if (!res.headersSent) {
        res.status(500).end();
      }
    });
  }
});

// GET /api/content/:id/thumbnail - Obtener thumbnail
export const getThumbnail = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;

  const result = await query(
    'SELECT thumbnail_path FROM content WHERE id = $1 AND deleted_at IS NULL',
    [id]
  );

  if (result.rowCount === 0 || !result.rows[0].thumbnail_path) {
    throw new AppError('Thumbnail not found', 404);
  }

  const thumbnailPath = path.resolve(
    process.env.STORAGE_PATH || './storage',
    result.rows[0].thumbnail_path
  );

  if (!fs.existsSync(thumbnailPath)) {
    throw new AppError('Thumbnail file not found on disk', 404);
  }

  // Enviar thumbnail con cache largo
  res.sendFile(thumbnailPath, {
    maxAge: '1y',
    immutable: true,
  });
});
