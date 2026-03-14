import { Request, Response } from 'express';
import { query } from '../config/database.js';
import { cacheGet, cacheSet } from '../config/redis.js';
import { asyncHandler, AppError } from '../types/express.js';
import { ContentQueryParams, PaginatedResponse, ContentListDTO } from '../models/index.js';

// GET /api/content - Listar contenido con filtros y paginación
export const getContent = asyncHandler(async (req: Request, res: Response) => {
  const {
    page = 1,
    limit = 20,
    category,
    type,
    search,
    featured,
    sort = 'recent',
  } = req.query as unknown as ContentQueryParams;

  const offset = (Number(page) - 1) * Number(limit);
  
  // Intentar obtener de cache
  const cacheKey = `content:list:${JSON.stringify(req.query)}`;
  const cached = await cacheGet(cacheKey);
  if (cached) {
    return res.json({ success: true, ...cached, cached: true });
  }

  // Construir query dinámica
  const conditions: string[] = ['c.deleted_at IS NULL', "c.status = 'active'"];
  const params: any[] = [];
  let paramIndex = 1;

  if (category) {
    conditions.push(`c.category_id = $${paramIndex}`);
    params.push(category);
    paramIndex++;
  }

  if (type) {
    conditions.push(`c.type = $${paramIndex}`);
    params.push(type);
    paramIndex++;
  }

  if (featured !== undefined) {
    conditions.push(`c.is_featured = $${paramIndex}`);
    params.push(featured === 'true' || featured === true);
    paramIndex++;
  }

  if (search) {
    conditions.push(`(
      to_tsvector('spanish', c.title || ' ' || COALESCE(c.description, '')) 
      @@ plainto_tsquery('spanish', $${paramIndex})
      OR c.title ILIKE $${paramIndex + 1}
    )`);
    params.push(search, `%${search}%`);
    paramIndex += 2;
  }

  // Ordenamiento
  let orderBy = 'c.created_at DESC';
  if (sort === 'popular') orderBy = 'c.access_count DESC';
  if (sort === 'rating') orderBy = 'c.average_rating DESC NULLS LAST';

  // Query principal
  const contentQuery = `
    SELECT 
      c.id, c.title, c.description, c.type, c.thumbnail_path,
      c.duration_seconds, c.file_size, c.access_count, 
      c.average_rating, c.is_featured, c.created_at,
      cat.name as category_name
    FROM content c
    LEFT JOIN categories cat ON c.category_id = cat.id
    WHERE ${conditions.join(' AND ')}
    ORDER BY ${orderBy}
    LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
  `;

  params.push(Number(limit), offset);

  // Query de conteo
  const countQuery = `
    SELECT COUNT(*) as total
    FROM content c
    WHERE ${conditions.join(' AND ')}
  `;

  const [contentResult, countResult] = await Promise.all([
    query(contentQuery, params),
    query(countQuery, params.slice(0, -2)), // Sin LIMIT/OFFSET
  ]);

  const total = parseInt(countResult.rows[0].total);
  const totalPages = Math.ceil(total / Number(limit));

  const response = {
    data: contentResult.rows,
    pagination: {
      page: Number(page),
      limit: Number(limit),
      total,
      total_pages: totalPages,
    },
  };

  // Cachear por 5 minutos
  await cacheSet(cacheKey, response, 300);

  res.json({
    success: true,
    ...response,
  });
});

// GET /api/content/:id - Detalle de contenido
export const getContentById = asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;

  // Intentar cache
  const cacheKey = `content:detail:${id}`;
  const cached = await cacheGet(cacheKey);
  if (cached) {
    return res.json({ success: true, data: cached, cached: true });
  }

  const result = await query(
    `
    SELECT 
      c.*,
      cat.name as category_name, cat.slug as category_slug,
      u.full_name as created_by_name,
      COALESCE(
        json_agg(
          json_build_object('id', t.id, 'name', t.name, 'slug', t.slug)
        ) FILTER (WHERE t.id IS NOT NULL),
        '[]'
      ) as tags
    FROM content c
    LEFT JOIN categories cat ON c.category_id = cat.id
    LEFT JOIN users u ON c.created_by = u.id
    LEFT JOIN content_tags ct ON c.id = ct.content_id
    LEFT JOIN tags t ON ct.tag_id = t.id
    WHERE c.id = $1 AND c.deleted_at IS NULL
    GROUP BY c.id, cat.name, cat.slug, u.full_name
    `,
    [id]
  );

  if (result.rowCount === 0) {
    throw new AppError('Content not found', 404);
  }

  const content = result.rows[0];

  // Cachear por 1 hora
  await cacheSet(cacheKey, content, 3600);

  res.json({
    success: true,
    data: content,
  });
});

// GET /api/content/featured - Contenido destacado
export const getFeaturedContent = asyncHandler(async (req: Request, res: Response) => {
  const cacheKey = 'content:featured';
  const cached = await cacheGet(cacheKey);
  if (cached) {
    return res.json({ success: true, data: cached, cached: true });
  }

  const result = await query(`
    SELECT 
      c.id, c.title, c.description, c.type, c.thumbnail_path,
      c.duration_seconds, c.access_count, c.average_rating,
      cat.name as category_name
    FROM content c
    LEFT JOIN categories cat ON c.category_id = cat.id
    WHERE c.is_featured = true 
      AND c.deleted_at IS NULL 
      AND c.status = 'active'
    ORDER BY c.created_at DESC
    LIMIT 10
  `);

  await cacheSet(cacheKey, result.rows, 600); // 10 minutos

  res.json({
    success: true,
    data: result.rows,
  });
});
