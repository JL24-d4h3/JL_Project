# Receiver Platform Architecture Plan

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CDN ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   search_ui  │     │   receiver   │     │    admin     │        │
│  │   :5174      │     │   :5176      │     │   :5177      │        │
│  │              │     │              │     │              │        │
│  │ AI Search    │────▶│ 4 Platforms  │     │ Management   │        │
│  │ Engine       │     │              │     │ Panel        │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                 │
│         │                    ▼                    │                 │
│         │           ┌──────────────┐              │                 │
│         └──────────▶│  ai_engine   │◀─────────────┘                 │
│                     │   :8000      │                                │
│                     │              │                                │
│                     │ ChromaDB +   │                                │
│                     │ PostgreSQL   │                                │
│                     └──────────────┘                                │
│                            │                                        │
│                            ▼                                        │
│                     ┌──────────────┐                                │
│                     │   storage    │                                │
│                     │  /mnt/ssd    │                                │
│                     └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

## 1. Receiver Routes (`client/receiver`)

### 1.1 Main Routes

```
/                                    → Landing (redirect to /educational-platform)
/sign-in                             → Sign in page
/sign-up                             → Sign up page

# Public (catalog only)
/educational-platform                → Course catalog (public)

# Protected (requires auth) - URL includes username and role
/:username/:role/courses             → My courses dashboard
/:username/:role/courses/:slug       → Course detail (sections, content)
/:username/:role/courses/:slug/viewer/:contentId → Content viewer

/library                             → Digital library
/library/:id                         → Document viewer

/projects                            → Academic projects
/projects/:id                        → Project detail

/news                                → News and updates
/news/:id                            → Full article
```

### 1.2 URL Structure Examples

```
# Student viewing a course
/JL24/student/software-architecture/
/JL24/student/software-architecture/viewer/abc123

# Teacher editing their course
/prof_garcia/teacher/html-css-intro/
/prof_garcia/teacher/html-css-intro/edit

# Admin with full access
/admin_user/admin/any-course/
```

### 1.3 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     AUTHENTICATION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SCENARIO 1: Sign in from catalog                               │
│  ─────────────────────────────────────────────────────          │
│  User at /educational-platform                                  │
│       │                                                         │
│       │ Clicks "Sign In"                                        │
│       ▼                                                         │
│  /sign-in?redirect=/educational-platform                        │
│       │                                                         │
│       │ After successful login                                  │
│       ▼                                                         │
│  /educational-platform (now logged in)                          │
│                                                                 │
│                                                                 │
│  SCENARIO 2: Sign in from specific course                       │
│  ─────────────────────────────────────────────────────          │
│  User at /educational-platform (clicks course card)             │
│       │                                                         │
│       │ Not logged in → Redirect                                │
│       ▼                                                         │
│  /sign-in?redirect=/JL24/student/software-architecture          │
│       │                                                         │
│       │ After successful login                                  │
│       ▼                                                         │
│  /JL24/student/software-architecture (course page)              │
│                                                                 │
│                                                                 │
│  SCENARIO 3: Sign up flow                                       │
│  ─────────────────────────────────────────────────────          │
│  User clicks "Sign Up"                                          │
│       │                                                         │
│       ▼                                                         │
│  /sign-up?redirect=...                                          │
│       │                                                         │
│       │ Enters: email, username, password                       │
│       ▼                                                         │
│  Redirect to original destination                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema (PostgreSQL)

### 2.1 Tables

