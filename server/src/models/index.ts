// ================================================
// TIPOS Y ENUMS
// ================================================

export enum UserRole {
  STUDENT = 'student',
  TEACHER = 'teacher',
  ADMIN = 'admin',
  SUPERADMIN = 'superadmin'
}

export enum ContentType {
  VIDEO = 'video',
  PDF = 'pdf',
  AUDIO = 'audio',
  INTERACTIVE = 'interactive',
  IMAGE = 'image',
  DOCUMENT = 'document'
}

export enum ContentStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  REJECTED = 'rejected',
  ARCHIVED = 'archived',
  PROCESSING = 'processing',
  FAILED = 'failed'
}

// ================================================
// INTERFACES DE MODELOS
// ================================================

export interface User {
  id: string;
  username: string;
  email: string | null;
  password_hash: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  last_login: Date | null;
  login_attempts: number;
  locked_until: Date | null;
  created_at: Date;
  updated_at: Date;
  metadata: Record<string, any>;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
  icon: string | null;
  color: string | null;
  display_order: number;
  is_active: boolean;
  created_at: Date;
}

export interface Tag {
  id: string;
  name: string;
  slug: string;
  usage_count: number;
  created_at: Date;
}

export interface Content {
  id: string;
  title: string;
  slug: string | null;
  description: string | null;
  type: ContentType;
  category_id: string | null;
  
  // Archivo
  file_path: string;
  file_size: number;
  file_hash: string;
  mime_type: string | null;
  
  // Multimedia
  duration_seconds: number | null;
  resolution: string | null;
  bitrate: number | null;
  
  // Previews
  thumbnail_path: string | null;
  preview_path: string | null;
  quality_versions: Record<string, string>;
  
  // Cache HTTP
  cache_control: string;
  etag: string | null;
  ttl: number;
  last_modified: Date;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Stats
  access_count: number;
  download_count: number;
  average_rating: number | null;
  rating_count: number;
  
  // Estado
  status: ContentStatus;
  rejected_reason: string | null;
  priority: number;
  is_featured: boolean;
  
  // Auditoría
  created_by: string | null;
  updated_by: string | null;
  created_at: Date;
  updated_at: Date;
  last_accessed: Date | null;
  deleted_at: Date | null;
  deleted_by: string | null;
}

export interface StorageNode {
  id: string;
  name: string;
  hostname: string;
  ip_address: string;
  port: number;
  zone_id: string | null;
  total_capacity_bytes: number;
  used_capacity_bytes: number;
  available_capacity_bytes: number | null;
  status: 'online' | 'offline' | 'maintenance' | 'degraded';
  health_score: number;
  latency_ms: number | null;
  bandwidth_mbps: number | null;
  node_type: 'origin' | 'edge' | 'backup';
  version: string | null;
  last_heartbeat: Date | null;
  created_at: Date;
  updated_at: Date;
  metadata: Record<string, any>;
}

// ================================================
// DTOs (Data Transfer Objects)
// ================================================

export interface ContentListDTO {
  id: string;
  title: string;
  description: string | null;
  type: ContentType;
  category_name: string | null;
  thumbnail_path: string | null;
  duration_seconds: number | null;
  file_size: number;
  access_count: number;
  average_rating: number | null;
  is_featured: boolean;
  created_at: Date;
}

export interface ContentDetailDTO extends ContentListDTO {
  slug: string | null;
  resolution: string | null;
  bitrate: number | null;
  quality_versions: Record<string, string>;
  tags: Tag[];
  category: Category | null;
  created_by_name: string | null;
  etag: string | null;
}

export interface UserDTO {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: Date;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: UserDTO;
  expires_in: number;
}

// ================================================
// REQUEST QUERY PARAMS
// ================================================

export interface ContentQueryParams {
  page?: number;
  limit?: number;
  category?: string;
  type?: ContentType;
  search?: string;
  featured?: boolean;
  sort?: 'recent' | 'popular' | 'rating';
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}
