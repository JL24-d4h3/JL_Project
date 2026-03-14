import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { createReadStream } from 'fs';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';

/**
 * Storage Service - Gestión centralizada de archivos
 * Principios SOLID: Single Responsibility
 */
export class StorageService {
  /**
   * Calcula SHA-256 hash de un archivo de forma eficiente (streaming)
   * No carga todo el archivo en memoria
   */
  async calculateFileHash(filePath: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const hash = crypto.createHash('sha256');
      const stream = createReadStream(filePath);

      stream.on('data', (chunk) => hash.update(chunk));
      stream.on('end', () => resolve(hash.digest('hex')));
      stream.on('error', reject);
    });
  }

  /**
   * Mueve archivo temporal a storage permanente con nombre basado en hash
   * Previene colisiones y organiza por tipo
   */
  async moveToStorage(
    tempPath: string,
    type: 'videos' | 'documents' | 'images' | 'audio' | 'code',
    extension: string
  ): Promise<{ filePath: string; fileHash: string; fileSize: number }> {
    // Calcular hash antes de mover
    const fileHash = await this.calculateFileHash(tempPath);
    
    // Obtener tamaño
    const stats = await fs.stat(tempPath);
    const fileSize = stats.size;

    // Crear directorio si no existe
    const targetDir = path.join(STORAGE_BASE, type);
    await fs.mkdir(targetDir, { recursive: true });

    // Nombre del archivo: hash + extensión (evita duplicados)
    const fileName = `${fileHash}${extension}`;
    const targetPath = path.join(targetDir, fileName);

    // Si ya existe, es un duplicado (no mover, solo eliminar temp)
    try {
      await fs.access(targetPath);
      // Ya existe, eliminar temporal
      await fs.unlink(tempPath);
    } catch {
      // No existe, mover archivo
      await fs.rename(tempPath, targetPath);
    }

    // Ruta relativa para DB
    const relativePath = path.join(type, fileName);

    return { filePath: relativePath, fileHash, fileSize };
  }

  /**
   * Verifica si un archivo existe en storage
   */
  async fileExists(relativePath: string): Promise<boolean> {
    try {
      const fullPath = path.join(STORAGE_BASE, relativePath);
      await fs.access(fullPath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Elimina archivo del storage (soft delete en DB, hard delete en disco)
   */
  async deleteFile(relativePath: string): Promise<void> {
    const fullPath = path.join(STORAGE_BASE, relativePath);
    try {
      await fs.unlink(fullPath);
    } catch (error) {
      // Log pero no falla si el archivo ya no existe
      console.warn(`File not found for deletion: ${relativePath}`);
    }
  }

  /**
   * Obtiene información de un archivo
   */
  async getFileInfo(relativePath: string): Promise<{ size: number; mtime: Date } | null> {
    try {
      const fullPath = path.join(STORAGE_BASE, relativePath);
      const stats = await fs.stat(fullPath);
      return {
        size: stats.size,
        mtime: stats.mtime,
      };
    } catch {
      return null;
    }
  }

  /**
   * Limpia archivos temporales antiguos (> 24 horas)
   * Debe ejecutarse en un cron job
   */
  async cleanupTempFiles(): Promise<number> {
    const tempDir = path.join(STORAGE_BASE, 'temp');
    let cleaned = 0;

    try {
      const files = await fs.readdir(tempDir);
      const now = Date.now();
      const oneDayMs = 24 * 60 * 60 * 1000;

      for (const file of files) {
        const filePath = path.join(tempDir, file);
        const stats = await fs.stat(filePath);

        if (now - stats.mtimeMs > oneDayMs) {
          await fs.unlink(filePath);
          cleaned++;
        }
      }
    } catch (error) {
      console.error('Error cleaning temp files:', error);
    }

    return cleaned;
  }
}

export const storageService = new StorageService();
