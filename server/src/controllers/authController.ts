import { Request, Response } from 'express';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { query } from '../config/database.js';
import { asyncHandler, AppError } from '../types/express.js';
import { LoginRequest, LoginResponse, UserDTO } from '../models/index.js';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

// POST /api/auth/login
export const login = asyncHandler(async (req: Request, res: Response) => {
  const { username, password } = req.body as LoginRequest;

  if (!username || !password) {
    throw new AppError('Username and password are required', 400);
  }

  // Buscar usuario
  const result = await query(
    'SELECT * FROM users WHERE username = $1 AND is_active = true',
    [username]
  );

  if (result.rowCount === 0) {
    throw new AppError('Invalid credentials', 401);
  }

  const user = result.rows[0];

  // Verificar si está bloqueado
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    const minutesLeft = Math.ceil(
      (new Date(user.locked_until).getTime() - Date.now()) / 60000
    );
    throw new AppError(
      `Account locked. Try again in ${minutesLeft} minutes`,
      423
    );
  }

  // Verificar contraseña
  const isValidPassword = await bcrypt.compare(password, user.password_hash);

  if (!isValidPassword) {
    // Incrementar intentos fallidos
    const newAttempts = user.login_attempts + 1;
    const lockUntil = newAttempts >= 5 
      ? new Date(Date.now() + 15 * 60 * 1000) // 15 minutos
      : null;

    await query(
      'UPDATE users SET login_attempts = $1, locked_until = $2 WHERE id = $3',
      [newAttempts, lockUntil, user.id]
    );

    if (lockUntil) {
      throw new AppError('Too many failed attempts. Account locked for 15 minutes', 423);
    }

    throw new AppError('Invalid credentials', 401);
  }

  // Login exitoso - resetear intentos y actualizar last_login
  await query(
    'UPDATE users SET login_attempts = 0, locked_until = NULL, last_login = NOW() WHERE id = $1',
    [user.id]
  );

  // Generar JWT
  const token = jwt.sign(
    { id: user.id, username: user.username, role: user.role },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES_IN as string }
  );

  // Crear sesión
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  await query(
    `INSERT INTO sessions (user_id, token_hash, ip_address, user_agent, expires_at)
     VALUES ($1, $2, $3, $4, NOW() + INTERVAL '7 days')`,
    [user.id, tokenHash, req.ip, req.get('user-agent')]
  );

  const userDTO: UserDTO = {
    id: user.id,
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    is_active: user.is_active,
    created_at: user.created_at,
  };

  const response: LoginResponse = {
    token,
    user: userDTO,
    expires_in: 7 * 24 * 60 * 60, // 7 días en segundos
  };

  res.json({
    success: true,
    data: response,
  });
});

// GET /api/auth/me - Usuario actual
export const getMe = asyncHandler(async (req: Request, res: Response) => {
  if (!req.user) {
    throw new AppError('Not authenticated', 401);
  }

  const result = await query(
    'SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE id = $1',
    [req.user.id]
  );

  if (result.rowCount === 0) {
    throw new AppError('User not found', 404);
  }

  res.json({
    success: true,
    data: result.rows[0],
  });
});

// POST /api/auth/logout
export const logout = asyncHandler(async (req: Request, res: Response) => {
  const token = req.headers.authorization?.replace('Bearer ', '');

  if (token) {
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    await query('UPDATE sessions SET is_active = false WHERE token_hash = $1', [tokenHash]);
  }

  res.json({
    success: true,
    message: 'Logged out successfully',
  });
});

// GET /api/auth/users - Lista de usuarios (solo admin/superadmin)
export const getUsers = asyncHandler(async (_req: Request, res: Response) => {
  const result = await query(
    `SELECT id, username, email, full_name, role, is_active, last_login, created_at
     FROM users
     ORDER BY role ASC, created_at ASC`,
    []
  );

  res.json({ success: true, data: result.rows, count: result.rowCount });
});
