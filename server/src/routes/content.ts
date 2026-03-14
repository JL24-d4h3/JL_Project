import { Router } from 'express';
import { getContent, getContentById, getFeaturedContent } from '../controllers/contentController.js';
import { streamContent, getThumbnail } from '../controllers/streamController.js';
import { authenticate } from '../middleware/auth.js';

const router = Router();

// Rutas públicas (por ahora)
router.get('/', getContent);
router.get('/featured', getFeaturedContent);
router.get('/:id', getContentById);

// Streaming (protegido opcionalmente)
router.get('/:id/stream', streamContent);
router.get('/:id/thumbnail', getThumbnail);

// Rutas protegidas se agregarán después
// router.post('/', authenticate, authorize('teacher', 'admin'), uploadContent);

export default router;
