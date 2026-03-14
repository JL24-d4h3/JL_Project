import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { query } from '../config/database.js';
import { AppError } from '../types/express.js';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

export const authenticate = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new AppError('No token provided', 401);
    }

    const token = authHeader.replace('Bearer ', '');

    // Verificar JWT
    const decoded = jwt.verify(token, JWT_SECRET) as any;

    // Verificar que la sesión existe y está activa
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    const sessionResult = await query(
      `SELECT * FROM sessions 
       WHERE token_hash = $1 
       AND is_active = true 
       AND expires_at > NOW()`,
      [tokenHash]
    );

    if (sessionResult.rowCount === 0) {
      throw new AppError('Invalid or expired token', 401);
    }

    // Actualizar last_activity
    await query(
      'UPDATE sessions SET last_activity = NOW() WHERE token_hash = $1',
      [tokenHash]
    );

    // Adjuntar usuario al request
    req.user = {
      id: decoded.id,
      username: decoded.username,
      role: decoded.role,
    };

    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      next(new AppError('Invalid token', 401));
    } else if (error instanceof jwt.TokenExpiredError) {
      next(new AppError('Token expired', 401));
    } else {
      next(error);
    }
  }
};

// Middleware para verificar roles
export const authorize = (...roles: string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new AppError('Not authenticated', 401));
    }

    if (!roles.includes(req.user.role)) {
      return next(
        new AppError(`Role '${req.user.role}' is not authorized for this action`, 403)
      );
    }

    next();
  };
};
