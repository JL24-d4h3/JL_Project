import { Router } from 'express';
import { getCategories, getCategoryById, getCategoriesTree } from '../controllers/categoryController.js';

const router = Router();

router.get('/', getCategories);
router.get('/tree', getCategoriesTree);
router.get('/:id', getCategoryById);

export default router;
