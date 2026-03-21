import { Router } from 'express';
import { login, signup, getMe, logout, getUsers } from '../controllers/authController.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = Router();

// Autenticación
router.post('/sign-in', login);
router.post('/sign-up', signup);
router.post('/login', login); // Compatibilidad
router.get('/me', authenticate, getMe);
router.post('/logout', authenticate, logout);
router.get('/users', authenticate, authorize('admin', 'superadmin'), getUsers);

export default router;
