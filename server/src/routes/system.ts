import { Router } from 'express';
import { authenticate, authorize } from '../middleware/auth.js';
import {
  getIntegrityReport,
  syncSystem,
  repairRecords,
  cleanFiles,
  clearCache,
} from '../controllers/systemController.js';

const router = Router();

// Todas las rutas de sistema requieren rol admin
router.use(authenticate, authorize('admin'));

/**
 * GET /api/system/integrity
 * Obtener reporte de integridad filesystem-BD
 */
router.get('/integrity', getIntegrityReport);

/**
 * POST /api/system/sync
 * Sincronizar filesystem y BD (eliminar registros y archivos huérfanos)
 * Body: { "dryRun": false } para aplicar cambios
 */
router.post('/sync', syncSystem);

/**
 * POST /api/system/repair-records
 * Eliminar registros de BD sin archivo en disco
 * Body: { "dryRun": false } para aplicar cambios
 */
router.post('/repair-records', repairRecords);

/**
 * POST /api/system/clean-files
 * Eliminar archivos en disco sin registro en BD
 * Body: { "dryRun": false } para aplicar cambios
 */
router.post('/clean-files', cleanFiles);

/**
 * POST /api/system/clear-cache
 * Limpiar caché de Redis manualmente
 * Body: { "pattern": "content:*" } (opcional)
 */
router.post('/clear-cache', clearCache);

export default router;
