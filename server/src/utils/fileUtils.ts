import fs from 'fs/promises';
import path from 'path';

/**
 * Verifica si un archivo existe en el disco
 */
export async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Verifica si un archivo existe de forma síncrona
 */
export function fileExistsSync(filePath: string): boolean {
  try {
    require('fs').accessSync(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Obtiene la ruta completa al archivo de storage
 */
export function getStoragePath(relativePath: string): string {
  return path.resolve(process.env.STORAGE_PATH || './storage', relativePath);
}
