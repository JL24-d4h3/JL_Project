import { Router } from 'express';
import { authenticate, authorize } from '../middleware/auth.js';
import { uploadMiddleware } from '../middleware/upload.js';
import { uploadContent, getContentStatus, deleteContent } from '../controllers/uploadController.js';

const router = Router();

/**
 * POST /api/upload
 * Upload de archivos
 * Solo SUPERADMIN (fácil cambiar a: authorize('superadmin', 'admin', 'teacher'))
 */
router.post(
  '/',
  authenticate,
  authorize('superadmin'), // 👈 Cambiar aquí para permitir más roles
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

export default router;
