import { Router } from 'express';
import { authenticate, authorize } from '../middleware/auth.js';
import { uploadMiddleware } from '../middleware/upload.js';
import {
  uploadContent,
  getContentStatus,
  deleteContent,
  getMyUploads,
  getPendingQueue,
  getPendingCount,
  reviewContent,
} from '../controllers/uploadController.js';

const router = Router();

/**
 * POST /api/upload
 * Upload de archivos
 * Solo SUPERADMIN (fácil cambiar a: authorize('superadmin', 'admin', 'teacher'))
 */
router.post(
  '/',
  authenticate,
  authorize('superadmin', 'admin', 'teacher'), // Sender app uses teacher role
  uploadMiddleware.single('file'), // Campo 'file' en el form-data
  uploadContent
);

/**
 * GET /api/upload/:id/status
 * Obtener estado de procesamiento
 * Todos los usuarios autenticados pueden ver el estado
 */
router.get(
  '/:id/status',
  authenticate,
  getContentStatus
);

/**
 * DELETE /api/upload/:id
 * Eliminar contenido
 * Solo SUPERADMIN o el creador original
 */
router.delete(
  '/:id',
  authenticate,
  authorize('superadmin'), // El controller verifica además si es creador
  deleteContent
);

/**
 * GET /api/upload/mine
 * Lista de envíos propios (sender app)
 */
router.get('/mine', authenticate, getMyUploads);

/**
 * GET /api/upload/pending/count
 * Cantidad de envíos pendientes (sidebar badge del admin)
 * Debe ir ANTES de /pending para que Express no lo trate como :id
 */
router.get(
  '/pending/count',
  authenticate,
  authorize('superadmin', 'admin'),
  getPendingCount
);

/**
 * GET /api/upload/pending
 * Cola de revisión completa (admin panel)
 */
router.get(
  '/pending',
  authenticate,
  authorize('superadmin', 'admin'),
  getPendingQueue
);

/**
 * PATCH /api/upload/:id/review
 * Aprobar / curar / rechazar un envío pendiente
 */
router.patch(
  '/:id/review',
  authenticate,
  authorize('superadmin', 'admin'),
  reviewContent
);

export default router;
