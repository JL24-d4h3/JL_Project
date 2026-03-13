import { Request, Response } from 'express';
import { asyncHandler } from '../types/express.js';
import {
  checkIntegrity,
  repairOrphanedRecords,
  cleanOrphanedFiles,
  syncFilesystem,
} from '../services/integrityService.js';
import { cacheDelete } from '../config/redis.js';

/**
 * GET /api/system/integrity
 * Verifica la integridad entre filesystem y BD
 */
export const getIntegrityReport = asyncHandler(
  async (req: Request, res: Response) => {
    const report = await checkIntegrity();

    res.json({
      success: true,
      data: report,
      message:
        report.stats.orphanedRecords === 0 && report.stats.orphanedFiles === 0
          ? 'Sistema íntegro: todos los archivos y registros están sincronizados'
          : 'Se detectaron inconsistencias',
    });
  }
);

/**
 * POST /api/system/sync
 * Sincroniza filesystem y BD, eliminando registros y archivos huérfanos
 */
export const syncSystem = asyncHandler(async (req: Request, res: Response) => {
  const { dryRun = true } = req.body;

  const result = await syncFilesystem(dryRun === true);

  // Si no es dry run, invalidar caché
  if (!dryRun) {
    await cacheDelete('content:*');
  }

  res.json({
    success: true,
    data: result,
    message: dryRun
      ? 'Modo simulación: no se realizaron cambios. Agregue {"dryRun": false} al body para aplicar cambios.'
      : 'Sincronización completada. Caché invalidado.',
  });
});

/**
 * POST /api/system/repair-records
 * Elimina registros de BD sin archivo en disco
 */
export const repairRecords = asyncHandler(
  async (req: Request, res: Response) => {
    const { dryRun = true } = req.body;

    const result = await repairOrphanedRecords(dryRun === true);

    // Si no es dry run, invalidar caché
    if (!dryRun) {
      await cacheDelete('content:*');
    }

    res.json({
      success: true,
      data: result,
      message: dryRun
        ? `Simulación: se eliminarían ${result.deleted.length} registros huérfanos`
        : `Se eliminaron ${result.deleted.length} registros huérfanos. Caché invalidado.`,
    });
  }
);

/**
 * POST /api/system/clean-files
 * Elimina archivos en disco sin registro en BD
 */
export const cleanFiles = asyncHandler(async (req: Request, res: Response) => {
  const { dryRun = true } = req.body;

  const result = await cleanOrphanedFiles(dryRun === true);

  res.json({
    success: true,
    data: result,
    message: dryRun
      ? `Simulación: se eliminarían ${result.deleted.length} archivos huérfanos`
      : `Se eliminaron ${result.deleted.length} archivos huérfanos`,
  });
});

/**
 * POST /api/system/clear-cache
 * Limpiar caché de Redis manualmente
 */
export const clearCache = asyncHandler(async (req: Request, res: Response) => {
  const { pattern = 'content:*' } = req.body;

  const deletedKeys = await cacheDelete(pattern);

  res.json({
    success: true,
    data: { deletedKeys, pattern },
    message: `Se eliminaron ${deletedKeys} entradas del caché`,
  });
});
