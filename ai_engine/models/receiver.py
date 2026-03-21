"""
Database models and schemas for receiver platform.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

# ============================================
# AUTH SCHEMAS
# ============================================

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=255)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserSignIn(BaseModel):
    email_or_username: str
    password: str

class User(UserBase):
    id: UUID
    avatar_url: Optional[str] = None
    role: str = "student"  # student, teacher, admin
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[str] = None

# ============================================
# COURSE SCHEMAS
# ============================================

class CourseBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    is_published: Optional[bool] = None

class Course(CourseBase):
    id: UUID
    teacher_id: Optional[UUID] = None
    is_published: bool = False
    view_count: int = 0
    like_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# SECTION SCHEMAS
# ============================================

class SectionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    position: int

class SectionCreate(SectionBase):
    course_id: UUID

class Section(SectionBase):
    id: UUID
    course_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================
# CONTENT SCHEMAS
# ============================================

class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    content_type: str  # video, pdf, doc, code, audio, image, link
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration_seconds: Optional[int] = None
    position: int
    is_downloadable: bool = True

class ContentCreate(ContentBase):
    section_id: UUID

class Content(ContentBase):
    id: UUID
    section_id: UUID
    view_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================
# INTERACTION SCHEMAS
# ============================================

class EnrollmentCreate(BaseModel):
    course_id: UUID

class Enrollment(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    enrolled_at: datetime
    last_accessed_at: Optional[datetime] = None
    progress_percent: int = 0

    class Config:
        from_attributes = True

class ReactionCreate(BaseModel):
    content_id: UUID
    reaction_type: str  # like, love, helpful

class CommentCreate(BaseModel):
    content_id: UUID
    body: str
    parent_id: Optional[UUID] = None

class Comment(BaseModel):
    id: UUID
    user_id: UUID
    content_id: UUID
    parent_id: Optional[UUID] = None
    body: str
    like_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RatingCreate(BaseModel):
    course_id: UUID
    rating: int = Field(..., ge=1, le=5)
