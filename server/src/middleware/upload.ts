import multer from 'multer';
import path from 'path';
import { Request } from 'express';
import { AppError } from '../types/express.js';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';
const MAX_FILE_SIZE = parseInt(process.env.MAX_FILE_SIZE || '524288000', 10); // 500 MB

/**
 * MIME types permitidos agrupados por categoría
 */
const ALLOWED_MIME_TYPES = {
  video: [
    'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime',
    'video/x-msvideo',       // .avi
    'video/x-matroska',      // .mkv
  ],
  audio: [
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4',
    'audio/flac', 'audio/aac', 'audio/x-flac',
    'audio/x-wav', 'audio/x-m4a',
  ],
  image: [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'image/svg+xml', 'image/bmp', 'image/tiff',
  ],
  document: [
    // Office / PDF
    'application/pdf',
    'application/msword',                                                               // .doc
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',          // .docx
    'application/vnd.ms-excel',                                                         // .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',                // .xlsx
    'application/vnd.ms-powerpoint',                                                    // .ppt
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',        // .pptx
    // Texto / código
    'text/plain',           // .txt, .py, .js, .ts, .java, .c, .cpp, .cs, .go, .rb, etc.
    'text/html',            // .html / .htm
    'text/css',             // .css
    'text/javascript',      // .js (algunos navegadores)
    'application/json',     // .json
    'application/xml',      // .xml
    'text/xml',
    'text/markdown',        // .md
    'text/x-python',        // .py (algunos sistemas)
    'text/x-java-source',   // .java
    'text/x-csrc',          // .c
    'text/x-c++src',        // .cpp
    // Comprimidos
    'application/zip',
    'application/x-zip-compressed',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
  ],
};

const ALL_ALLOWED_TYPES = Object.values(ALLOWED_MIME_TYPES).flat();

/**
 * Extensiones permitidas
 */
const ALLOWED_EXTENSIONS = new Set([
  // Video
  '.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv',
  // Audio
  '.mp3', '.wav', '.m4a', '.flac', '.aac', '.opus',
  // Imágenes
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff',
  // Documentos Office
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  // Código fuente / texto
  '.txt', '.md', '.html', '.htm', '.css',
  '.js', '.ts', '.jsx', '.tsx',
  '.py', '.java', '.c', '.cpp', '.cc', '.h', '.hpp',
  '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs',
  '.sh', '.bash', '.zsh',
  '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env',
  '.sql', '.graphql', '.proto',
  '.r', '.m', '.scala', '.lua', '.pl', '.ex', '.exs',
  // Archivos comprimidos
  '.zip', '.rar', '.7z', '.tar', '.gz',
]);

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, path.join(STORAGE_BASE, 'temp'));
  },
  filename: (_req, file, cb) => {
    const uniqueSuffix = `${Date.now()}_${Math.round(Math.random() * 1e9)}`;
    const ext = path.extname(file.originalname);
    const name = path.basename(file.originalname, ext)
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .slice(0, 60);
    cb(null, `${name}_${uniqueSuffix}${ext}`);
  },
});

const fileFilter = (_req: Request, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
  const ext = path.extname(file.originalname).toLowerCase();

  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return cb(new AppError(`Extensión de archivo no permitida: ${ext}`, 400));
  }

  // MIME type flexible: octet-stream es el fallback para archivos de código/texto
  const isValidMime =
    ALL_ALLOWED_TYPES.includes(file.mimetype) ||
    file.mimetype === 'application/octet-stream' ||
    file.mimetype.startsWith('text/');

  if (!isValidMime) {
    return cb(
      new AppError(
        `Tipo de archivo no permitido: ${file.mimetype}`,
        400
      )
    );
  }

  cb(null, true);
};

export const uploadMiddleware = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: MAX_FILE_SIZE,
    files: 1,
  },
});

/**
 * Determina el tipo de contenido basado en MIME type o extensión
 */
export function getContentTypeFromMime(
  mimeType: string,
  filename?: string
): 'video' | 'pdf' | 'audio' | 'image' | 'document' | 'code' {
  const ext = filename ? path.extname(filename).toLowerCase() : '';

  // Extensiones de código fuente
  const codeExtensions = [
    '.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.c', '.cpp', '.cc', '.h', '.hpp',
    '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.sh', '.bash', '.zsh',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env', '.sql', '.graphql',
    '.proto', '.r', '.m', '.scala', '.lua', '.pl', '.ex', '.exs',
  ];

  // La extensión siempre gana para archivos de código, independientemente del MIME type
  // (application/json, text/x-python, application/octet-stream, etc.)
  if (codeExtensions.includes(ext)) return 'code';

  if (ALLOWED_MIME_TYPES.video.includes(mimeType)) return 'video';
  if (ALLOWED_MIME_TYPES.audio.includes(mimeType)) return 'audio';
  if (ALLOWED_MIME_TYPES.image.includes(mimeType)) return 'image';
  if (mimeType === 'application/pdf') return 'pdf';

  // Para MIME types no informativos, revisar extensión
  if (mimeType === 'application/octet-stream' || mimeType.startsWith('text/')) {
    if (['.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv'].includes(ext)) return 'video';
    if (['.mp3', '.wav', '.m4a', '.flac', '.aac', '.opus'].includes(ext)) return 'audio';
    if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff'].includes(ext)) return 'image';
    if (ext === '.pdf') return 'pdf';
  }

  return 'document';
}

/**
 * Determina la carpeta de storage permanente
 */
export function getStorageFolderFromMime(
  mimeType: string,
  filename?: string
): 'videos' | 'documents' | 'images' | 'audio' | 'code' {
  const type = getContentTypeFromMime(mimeType, filename);
  if (type === 'video') return 'videos';
  if (type === 'audio') return 'audio';
  if (type === 'image') return 'images';
  if (type === 'code') return 'code';
  return 'documents';
}
