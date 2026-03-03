import multer from 'multer';
import path from 'path';
import { Request } from 'express';
import { AppError } from '../types/express.js';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';
const MAX_FILE_SIZE = parseInt(process.env.MAX_FILE_SIZE || '524288000', 10); // 500 MB

/**
 * MIME types permitidos - Fácilmente extensible
 */
const ALLOWED_MIME_TYPES = {
  video: ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'],
  document: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  image: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  audio: ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4'],
};

const ALL_ALLOWED_TYPES = Object.values(ALLOWED_MIME_TYPES).flat();

/**
 * Configuración de almacenamiento temporal
 * Los archivos se mueven a storage permanente después de validación
 */
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const tempDir = path.join(STORAGE_BASE, 'temp');
    cb(null, tempDir);
  },
  filename: (req, file, cb) => {
    // Nombre temporal único: timestamp_random_originalname
    const uniqueSuffix = `${Date.now()}_${Math.round(Math.random() * 1e9)}`;
    const ext = path.extname(file.originalname);
    const name = path.basename(file.originalname, ext);
    cb(null, `${name}_${uniqueSuffix}${ext}`);
  },
});

/**
 * Filtro de archivos - Validación temprana
 */
const fileFilter = (_req: Request, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
  // Validar extensión primero (más confiable que MIME)
  const ext = path.extname(file.originalname).toLowerCase();
  const allowedExtensions = [
    '.mp4', '.webm', '.ogg', '.mov', // video
    '.pdf', '.doc', '.docx', // documents
    '.jpg', '.jpeg', '.png', '.gif', '.webp', // images
    '.mp3', '.wav', '.ogg', '.m4a', // audio
  ];

  if (!allowedExtensions.includes(ext)) {
    return cb(new AppError(`File extension not allowed: ${ext}`, 400));
  }

  // Validar MIME type (permitir octet-stream como fallback)
  const isValidMime = ALL_ALLOWED_TYPES.includes(file.mimetype) || 
                      file.mimetype === 'application/octet-stream';
  
  if (!isValidMime) {
    return cb(
      new AppError(
        `File type not allowed: ${file.mimetype}. Allowed types: ${ALL_ALLOWED_TYPES.join(', ')}`,
        400
      )
    );
  }

  cb(null, true);
};

/**
 * Configuración de Multer con límites y validaciones
 */
export const uploadMiddleware = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: MAX_FILE_SIZE, // 500 MB por defecto
    files: 1, // Solo un archivo a la vez (escalable a múltiples si es necesario)
  },
});

/**
 * Determina el tipo de contenido basado en MIME type o extensión
 */
export function getContentTypeFromMime(mimeType: string, filename?: string): 'video' | 'pdf' | 'audio' | 'image' | 'document' {
  // Si es octet-stream, usar extensión
  if (mimeType === 'application/octet-stream' && filename) {
    const ext = path.extname(filename).toLowerCase();
    if (['.mp4', '.webm', '.ogg', '.mov'].includes(ext)) return 'video';
    if (['.mp3', '.wav', '.m4a'].includes(ext)) return 'audio';
    if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(ext)) return 'image';
    if (ext === '.pdf') return 'pdf';
    return 'document';
  }
  
  if (ALLOWED_MIME_TYPES.video.includes(mimeType)) return 'video';
  if (ALLOWED_MIME_TYPES.audio.includes(mimeType)) return 'audio';
  if (ALLOWED_MIME_TYPES.image.includes(mimeType)) return 'image';
  if (mimeType === 'application/pdf') return 'pdf';
  return 'document';
}

/**
 * Determina la carpeta de storage basado en tipo o extensión
 */
export function getStorageFolderFromMime(mimeType: string, filename?: string): 'videos' | 'documents' | 'images' | 'audio' {
  // Si es octet-stream, usar extensión
  if (mimeType === 'application/octet-stream' && filename) {
    const ext = path.extname(filename).toLowerCase();
    if (['.mp4', '.webm', '.ogg', '.mov'].includes(ext)) return 'videos';
    if (['.mp3', '.wav', '.m4a'].includes(ext)) return 'audio';
    if (['.jpg', '.jpeg', '.png', '.gif', '.webp'].includes(ext)) return 'images';
    return 'documents';
  }
  
  if (ALLOWED_MIME_TYPES.video.includes(mimeType)) return 'videos';
  if (ALLOWED_MIME_TYPES.audio.includes(mimeType)) return 'audio';
  if (ALLOWED_MIME_TYPES.image.includes(mimeType)) return 'images';
  return 'documents';
}
