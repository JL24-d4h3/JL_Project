import { Router } from 'express';
import { login, getMe, logout, getUsers } from '../controllers/authController.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = Router();

router.post('/login', login);
router.get('/me', authenticate, getMe);
router.post('/logout', authenticate, logout);
router.get('/users', authenticate, authorize('admin', 'superadmin'), getUsers);

export default router;
