import { Request, Response, NextFunction } from 'express';

// Extender Express Request para incluir user
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        username: string;
        role: string;
      };
    }
  }
}

export interface ErrorResponse {
  error: string;
  message: string;
  status: number;
  timestamp: string;
}

export class AppError extends Error {
  constructor(
    public message: string,
    public statusCode: number = 500,
    public isOperational: boolean = true
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

export const asyncHandler = (fn: Function) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

export const errorHandler = (
  err: Error | AppError,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const statusCode = err instanceof AppError ? err.statusCode : 500;
  const isOperational = err instanceof AppError ? err.isOperational : false;

  console.error('Error:', {
    message: err.message,
    stack: err.stack,
    statusCode,
    isOperational,
    path: req.path,
  });

  res.status(statusCode).json({
    error: err.name || 'Error',
    message: err.message || 'Internal server error',
    status: statusCode,
    timestamp: new Date().toISOString(),
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  } as ErrorResponse);
};
