import { Request, Response } from 'express';
import { pool } from '../config/database.js';

export const getCourses = async (req: Request, res: Response) => {
  try {
    const { limit = 50, page = 1, category } = req.query;
    const offset = (Number(page) - 1) * Number(limit);

    let sql = `
      SELECT 
        id, slug, title, description, thumbnail_url, 
        category, is_published, view_count, like_count, created_at, updated_at
      FROM courses
      WHERE is_published = true
    `;
    const params: any[] = [];
    let paramCount = 1;

    if (category) {
      sql += ` AND category = $${paramCount}`;
      params.push(category);
      paramCount++;
    }

    sql += ` ORDER BY created_at DESC LIMIT $${paramCount} OFFSET $${paramCount + 1}`;
    params.push(limit, offset);

    const result = await pool.query(sql, params);
    const courses = result.rows;

    // Get total count
    let countSql = 'SELECT COUNT(*) as count FROM courses WHERE is_published = true';
    const countParams: any[] = [];
    if (category) {
      countSql += ' AND category = $1';
      countParams.push(category);
    }
    const countResult = await pool.query(countSql, countParams);
    const total = parseInt(countResult.rows[0].count);

    res.json({
      success: true,
      data: courses,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        total_pages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    console.error('Error getting courses:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get courses',
    });
  }
};

export const getCourseById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await pool.query(
      `SELECT * FROM courses WHERE id = $1 AND is_published = true`,
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Course not found',
      });
    }

    res.json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    console.error('Error getting course:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get course',
    });
  }
};

export const getCourseBySlug = async (req: Request, res: Response) => {
  try {
    const { slug } = req.params;

    const result = await pool.query(
      `SELECT * FROM courses WHERE slug = $1 AND is_published = true`,
      [slug]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Course not found',
      });
    }

    res.json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    console.error('Error getting course:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get course',
    });
  }
};
