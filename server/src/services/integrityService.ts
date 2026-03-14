import { query } from '../config/database.js';
import fs from 'fs/promises';
import path from 'path';

interface IntegrityReport {
  orphanedRecords: Array<{
    id: string;
    title: string;
    file_path: string;
    status: string;
  }>;
  orphanedFiles: string[];
  stats: {
    totalRecords: number;
    validRecords: number;
    orphanedRecords: number;
    orphanedFiles: number;
  };
}

/**
 * Verifica la integridad entre el filesystem y la base de datos
 */
export async function checkIntegrity(): Promise<IntegrityReport> {
  const storageRoot = path.join(process.cwd(), 'storage');
  const orphanedRecords: IntegrityReport['orphanedRecords'] = [];
  const orphanedFiles: string[] = [];

  // 1. Obtener todos los registros activos de la BD
  const result = await query(`
    SELECT id, title, file_path, status
    FROM content
    WHERE deleted_at IS NULL
    ORDER BY created_at DESC
  `);

  const records = result.rows;
  const validRecords: string[] = [];

  // 2. Verificar que cada registro tiene su archivo en disco
  for (const record of records) {
    const fullPath = path.join(storageRoot, record.file_path);

    try {
      await fs.access(fullPath);
      validRecords.push(record.file_path);
    } catch (error) {
      // Archivo no existe
      orphanedRecords.push({
        id: record.id,
        title: record.title,
        file_path: record.file_path,
        status: record.status,
      });
    }
  }

  // 3. Buscar archivos en disco sin registro en BD
  const folders = ['videos', 'audio', 'images', 'code', 'documents'];

  for (const folder of folders) {
    const folderPath = path.join(storageRoot, folder);

    try {
      const files = await fs.readdir(folderPath);

      for (const file of files) {
        if (file === '.gitkeep') continue;

        const relativePath = `${folder}/${file}`;

        // Si el archivo no está en la lista de archivos válidos
        if (!validRecords.includes(relativePath)) {
          orphanedFiles.push(relativePath);
        }
      }
    } catch (error) {
      console.warn(`No se pudo leer la carpeta ${folder}:`, error);
    }
  }

  return {
    orphanedRecords,
    orphanedFiles,
    stats: {
      totalRecords: records.length,
      validRecords: validRecords.length,
      orphanedRecords: orphanedRecords.length,
      orphanedFiles: orphanedFiles.length,
    },
  };
}

/**
 * Repara inconsistencias eliminando registros huérfanos
 */
export async function repairOrphanedRecords(dryRun: boolean = true): Promise<{
  deleted: string[];
  dryRun: boolean;
}> {
  const { orphanedRecords } = await checkIntegrity();
  const deleted: string[] = [];

  for (const record of orphanedRecords) {
    if (!dryRun) {
      // Marcar como eliminado (soft delete)
      await query(
        `UPDATE content
         SET deleted_at = NOW(),
             updated_at = NOW()
         WHERE id = $1`,
        [record.id]
      );
    }
    deleted.push(`${record.title} (${record.file_path})`);
  }

  return { deleted, dryRun };
}

/**
 * Limpia archivos huérfanos del filesystem
 */
export async function cleanOrphanedFiles(dryRun: boolean = true): Promise<{
  deleted: string[];
  dryRun: boolean;
}> {
  const storageRoot = path.join(process.cwd(), 'storage');
  const { orphanedFiles } = await checkIntegrity();
  const deleted: string[] = [];

  for (const file of orphanedFiles) {
    const fullPath = path.join(storageRoot, file);

    if (!dryRun) {
      try {
        await fs.unlink(fullPath);
      } catch (error) {
        console.error(`Error al eliminar ${file}:`, error);
        continue;
      }
    }
    deleted.push(file);
  }

  return { deleted, dryRun };
}

/**
 * Sincronización completa: limpia registros huérfanos Y archivos huérfanos
 */
export async function syncFilesystem(dryRun: boolean = true): Promise<{
  orphanedRecordsDeleted: string[];
  orphanedFilesDeleted: string[];
  dryRun: boolean;
}> {
  const recordsResult = await repairOrphanedRecords(dryRun);
  const filesResult = await cleanOrphanedFiles(dryRun);

  return {
    orphanedRecordsDeleted: recordsResult.deleted,
    orphanedFilesDeleted: filesResult.deleted,
    dryRun,
  };
}
