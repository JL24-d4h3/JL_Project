import { Request, Response } from 'express';
import path from 'path';
import { query } from '../config/database.js';
import { asyncHandler, AppError } from '../types/express.js';
import { storageService } from '../services/storageService.js';
import { ffmpegService } from '../services/ffmpegService.js';
import { getContentTypeFromMime, getStorageFolderFromMime } from '../middleware/upload.js';

/**
 * POST /api/content
 * Upload de archivos (video, PDF, audio, imágenes)
 * Solo SUPERADMIN (fácilmente extensible a otros roles)
 * 
 * Arquitectura:
 * 1. Multer recibe archivo → temp/
 * 2. Validar y procesar
 * 3. Calcular hash y mover a storage permanente
 * 4. Extraer metadata (FFmpeg para videos)
 * 5. Generar thumbnail (videos)
 * 6. Insertar en DB con status 'processing' → 'active'
 */
export const uploadContent = asyncHandler(async (req: Request, res: Response) => {
  // Validar que hay archivo
  if (!req.file) {
    throw new AppError('No file uploaded', 400);
  }

  // Validar campos requeridos
  const { title, description, category_id, is_featured } = req.body;

  if (!title) {
    throw new AppError('Title is required', 400);
  }

  if (!category_id) {
    throw new AppError('Category ID is required', 400);
  }

  const file = req.file;
  const userId = req.user!.id; // Garantizado por authenticate middleware
  const contentType = getContentTypeFromMime(file.mimetype, file.originalname);
  const storageFolder = getStorageFolderFromMime(file.mimetype, file.originalname);
  const extension = path.extname(file.originalname);

  console.log(`📤 Processing upload: ${file.originalname} (${contentType})`);

  try {
    // 1. Mover archivo a storage permanente y calcular hash
    const { filePath, fileHash, fileSize } = await storageService.moveToStorage(
      file.path,
      storageFolder,
      extension
    );

    console.log(`✓ File moved to storage: ${filePath} (hash: ${fileHash})`);

    // 2. Verificar duplicados por hash
    const duplicateCheck = await query(
      'SELECT id, title FROM content WHERE file_hash = $1 AND deleted_at IS NULL',
      [fileHash]
    );

    if (duplicateCheck.rowCount! > 0) {
      const duplicate = duplicateCheck.rows[0];
      throw new AppError(
        `Duplicate file detected. Already exists as: "${duplicate.title}" (ID: ${duplicate.id})`,
        409
      );
    }

    // 3. Extraer metadata según tipo
    let metadata: any = {};
    let thumbnailPath: string | null = null;
    let duration: number | null = null;
    let resolution: string | null = null;
    let bitrate: number | null = null;

    if (contentType === 'video') {
      console.log('🎬 Extracting video metadata...');
      
      try {
        const videoMetadata = await ffmpegService.extractVideoMetadata(filePath);
        
        metadata = {
          codec: videoMetadata.codec,
          fps: videoMetadata.fps,
          hasAudio: videoMetadata.hasAudio,
        };
        
        duration = videoMetadata.duration;
        resolution = videoMetadata.resolution;
        bitrate = videoMetadata.bitrate;

        console.log(`✓ Video metadata: ${resolution}, ${duration}s, ${videoMetadata.codec}`);

        // 4. Generar thumbnail
        console.log('🖼️  Generating thumbnail...');
        const thumbnailName = `${fileHash}.jpg`;
        thumbnailPath = await ffmpegService.generateThumbnail(filePath, thumbnailName);
        console.log(`✓ Thumbnail generated: ${thumbnailPath}`);

      } catch (error: any) {
        console.warn(`⚠️  FFmpeg processing failed: ${error.message}`);
        // No falla el upload, solo no tiene metadata/thumbnail
      }
    }

    // 5. Generar slug del título
    const slug = title
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remover acentos
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');

    // 6. Insertar en base de datos
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
        category_id,
        filePath,
        fileSize,
        fileHash,
        file.mimetype,
        duration,
        resolution,
        bitrate,
        thumbnailPath,
        JSON.stringify(metadata),
        'pending', // Awaiting admin review before going active
        is_featured === 'true' || is_featured === true,
        userId,
      ]
    );

    const content = result.rows[0];

    console.log(`✅ Content uploaded successfully: ${content.id}`);

    // Disparar ingesta en el AI Engine de forma asíncrona (fire-and-forget)
    // No esperamos la respuesta para no bloquear la respuesta al cliente
    const aiEngineUrl = process.env.AI_ENGINE_URL || 'http://localhost:8000';
    (async () => {
      try {
        const ingestRes = await fetch(`${aiEngineUrl}/api/ingest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content_id: content.id }),
          signal: AbortSignal.timeout(5000),  // timeout de 5 s para el encolado
        });
        if (ingestRes.ok) {
          console.log(`🤖 AI ingest encolado para content_id=${content.id}`);
        } else {
          console.warn(`⚠️  AI Engine respondió ${ingestRes.status} al engestin content_id=${content.id}`);
        }
      } catch (err: any) {
        // El AI Engine puede no estar corriendo en desarrollo — no falla el upload
        console.warn(`⚠️  No se pudo contactar al AI Engine para ingesta: ${err?.message ?? err}`);
      }
    })();

    res.status(201).json({
      success: true,
      message: 'Content uploaded successfully',
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
    // Cleanup: eliminar archivo temporal si algo falla
    try {
      await storageService.deleteFile(file.path);
    } catch {}
    
    throw error;
  }
});

/**
 * GET /api/content/:id/status
 * Obtener estado de procesamiento de un contenido
 * Útil para uploads asíncronos con queue system
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
 * Eliminar contenido (soft delete en DB + hard delete de archivos físicos)
 * Solo SUPERADMIN y el creador original
 */
export const deleteContent = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  const userId = req.user!.id;
  const userRole = req.user!.role;

  // Obtener contenido
  const result = await query(
    'SELECT * FROM content WHERE id = $1 AND deleted_at IS NULL',
    [id]
  );

  if (result.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = result.rows[0];

  // Verificar permisos: superadmin o creador
  if (userRole !== 'superadmin' && content.created_by !== userId) {
    throw new AppError('You do not have permission to delete this content', 403);
  }

  // Soft delete en DB
  await query(
    'UPDATE content SET deleted_at = NOW(), updated_by = $1 WHERE id = $2',
    [userId, id]
  );

  // Hard delete de archivos físicos (asíncrono, no bloquea la respuesta)
  (async () => {
    try {
      // Eliminar archivo principal
      if (content.file_path) {
        await storageService.deleteFile(content.file_path);
        console.log(`  ✓ Deleted file: ${content.file_path}`);
      }
      
      // Eliminar thumbnail si existe
      if (content.thumbnail_path) {
        await storageService.deleteFile(content.thumbnail_path);
        console.log(`  ✓ Deleted thumbnail: ${content.thumbnail_path}`);
      }

      // Eliminar versiones de calidad si existen
      if (content.quality_versions) {
        const versions = content.quality_versions as any;
        for (const [quality, filepath] of Object.entries(versions)) {
          await storageService.deleteFile(filepath as string);
          console.log(`  ✓ Deleted ${quality}: ${filepath}`);
        }
      }
    } catch (error) {
      console.error(`⚠️  Error deleting files for content ${id}:`, error);
      // No falla la operación, solo logea
    }
  })();

  console.log(`🗑️  Content deleted: ${content.title} (${id})`);

  res.json({
    success: true,
    message: 'Content deleted successfully',
  });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/mine
// Returns uploads submitted by the current authenticated user
// ─────────────────────────────────────────────────────────
export const getMyUploads = asyncHandler(async (req: Request, res: Response) => {
  const userId = req.user!.id;

  const result = await query(
    `SELECT id, title, description, content_type, status, rejected_reason,
            duration, file_size_bytes, thumbnail_path, created_at, updated_at
     FROM content
     WHERE created_by = $1 AND deleted_at IS NULL
     ORDER BY created_at DESC`,
    [userId]
  );

  res.json({ success: true, data: result.rows });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/pending
// Returns all content with status 'pending' (admin only)
// ─────────────────────────────────────────────────────────
export const getPendingQueue = asyncHandler(async (req: Request, res: Response) => {
  const result = await query(
    `SELECT c.id, c.title, c.description, c.content_type, c.status,
            c.duration, c.file_size_bytes, c.thumbnail_path, c.file_path,
            c.created_at, c.updated_at,
            u.username AS submitted_by_username, u.full_name AS submitted_by_name
     FROM content c
     LEFT JOIN users u ON u.id = c.created_by
     WHERE c.status = 'pending' AND c.deleted_at IS NULL
     ORDER BY c.created_at ASC`,
    []
  );

  res.json({ success: true, data: result.rows });
});

// ─────────────────────────────────────────────────────────
// GET /api/upload/pending/count
// Returns count of pending submissions (for sidebar badge)
// ─────────────────────────────────────────────────────────
export const getPendingCount = asyncHandler(async (req: Request, res: Response) => {
  const result = await query(
    `SELECT COUNT(*)::int AS count FROM content
     WHERE status = 'pending' AND deleted_at IS NULL`,
    []
  );

  res.json({ success: true, count: result.rows[0].count });
});

// ─────────────────────────────────────────────────────────
// PATCH /api/upload/:id/review
// Approve, curate (edit + approve), or reject a pending item
// Body (discriminated union):
//   { action: 'approve' }
//   { action: 'curate', title?, description?, category_id?, is_featured? }
//   { action: 'reject', reason: string }
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

  // Fetch the content
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

  if (action === 'reject') {
    await query(
      `UPDATE content
       SET status = 'rejected', rejected_reason = $1, updated_by = $2, updated_at = NOW()
       WHERE id = $3`,
      [payload.reason, userId, id]
    );

    return res.json({ success: true, message: 'Content rejected.' });
  }

  // approve or curate
  const newTitle       = payload.title       ?? content.title;
  const newDescription = payload.description ?? content.description;
  const newCategoryId  = payload.category_id ?? content.category_id;
  const newIsFeatured  = payload.is_featured  ?? content.is_featured;

  await query(
    `UPDATE content
     SET status = 'active', rejected_reason = NULL,
         title = $1, description = $2, category_id = $3, is_featured = $4,
         updated_by = $5, updated_at = NOW()
     WHERE id = $6`,
    [newTitle, newDescription, newCategoryId, newIsFeatured, userId, id]
  );

  res.json({ success: true, message: `Content ${action === 'curate' ? 'curated and ' : ''}approved.` });
});
