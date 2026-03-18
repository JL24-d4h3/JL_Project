import { Request, Response } from 'express';
import path from 'path';
import fs from 'fs/promises';
import { query } from '../config/database.js';
import { asyncHandler, AppError } from '../types/express.js';
import { storageService } from '../services/storageService.js';
import { ffmpegService } from '../services/ffmpegService.js';
import { getContentTypeFromMime, getStorageFolderFromMime } from '../middleware/upload.js';
import { cacheDelete } from '../config/redis.js';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';

/**
 * POST /api/upload
 * Upload de archivos — el archivo queda en temp/ hasta que el admin lo revise.
 * En aprobación → se mueve a la carpeta definitiva.
 * En rechazo → se elimina de temp/.
 */
export const uploadContent = asyncHandler(async (req: Request, res: Response) => {
  if (!req.file) {
    throw new AppError('No file uploaded', 400);
  }

  const { title, description, category_id, is_featured } = req.body;

  if (!title) throw new AppError('Title is required', 400);
  // category_id ahora es opcional — el sistema de clasificación automática asigna categoría basada en el contenido

  const file = req.file;
  const userId = req.user!.id;
  const contentType = getContentTypeFromMime(file.mimetype, file.originalname);

  // Ruta relativa del archivo temporal (para guardar en DB)
  const relativeTempPath = `temp/${path.basename(file.path)}`;

  console.log(`📤 Processing upload: ${file.originalname} (${contentType})`);

  try {
    // 1. Calcular hash del archivo en temp (para detección de duplicados)
    const fileHash = await storageService.calculateFileHash(file.path);
    const stats = await fs.stat(file.path);
    const fileSize = stats.size;

    console.log(`✓ File hash calculated: ${fileHash} (${fileSize} bytes)`);

    // 2. Verificar duplicados por hash (solo entre archivos activos o pendientes)
    const duplicateCheck = await query(
      `SELECT id, title FROM content
       WHERE file_hash = $1
         AND deleted_at IS NULL
         AND status NOT IN ('rejected', 'failed')`,
      [fileHash]
    );

    if (duplicateCheck.rowCount! > 0) {
      const duplicate = duplicateCheck.rows[0];
      // Eliminar el archivo temporal ya que es duplicado
      await storageService.deleteFile(relativeTempPath);
      throw new AppError(
        `Este archivo ya existe en el sistema como «${duplicate.title}». Si necesitas reemplazarlo, contacta al administrador.`,
        409
      );
    }

    // 2b. Limpiar registros antiguos rejected/failed con el mismo hash
    // para que el INSERT no viole la constraint UNIQUE en file_hash.
    // También liberar el slug agregándole timestamp para permitir reutilización.
    await query(
      `UPDATE content
       SET deleted_at = NOW(),
           slug = slug || '_deleted_' || extract(epoch from NOW())::bigint::text,
           updated_at = NOW()
       WHERE file_hash = $1
         AND deleted_at IS NULL
         AND status IN ('rejected', 'failed')`,
      [fileHash]
    );

    // 3. Extraer metadata según tipo (en el archivo temporal)
    let metadata: any = {};
    let thumbnailPath: string | null = null;
    let duration: number | null = null;
    let resolution: string | null = null;
    let bitrate: number | null = null;

    if (contentType === 'video') {
      console.log('🎬 Extracting video metadata...');
      try {
        const videoMetadata = await ffmpegService.extractVideoMetadata(file.path);

        metadata = {
          codec: videoMetadata.codec,
          fps: videoMetadata.fps,
          hasAudio: videoMetadata.hasAudio,
        };

        duration = videoMetadata.duration;
        resolution = videoMetadata.resolution;
        bitrate = videoMetadata.bitrate;

        console.log(`✓ Video metadata: ${resolution}, ${duration}s, ${videoMetadata.codec}`);

        // 4. Generar thumbnail (los thumbnails van directo a thumbnails/, no a temp)
        console.log('🖼️  Generating thumbnail...');
        const thumbnailName = `${fileHash}.jpg`;
        thumbnailPath = await ffmpegService.generateThumbnail(file.path, thumbnailName);
        console.log(`✓ Thumbnail generated: ${thumbnailPath}`);
      } catch (error: any) {
        console.warn(`⚠️  FFmpeg processing failed: ${error.message}`);
      }
    }

    // 5. Generar slug del título
    const slug = title
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');

    // 6. Insertar en DB — file_path apunta a temp/ hasta que se apruebe
    // category_id es opcional: si no se provee, se asignará NULL y la clasificación automática se encargará
    const result = await query(
      `INSERT INTO content (
        title, slug, description, type, category_id,
        file_path, file_size, file_hash, mime_type,
        duration_seconds, resolution, bitrate,
        thumbnail_path, metadata,
        status, is_featured,
        created_by, updated_by
      ) VALUES (
        $1, $2, $3, $4, $5,
        $6, $7, $8, $9,
        $10, $11, $12,
        $13, $14,
        $15, $16,
        $17, $17
      ) RETURNING id, title, slug, type, file_path, file_size, status, created_at`,
      [
        title,
        slug,
        description || null,
        contentType,
        category_id || null,  // ← ahora puede ser NULL
        relativeTempPath,   // ← archivo queda en temp/ hasta aprobación
        fileSize,
        fileHash,
        file.mimetype,
        duration,
        resolution,
        bitrate,
        thumbnailPath,
        JSON.stringify(metadata),
        'pending',
        is_featured === 'true' || is_featured === true,
        userId,
      ]
    );

    const content = result.rows[0];
    console.log(`✅ Content queued for review: ${content.id}`);

    // La indexación en el AI Engine se dispara al aprobar (reviewContent),
    // no aquí, porque el archivo aún está en temp/ y el contenido es pending.

    res.status(201).json({
      success: true,
      message: 'Content uploaded successfully and pending review',
      data: {
        id: content.id,
        title: content.title,
        slug: content.slug,
        type: content.type,
        file_path: content.file_path,
        file_size: content.file_size,
        status: content.status,
        created_at: content.created_at,
        thumbnail_path: thumbnailPath,
        duration_seconds: duration,
        resolution,
      },
    });
  } catch (error) {
    // Cleanup: eliminar archivo temporal si algo falla (excepto duplicados, ya eliminados arriba)
    try {
      const fileExists = await storageService.fileExists(relativeTempPath);
      if (fileExists) await storageService.deleteFile(relativeTempPath);
    } catch {}
    throw error;
  }
});

