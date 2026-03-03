import { Request, Response } from 'express';
import { query } from '../config/database.js';
import { asyncHandler, AppError } from '../types/express.js';
import { Category } from '../models/index.js';

// GET /api/categories - Listar todas las categorías
export const getCategories = asyncHandler(async (req: Request, res: Response) => {
  const result = await query(`
    SELECT 
      id, name, slug, description, parent_id, icon, color,
      display_order, is_active, created_at
    FROM categories
    WHERE is_active = true
    ORDER BY display_order ASC, name ASC
  `);

  res.json({
    success: true,
    data: result.rows,
    count: result.rowCount,
  });
});

// GET /api/categories/:id - Detalle de categoría con contenido
export const getCategoryById = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;

  const categoryResult = await query(
    'SELECT * FROM categories WHERE id = $1 AND is_active = true',
    [id]
  );

  if (categoryResult.rowCount === 0) {
    throw new AppError('Category not found', 404);
  }

  // Obtener contenido de esta categoría
  const contentResult = await query(
    `SELECT 
      id, title, description, type, thumbnail_path,
      duration_seconds, file_size, access_count, is_featured
    FROM content
    WHERE category_id = $1 AND deleted_at IS NULL AND status = 'active'
    ORDER BY is_featured DESC, created_at DESC
    LIMIT 50`,
    [id]
  );

  res.json({
    success: true,
    data: {
      category: categoryResult.rows[0],
      content: contentResult.rows,
      content_count: contentResult.rowCount,
    },
  });
});

// GET /api/categories/tree - Categorías en estructura de árbol
export const getCategoriesTree = asyncHandler(async (req: Request, res: Response) => {
  const result = await query(`
    WITH RECURSIVE category_tree AS (
      -- Categorías raíz
      SELECT 
        id, name, slug, description, parent_id, icon, color,
        display_order, 0 as level
      FROM categories
      WHERE parent_id IS NULL AND is_active = true
      
      UNION ALL
      
      -- Subcategorías
      SELECT 
        c.id, c.name, c.slug, c.description, c.parent_id, c.icon, c.color,
        c.display_order, ct.level + 1
      FROM categories c
      INNER JOIN category_tree ct ON c.parent_id = ct.id
      WHERE c.is_active = true
    )
    SELECT * FROM category_tree
    ORDER BY level, display_order, name
  `);

  res.json({
    success: true,
    data: result.rows,
  });
});