```sql
-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    role VARCHAR(20) NOT NULL DEFAULT 'student', -- student, teacher, admin
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- EDUCATIONAL PLATFORM
-- ============================================

CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL, -- URL-friendly identifier
    title VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR(500),
    category VARCHAR(100),
    teacher_id UUID REFERENCES users(id),
    is_published BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE course_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    position INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE course_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID REFERENCES course_sections(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content_type VARCHAR(50) NOT NULL, -- video, pdf, doc, code, audio, image, link
    file_path VARCHAR(500),
    file_size BIGINT,
    duration_seconds INTEGER,
    position INTEGER NOT NULL,
    is_downloadable BOOLEAN DEFAULT true,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- USER INTERACTIONS
-- ============================================

CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP,
    progress_percent INTEGER DEFAULT 0,
    UNIQUE(user_id, course_id)
);

CREATE TABLE content_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES course_contents(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP DEFAULT NOW(),
    watch_duration_seconds INTEGER
);

CREATE TABLE reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES course_contents(id) ON DELETE CASCADE,
    reaction_type VARCHAR(20) NOT NULL, -- like, love, helpful
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, content_id, reaction_type)
);

CREATE TABLE ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, course_id)
);

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES course_contents(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id),
    body TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE comment_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, comment_id)
);

CREATE TABLE favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES course_contents(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, content_id)
);

CREATE TABLE history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID REFERENCES course_contents(id) ON DELETE CASCADE,
    accessed_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- DIGITAL LIBRARY
-- ============================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    page_count INTEGER,
    thumbnail_url VARCHAR(500),
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- PROJECTS
-- ============================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    author_id UUID REFERENCES users(id),
    category VARCHAR(100),
    tags TEXT[],
    thumbnail_url VARCHAR(500),
    repository_url VARCHAR(500),
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE project_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT
);

-- ============================================
-- NEWS
-- ============================================

CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    body TEXT NOT NULL,
    author_id UUID REFERENCES users(id),
    thumbnail_url VARCHAR(500),
    is_featured BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_courses_slug ON courses(slug);
CREATE INDEX idx_courses_category ON courses(category);
CREATE INDEX idx_courses_teacher ON courses(teacher_id);
CREATE INDEX idx_course_contents_section ON course_contents(section_id);
CREATE INDEX idx_enrollments_user ON enrollments(user_id);
CREATE INDEX idx_comments_content ON comments(content_id);
CREATE INDEX idx_content_views_user ON content_views(user_id);
CREATE INDEX idx_history_user ON history(user_id);
```

---

## 3. API Endpoints (ai_engine)

### 3.1 Authentication

```
POST   /api/auth/sign-up              → Create account (email, username, password)
POST   /api/auth/sign-in              → Sign in (email/username + password) → JWT
POST   /api/auth/sign-out             → Sign out (invalidate token)
GET    /api/auth/me                   → Get current user
POST   /api/auth/refresh              → Refresh access token
```

### 3.2 Courses (Educational Platform)

```
# Public
GET    /api/courses                   → List courses (paginated, filterable)
GET    /api/courses/:slug             → Course detail (public info only)

# Protected (requires auth)
GET    /api/courses/:slug/full        → Full course with sections & content
GET    /api/courses/:slug/sections    → Course sections
GET    /api/courses/:slug/content/:id → Specific content item

# Teacher/Admin only
POST   /api/courses                   → Create course
PUT    /api/courses/:slug             → Update course
DELETE /api/courses/:slug             → Delete course
POST   /api/courses/:slug/sections    → Create section
PUT    /api/sections/:id              → Update section
DELETE /api/sections/:id              → Delete section
POST   /api/sections/:id/content      → Upload content
PUT    /api/content/:id               → Update content
DELETE /api/content/:id               → Delete content
POST   /api/content/:id/upload        → Upload file
```

### 3.3 User Interactions (requires auth)

```
POST   /api/courses/:slug/enroll      → Enroll in course
POST   /api/content/:id/view          → Record view
POST   /api/content/:id/reaction      → Add reaction
DELETE /api/content/:id/reaction      → Remove reaction
POST   /api/courses/:slug/rating      → Rate course
POST   /api/content/:id/comments      → Add comment
POST   /api/comments/:id/like         → Like comment
POST   /api/content/:id/favorite      → Add to favorites
DELETE /api/content/:id/favorite      → Remove from favorites
GET    /api/content/:id/download      → Download file
```

### 3.4 User Profile

```
GET    /api/users/:username           → Public profile
GET    /api/users/me/enrollments      → My courses
GET    /api/users/me/history          → My history
GET    /api/users/me/favorites        → My favorites
PUT    /api/users/me                  → Update profile
```