/**
 * GET /api/content/:id/status
 */
export const getContentStatus = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;

  const result = await query(
    'SELECT id, title, status, created_at, updated_at FROM content WHERE id = $1',
    [id]
  );

  if (result.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = result.rows[0];

  res.json({
    success: true,
    data: {
      id: content.id,
      title: content.title,
      status: content.status,
      created_at: content.created_at,
      updated_at: content.updated_at,
    },
  });
});

/**
 * DELETE /api/content/:id
 */
export const deleteContent = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  const userId = req.user!.id;
  const userRole = req.user!.role;

  const result = await query(
    'SELECT * FROM content WHERE id = $1 AND deleted_at IS NULL',
    [id]
  );

  if (result.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = result.rows[0];

  if (userRole !== 'superadmin' && content.created_by !== userId) {
    throw new AppError('You do not have permission to delete this content', 403);
  }

  // Liberar el slug al eliminar (soft delete) para que pueda reutilizarse
  await query(
    `UPDATE content
     SET deleted_at = NOW(),
         slug = slug || '_deleted_' || extract(epoch from NOW())::bigint::text,
         updated_by = $1
     WHERE id = $2`,
    [userId, id]
  );

  (async () => {
    try {
      if (content.file_path) {
        await storageService.deleteFile(content.file_path);
        console.log(`  ✓ Deleted file: ${content.file_path}`);
      }
      if (content.thumbnail_path) {
        await storageService.deleteFile(content.thumbnail_path);
        console.log(`  ✓ Deleted thumbnail: ${content.thumbnail_path}`);
      }
      if (content.quality_versions) {
        const versions = content.quality_versions as any;
        for (const [, filepath] of Object.entries(versions)) {
          await storageService.deleteFile(filepath as string);
        }
      }
    } catch (error) {
      console.error(`⚠️  Error deleting files for content ${id}:`, error);
    }
  })();

  console.log(`🗑️  Content deleted: ${content.title} (${id})`);

  res.json({ success: true, message: 'Content deleted successfully' });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/mine
// ─────────────────────────────────────────────────────────
export const getMyUploads = asyncHandler(async (req: Request, res: Response) => {
  const userId = req.user!.id;

  const result = await query(
    `SELECT id, title, description, type AS content_type, status, rejected_reason,
            duration_seconds AS duration, file_size AS file_size_bytes,
            thumbnail_path, created_at, updated_at
     FROM content
     WHERE created_by = $1 AND deleted_at IS NULL
     ORDER BY created_at DESC`,
    [userId]
  );

  res.json({ success: true, data: result.rows });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/pending
// ─────────────────────────────────────────────────────────
export const getPendingQueue = asyncHandler(async (_req: Request, res: Response) => {
  const result = await query(
    `SELECT c.id, c.title, c.description, c.type AS content_type, c.status,
            c.duration_seconds AS duration, c.file_size AS file_size_bytes,
            c.thumbnail_path, c.file_path,
            c.created_at, c.updated_at,
            u.username AS submitted_by_username, u.full_name AS submitted_by_name
     FROM content c
     LEFT JOIN users u ON u.id = c.created_by
     WHERE c.status = 'pending' AND c.deleted_at IS NULL
     ORDER BY c.created_at ASC`,
    []
  );

  // Filtrar registros cuyo archivo ya no existe en disco y auto-eliminarlos
  const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';

  const existsChecks = await Promise.all(result.rows.map(async (row) => {
    const fullPath = path.join(STORAGE_BASE, row.file_path);
    try { await fs.access(fullPath); return true; } catch { return false; }
  }));

  const valid = result.rows.filter((_, i) => existsChecks[i]);
  const orphanIds = result.rows.filter((_, i) => !existsChecks[i]).map(r => r.id);

  if (orphanIds.length > 0) {
    // Los ítems de la cola son siempre pending → marcar como fallo del sistema
    await query(
      `UPDATE content
       SET status          = 'failed',
           rejected_reason = 'Ocurrió un error con el archivo. Por favor vuelve a subirlo.',
           updated_at      = NOW()
       WHERE id = ANY($1::uuid[]) AND deleted_at IS NULL`,
      [orphanIds]
    );
    await cacheDelete('content:*');
    console.log(`[queue] ${orphanIds.length} registros huérfanos → failed`);
  }

  res.json({ success: true, data: valid });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/pending/count
// ─────────────────────────────────────────────────────────
export const getPendingCount = asyncHandler(async (_req: Request, res: Response) => {
  const result = await query(
    `SELECT COUNT(*)::int AS count FROM content
     WHERE status = 'pending' AND deleted_at IS NULL`,
    []
  );

  res.json({ success: true, count: result.rows[0].count });
});

// ─────────────────────────────────────────────────────────
// PATCH /api/upload/:id/review
// approve → move file from temp to permanent
// curate  → edit metadata + move file from temp to permanent
// reject  → delete temp file
// ─────────────────────────────────────────────────────────
export const reviewContent = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  const userId = req.user!.id;
  const { action, ...payload } = req.body as {
    action: 'approve' | 'curate' | 'reject';
    reason?: string;
    title?: string;
    description?: string;
    category_id?: string;
    is_featured?: boolean;
  };

  if (!['approve', 'curate', 'reject'].includes(action)) {
    throw new AppError('Invalid action. Must be approve, curate, or reject.', 400);
  }

  if (action === 'reject' && !payload.reason?.trim()) {
    throw new AppError('A rejection reason is required.', 400);
  }

  const existing = await query(
    `SELECT * FROM content WHERE id = $1 AND deleted_at IS NULL`,
    [id]
  );

  if (existing.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = existing.rows[0];

  if (content.status !== 'pending') {
    throw new AppError(`Content is not pending (current status: ${content.status})`, 409);
  }

  // ── REJECT ──────────────────────────────────────────────
  if (action === 'reject') {
    // Eliminar archivo temporal del disco
    try {
      await storageService.deleteFile(content.file_path);
      console.log(`🗑️  Deleted temp file on rejection: ${content.file_path}`);
    } catch (e) {
      console.warn(`⚠️  Could not delete temp file: ${content.file_path}`);
    }

    // Eliminar thumbnail si existe
    if (content.thumbnail_path) {
      try {
        await storageService.deleteFile(content.thumbnail_path);
      } catch {}
    }

    await query(
      `UPDATE content
       SET status = 'rejected', rejected_reason = $1, updated_by = $2, updated_at = NOW()
       WHERE id = $3`,
      [payload.reason, userId, id]
    );

    return res.json({ success: true, message: 'Content rejected.' });
  }

  // ── APPROVE / CURATE ─────────────────────────────────────
  // Mover archivo de temp/ a la carpeta permanente correspondiente
  const tempAbsPath = path.join(STORAGE_BASE, content.file_path);
  const storageFolder = getStorageFolderFromMime(content.mime_type, content.file_path);
  const ext = path.extname(content.file_path);

  let permanentPath = content.file_path; // fallback si falla el move

  try {
    const moved = await storageService.moveToStorage(tempAbsPath, storageFolder, ext);
    permanentPath = moved.filePath;
    console.log(`✅ File moved to permanent storage: ${permanentPath}`);
  } catch (moveError: any) {
    console.error(`⚠️  Failed to move file to permanent storage: ${moveError.message}`);
    throw new AppError('Failed to move file to permanent storage. Please try again.', 500);
  }

  const newTitle       = payload.title       ?? content.title;
  const newDescription = payload.description ?? content.description;
  const newCategoryId  = payload.category_id ?? content.category_id;
  const newIsFeatured  = payload.is_featured  ?? content.is_featured;

  await query(
    `UPDATE content
     SET status = 'active', rejected_reason = NULL,
         file_path = $1,
         title = $2, description = $3, category_id = $4, is_featured = $5,
         updated_by = $6, updated_at = NOW()
     WHERE id = $7`,
    [permanentPath, newTitle, newDescription, newCategoryId, newIsFeatured, userId, id]
  );

  // Invalidar caché de listas de contenido para que aparezca inmediatamente
  await cacheDelete('content:*');

  // Disparar indexación en el AI Engine ahora que el contenido está activo
  const aiEngineUrl = process.env.AI_ENGINE_URL || 'http://localhost:8000';
  (async () => {
    try {
      const ingestRes = await fetch(`${aiEngineUrl}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_id: id }),
        signal: AbortSignal.timeout(5000),
      });
      if (ingestRes.ok) {
        console.log(`🤖 AI ingest encolado para content_id=${id}`);
      } else {
        console.warn(`⚠️  AI Engine respondió ${ingestRes.status} al indexar ${id}`);
      }
    } catch (err: any) {
      console.warn(`⚠️  No se pudo contactar al AI Engine para indexar: ${err?.message ?? err}`);
    }
  })();

  return res.json({ success: true, message: `Content ${action === 'curate' ? 'curated and ' : ''}approved.` });
});
