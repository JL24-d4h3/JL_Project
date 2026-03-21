import { Router } from 'express';
import { getCourses, getCourseById, getCourseBySlug } from '../controllers/courseController.js';

const router = Router();

router.get('/', getCourses);
router.get('/slug/:slug', getCourseBySlug);
router.get('/:id', getCourseById);

export default router;