---

## 4. Integration with search_ui

### 4.1 Search Result to Viewer Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 FLOW: search_ui → receiver                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User searches "probability" in search_ui                    │
│                                                                 │
│  2. ai_engine queries ChromaDB + BM25                          │
│                                                                 │
│  3. Results include viewer_url:                                 │
│     {                                                           │
│       "content_id": "uuid-123",                                 │
│       "title": "Monte Carlo Simulations",                       │
│       "snippet": "...axiomatic probability...",                 │
│       "content_type": "pdf",                                    │
│       "viewer_url": "/:username/:role/courses/stats-101/..."   │
│     }                                                           │
│                                                                 │
│  4. User clicks → Redirects to receiver                         │
│                                                                 │
│  5. Receiver checks auth:                                       │
│     - If logged in → Show viewer                                │
│     - If not → /sign-in?redirect=... → Then viewer              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Frontend Structure (Receiver)

### 5.1 Folder Structure

```
client/receiver/src/
├── components/
│   ├── ui/                    # shadcn/ui components
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   ├── auth/
│   │   ├── SignInForm.tsx
│   │   ├── SignUpForm.tsx
│   │   └── ProtectedRoute.tsx
│   ├── course/
│   │   ├── CourseCard.tsx
│   │   ├── CourseGrid.tsx
│   │   ├── SectionAccordion.tsx
│   │   ├── ContentItem.tsx
│   │   └── CourseStats.tsx
│   ├── viewer/
│   │   ├── VideoPlayer.tsx
│   │   ├── PDFViewer.tsx
│   │   ├── CodeViewer.tsx
│   │   └── ImageViewer.tsx
│   └── social/
│       ├── CommentSection.tsx
│       ├── ReactionBar.tsx
│       ├── RatingStars.tsx
│       └── ShareButton.tsx
├── pages/
│   ├── SignInPage.tsx
│   ├── SignUpPage.tsx
│   ├── CatalogPage.tsx
│   ├── CoursePage.tsx
│   ├── ViewerPage.tsx
│   └── TeacherDashboard.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useCourse.ts
│   └── useViewer.ts
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── utils.ts
└── stores/
    ├── authStore.ts
    └── uiStore.ts
```

---

## 6. Implementation Phases

### Phase 1: Authentication & Database
- [x] Create SQL migrations
- [ ] Implement auth endpoints (sign-in, sign-up, sign-out)
- [ ] Create SignInPage and SignUpPage components
- [ ] Implement ProtectedRoute and AuthProvider
- [ ] Configure JWT with refresh tokens

### Phase 2: Educational Platform - Student View
- [ ] CatalogPage: Course grid with filters
- [ ] CoursePage: Detail with sections and content
- [ ] ViewerPage: Viewers for each file type
- [ ] Implement comments and reactions
- [ ] Implement ratings
- [ ] Implement favorites and history

### Phase 3: Educational Platform - Teacher View
- [ ] TeacherDashboard: My courses list
- [ ] CourseEditor: Create/edit course
- [ ] SectionEditor: Create/edit sections
- [ ] ContentUploader: File upload with drag & drop
- [ ] Drag & drop reordering

### Phase 4: Integration with search_ui
- [ ] Add viewer_url to search results
- [ ] Implement deep linking from search_ui
- [ ] Handle post-login redirect to content

### Phase 5: Other Platforms
- [ ] Digital Library
- [ ] Projects
- [ ] News

---

## 7. Tech Stack

### Frontend (receiver)
- React 18 + TypeScript
- Vite
- TailwindCSS
- shadcn/ui (Radix primitives)
- Zustand (state management)
- React Query (data fetching)
- React Router v7

### Backend (ai_engine)
- FastAPI
- PostgreSQL
- python-jose (JWT)
- Pydantic v2
- passlib + bcrypt (password hashing)

### Storage
- PostgreSQL for structured data
- Filesystem for media files
- ChromaDB for search embeddings
