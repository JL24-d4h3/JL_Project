# Estrategia de Testing - CDN Offline

## 1. Pirámide de Testing

```
           /\
          /  \         E2E Tests (5%)
         /____\        - Flujos completos usuario
        /      \       - Tests de integración sistema
       /        \      
      /__________\     Integration Tests (25%)
     /            \    - API + DB
    /              \   - Servicios externos
   /________________\  
  /                  \ Unit Tests (70%)
 /____________________\ - Funciones individuales
                         - Lógica de negocio
```

---

## 2. Tests Unitarios (Unit Tests)

### 2.1 Backend (Node.js + Jest)

**Archivos a testear**:

```
server/src/
├── services/
│   ├── contentService.test.ts
│   ├── storageService.test.ts
│   ├── evictionService.test.ts
│   └── authService.test.ts
├── utils/
│   ├── hash.test.ts
│   ├── validation.test.ts
│   └── fileUtils.test.ts
└── middleware/
    └── auth.test.ts
```

**Ejemplo: contentService.test.ts**

```typescript
import { ContentService } from './contentService';
import { mockDB, mockRedis } from '../__mocks__';

describe('ContentService', () => {
  let service: ContentService;
  
  beforeEach(() => {
    service = new ContentService(mockDB, mockRedis);
  });
  
  describe('getContentById', () => {
    it('should return content from cache if available', async () => {
      const mockContent = { id: '123', title: 'Test Video' };
      mockRedis.get.mockResolvedValue(JSON.stringify(mockContent));
      
      const result = await service.getContentById('123');
      
      expect(result).toEqual(mockContent);
      expect(mockDB.query).not.toHaveBeenCalled();
    });
    
    it('should fetch from DB if cache miss', async () => {
      mockRedis.get.mockResolvedValue(null);
      mockDB.query.mockResolvedValue({ rows: [{ id: '123', title: 'Test' }] });
      
      const result = await service.getContentById('123');
      
      expect(mockDB.query).toHaveBeenCalled();
      expect(mockRedis.setex).toHaveBeenCalled();
    });
    
    it('should throw error if content not found', async () => {
      mockRedis.get.mockResolvedValue(null);
      mockDB.query.mockResolvedValue({ rows: [] });
      
      await expect(service.getContentById('invalid')).rejects.toThrow('Content not found');
    });
  });
  
  describe('searchContent', () => {
    it('should search by title using full-text search', async () => {
      const query = 'Números Reales';
      mockDB.query.mockResolvedValue({ rows: [{ id: '1', title: 'Números Reales' }] });
      
      const result = await service.searchContent(query);
      
      expect(result).toHaveLength(1);
      expect(mockDB.query.mock.calls[0][0]).toContain('to_tsvector');
    });
  });
});
```

**Ejemplo: evictionService.test.ts**

```typescript
describe('EvictionService', () => {
  describe('getLRUCandidates', () => {
    it('should return least recently accessed content', async () => {
      mockDB.query.mockResolvedValue({
        rows: [
          { id: '1', title: 'Old Content', last_accessed: '2026-01-01' },
          { id: '2', title: 'Newer Content', last_accessed: '2026-02-01' }
        ]
      });
      
      const candidates = await evictionService.getLRUCandidates(5);
      
      expect(candidates[0].id).toBe('1');
    });
    
    it('should respect priority levels', async () => {
      // High priority content should not be evicted
      const candidates = await evictionService.getLRUCandidates(10);
      
      expect(candidates.every(c => c.priority < 10)).toBe(true);
    });
  });
  
  describe('evictContent', () => {
    it('should archive file before deletion', async () => {
      const contentId = '123';
      
      await evictionService.evictContent(contentId);
      
      expect(mockFS.copy).toHaveBeenCalledWith(
        expect.stringContaining('/storage/videos/123'),
        expect.stringContaining('/storage/archived/123')
      );
    });
    
    it('should update database and log eviction', async () => {
      await evictionService.evictContent('123');
      
      expect(mockDB.query).toHaveBeenCalledWith(
        expect.stringContaining('UPDATE content SET deleted_at'),
        expect.anything()
      );
      expect(mockDB.query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO eviction_log'),
        expect.anything()
      );
    });
  });
});
```

### 2.2 Frontend (React + Vitest)

```typescript
// VideoPlayer.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoPlayer } from './VideoPlayer';

describe('VideoPlayer', () => {
  it('should render video player with controls', () => {
    render(<VideoPlayer src="/api/stream/123" />);
    
    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
  });
  
  it('should handle play/pause toggle', () => {
    const { container } = render(<VideoPlayer src="/api/stream/123" />);
    const playButton = screen.getByRole('button', { name: /play/i });
    
    fireEvent.click(playButton);
    
    expect(container.querySelector('video')).toHaveProperty('paused', false);
  });
  
  it('should request appropriate quality based on bandwidth', async () => {
    // Mock network speed detection
    (navigator as any).connection = { downlink: 2 }; // 2 Mbps
    
    render(<VideoPlayer src="/api/stream/123" autoQuality />);
    
    // Should request 480p for low bandwidth
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('quality=480p')
      );
    });
  });
});
```

---

## 3. Tests de Integración

### 3.1 API Tests (Supertest)

```typescript
// api.test.ts
import request from 'supertest';
import { app } from '../src/app';
import { db } from '../src/config/database';

describe('Content API', () => {
  let authToken: string;
  let testContentId: string;
  
  beforeAll(async () => {
    // Setup test database
    await db.migrate.latest();
    await db.seed.run();
    
    // Login to get auth token
    const res = await request(app)
      .post('/api/auth/login')
      .send({ username: 'admin', password: 'test123' });
    authToken = res.body.token;
  });
  
  afterAll(async () => {
    await db.destroy();
  });
  
  describe('GET /api/content', () => {
    it('should return list of content', async () => {
      const res = await request(app)
        .get('/api/content')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);
      
      expect(res.body).toHaveProperty('data');
      expect(Array.isArray(res.body.data)).toBe(true);
    });
    
    it('should filter by category', async () => {
      const res = await request(app)
        .get('/api/content?category=matematicas')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);
      
      expect(res.body.data.every(c => c.category === 'matematicas')).toBe(true);
    });
    
    it('should return 401 without auth', async () => {
      await request(app)
        .get('/api/content')
        .expect(401);
    });
  });
  
  describe('POST /api/content/upload', () => {
    it('should upload video file', async () => {
      const res = await request(app)
        .post('/api/content/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .field('title', 'Test Video')
        .field('category', 'matematicas')
        .attach('file', '__tests__/fixtures/sample.mp4')
        .expect(201);
      
      testContentId = res.body.id;
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe('Test Video');
    });
    
    it('should reject non-video files for video content', async () => {
      await request(app)
        .post('/api/content/upload')
        .set('Authorization', `Bearer ${authToken}`)
        .field('type', 'video')
        .attach('file', '__tests__/fixtures/document.pdf')
        .expect(400);
    });
    
    it('should reject uploads without teacher/admin role', async () => {
      // Login as student
      const studentRes = await request(app)
        .post('/api/auth/login')
        .send({ username: 'student1', password: 'test123' });
      
      await request(app)
        .post('/api/content/upload')
        .set('Authorization', `Bearer ${studentRes.body.token}`)
        .attach('file', '__tests__/fixtures/sample.mp4')
        .expect(403);
    });
  });
  
  describe('GET /api/stream/:id', () => {
    it('should stream video with HTTP range support', async () => {
      const res = await request(app)
        .get(`/api/stream/${testContentId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .set('Range', 'bytes=0-1023')
        .expect(206); // Partial Content
      
      expect(res.headers['content-range']).toBeDefined();
      expect(res.headers['accept-ranges']).toBe('bytes');
    });
    
    it('should track access in database', async () => {
      await request(app)
        .get(`/api/stream/${testContentId}`)
        .set('Authorization', `Bearer ${authToken}`);
      
      const logs = await db('access_log')
        .where({ content_id: testContentId })
        .orderBy('accessed_at', 'desc')
        .first();
      
      expect(logs).toBeDefined();
      expect(logs.content_id).toBe(testContentId);
    });
  });
  
  describe('DELETE /api/content/:id', () => {
    it('should soft delete content (admin only)', async () => {
      await request(app)
        .delete(`/api/content/${testContentId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);
      
      const content = await db('content')
        .where({ id: testContentId })
        .first();
      
      expect(content.deleted_at).not.toBeNull();
    });
  });
});
```

### 3.2 Database Integration Tests

```typescript
describe('Database Operations', () => {
  describe('Content deduplication', () => {
    it('should detect duplicate files by hash', async () => {
      const hash = 'abc123def456';
      
      await db('content').insert({
        title: 'Original',
        file_hash: hash,
        file_path: '/storage/1.mp4',
        // ... otros campos
      });
      
      // Intentar insertar duplicado
      const result = await db('content').insert({
        title: 'Duplicate',
        file_hash: hash,
        file_path: '/storage/2.mp4'
      }).catch(err => err);
      
      // El trigger debería lanzar un NOTICE o prevenir duplicados
      expect(result).toBeDefined();
    });
  });
  
  describe('Access count trigger', () => {
    it('should auto-increment on access_log insert', async () => {
      const contentId = await createTestContent();
      const initialCount = await db('content')
        .where({ id: contentId })
        .first()
        .then(c => c.access_count);
      
      await db('access_log').insert({
        content_id: contentId,
        user_id: testUserId
      });
      
      const newCount = await db('content')
        .where({ id: contentId })
        .first()
        .then(c => c.access_count);
      
      expect(newCount).toBe(initialCount + 1);
    });
  });
});
```

---

## 4. Tests End-to-End (E2E)

### 4.1 Playwright/Cypress

```typescript
// e2e/video-playback.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Video Playback Flow', () => {
  test('complete user journey: search → play video', async ({ page }) => {
    // 1. Login
    await page.goto('http://192.168.1.100:3000');
    await page.fill('input[name="username"]', 'student1');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    
    // 2. Search for content
    await page.fill('input[placeholder="Buscar..."]', 'Números Reales');
    await page.keyboard.press('Enter');
    
    // 3. Verify search results
    await expect(page.locator('.content-card')).toHaveCount(1, { timeout: 5000 });
    await expect(page.locator('.content-card').first()).toContainText('Números Reales');
    
    // 4. Click on video
    await page.click('.content-card').first();
    
    // 5. Wait for video player to load
    await expect(page.locator('video')).toBeVisible({ timeout: 10000 });
    
    // 6. Play video
    await page.click('button[aria-label="Play"]');
    
    // 7. Verify video is playing
    const isPaused = await page.locator('video').evaluate((video: HTMLVideoElement) => video.paused);
    expect(isPaused).toBe(false);
    
    // 8. Wait a few seconds and check progress
    await page.waitForTimeout(3000);
    const currentTime = await page.locator('video').evaluate((video: HTMLVideoElement) => video.currentTime);
    expect(currentTime).toBeGreaterThan(0);
  });
  
  test('admin can upload new content', async ({ page }) => {
    // Login as admin
    await page.goto('http://192.168.1.100:3000/admin');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Navigate to upload
    await page.click('text=Subir Contenido');
    
    // Fill form
    await page.fill('input[name="title"]', 'E2E Test Video');
    await page.selectOption('select[name="category"]', 'matematicas');
    await page.setInputFiles('input[type="file"]', 'test-fixtures/sample-video.mp4');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Verify success
    await expect(page.locator('.success-message')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('.success-message')).toContainText('subido exitosamente');
  });
});
```

---

## 5. Tests de Performance y Carga

### 5.1 Artillery (Load Testing)

```yaml
# load-test.yml
config:
  target: 'http://192.168.1.100:3000'
  phases:
    - duration: 60
      arrivalRate: 10 # 10 usuarios/segundo
      name: "Warm up"
    - duration: 300
      arrivalRate: 50 # 50 usuarios/segundo
      name: "Sustained load"
    - duration: 120
      arrivalRate: 100 # Spike
      name: "Stress test"
  processor: "./test-functions.js"

scenarios:
  - name: "Stream video concurrently"
    weight: 70
    flow:
      - post:
          url: "/api/auth/login"
          json:
            username: "student{{ $randomNumber(1, 100) }}"
            password: "test123"
          capture:
            - json: "$.token"
              as: "authToken"
      - get:
          url: "/api/content"
          headers:
            Authorization: "Bearer {{ authToken }}"
          capture:
            - json: "$.data[0].id"
              as: "contentId"
      - get:
          url: "/api/stream/{{ contentId }}"
          headers:
            Authorization: "Bearer {{ authToken }}"
            Range: "bytes=0-5242880" # Stream first 5MB
  
  - name: "Search content"
    weight: 20
    flow:
      - get:
          url: "/api/search?q=matematicas"
  
  - name: "Browse categories"
    weight: 10
    flow:
      - get:
          url: "/api/content?category=matematicas"

```

**Ejecutar**:
```bash
artillery run load-test.yml --output report.json
artillery report report.json --output report.html
```

**Métricas objetivo**:
- Response time (p95): < 500ms para API
- Response time (p95): < 2s para inicio de streaming
- Error rate: < 1%
- Throughput: >= 50 RPS
- Concurrent streams: >= 20 videos simultáneos

### 5.2 K6 (Alternative)

```javascript
// k6-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // Login
  let loginRes = http.post('http://192.168.1.100:3000/api/auth/login', {
    username: 'student1',
    password: 'test123',
  });
  
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });
  
  let token = loginRes.json('token');
  
  // Get content list
  let listRes = http.get('http://192.168.1.100:3000/api/content', {
    headers: { Authorization: `Bearer ${token}` },
  });
  
  check(listRes, {
    'content list loaded': (r) => r.status === 200,
  });
  
  sleep(1);
}
```

---

## 6. Tests de Red y Conectividad

### 6.1 Simulación de Condiciones de Red

```bash
# Linux: Usar tc (traffic control) para simular latencia/pérdida de paquetes

# Añadir 100ms de latencia
sudo tc qdisc add dev eth0 root netem delay 100ms

# Simular 5% de pérdida de paquetes
sudo tc qdisc change dev eth0 root netem loss 5%

# Limitar ancho de banda a 1Mbps
sudo tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms

# Limpiar reglas
sudo tc qdisc del dev eth0 root
```

**Test con condiciones adversas**:
```typescript
test('video should continue playing with packet loss', async ({ page }) => {
  // Ejecutar este test con tc configurado para 5% de pérdida
  await page.goto('http://192.168.1.100:3000/player/123');
  
  await page.click('button[aria-label="Play"]');
  
  // Esperar 30 segundos de reproducción
  await page.waitForTimeout(30000);
  
  // Verificar que no haya errores y el video avance
  const currentTime = await page.locator('video').evaluate(v => v.currentTime);
  expect(currentTime).toBeGreaterThan(25); // Al menos 25s de 30s
  
  const hasError = await page.locator('.video-error').isVisible().catch(() => false);
  expect(hasError).toBe(false);
});
```

---

## 7. Tests de Seguridad

### 7.1 Security Checks

```typescript
describe('Security Tests', () => {
  test('SQL injection prevention', async () => {
    const maliciousInput = "' OR '1'='1"; --";
    
    const res = await request(app)
      .get(`/api/search?q=${encodeURIComponent(maliciousInput)}`)
      .set('Authorization', `Bearer ${authToken}`);
    
    // No debería retornar todos los registros
    expect(res.body.data.length).toBeLessThan(100);
  });
  
  test('XSS prevention in title display', async () => {
    const xssPayload = '<script>alert("XSS")</script>';
    
    await request(app)
      .post('/api/content/upload')
      .set('Authorization', `Bearer ${adminToken}`)
      .field('title', xssPayload)
      .attach('file', 'test.mp4');
    
    const res = await request(app).get('/api/content');
    
    // El payload debe estar escapado
    expect(res.text).not.toContain('<script>');
  });
  
  test('unauthorized access to admin endpoints', async () => {
    await request(app)
      .delete('/api/content/123')
      .set('Authorization', `Bearer ${studentToken}`)
      .expect(403);
  });
  
  test('file upload size limit', async () => {
    // Intentar subir archivo de 2GB (debe fallar si límite es 1GB)
    const res = await request(app)
      .post('/api/content/upload')
      .set('Authorization', `Bearer ${adminToken}`)
      .field('title', 'Large File')
      .attach('file', 'huge-file.mp4') // Mock de 2GB
      .expect(413); // Payload Too Large
  });
});
```

---

## 8. Tests de Eviction

```typescript
describe('Eviction Policy Tests', () => {
  beforeEach(async () => {
    // Poblar DB con contenido de prueba
    await seedTestContent(100); // 100 videos
  });
  
  test('LRU eviction removes least recently accessed', async () => {
    // Marcar algunos contenidos como accedidos recientemente
    await accessContent(['id1', 'id2', 'id3']);
    
    // Simular disco lleno (80% usado)
    mockStorageUsage(0.85);
    
    // Ejecutar eviction
    await evictionService.checkAndEvict();
    
    // Verificar que contenidos recientes NO fueron eliminados
    const recentContent = await db('content')
      .whereIn('id', ['id1', 'id2', 'id3'])
      .where({ deleted_at: null });
    
    expect(recentContent.length).toBe(3);
    
    // Verificar que contenidos antiguos SÍ fueron eliminados
    const oldContent = await db('content')
      .where('last_accessed', '<', new Date(Date.now() - 90 * 24 * 60 * 60 * 1000))
      .where({ deleted_at: null });
    
    expect(oldContent.length).toBeLessThan(10);
  });
  
  test('high priority content is never evicted', async () => {
    await db('content')
      .where({ id: 'important-video' })
      .update({ priority: 10 });
    
    mockStorageUsage(0.95); // 95% lleno - situación crítica
    
    await evictionService.checkAndEvict();
    
    const content = await db('content')
      .where({ id: 'important-video' })
      .first();
    
    expect(content.deleted_at).toBeNull();
  });
});
```

---

## 9. CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: CI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: cdn_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd server && npm ci
          cd ../client && npm ci
      
      - name: Run unit tests
        run: cd server && npm test
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/cdn_test
          REDIS_URL: redis://localhost:6379
        run: cd server && npm run test:integration
      
      - name: Build frontend
        run: cd client && npm run build
      
      - name: Run E2E tests
        run: cd client && npm run test:e2e
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 10. Checklist de Testing Pre-Release

```markdown
## Funcionalidades Core
- [ ] Login/logout funciona para todos los roles
- [ ] Búsqueda retorna resultados relevantes
- [ ] Videos se reproducen sin buffering excesivo (<3s inicial)
- [ ] Upload de contenido funciona (video, PDF)
- [ ] Thumbnails se generan correctamente
- [ ] Permisos por rol se respetan

## Performance
- [ ] 50 usuarios concurrentes sin degradación
- [ ] 10 streams simultáneos funcionan
- [ ] API response time p95 < 500ms
- [ ] Database queries optimizadas (< 100ms)

## Almacenamiento
- [ ] Eviction se activa al 80% de uso
- [ ] Archivos eliminados se archivan primero
- [ ] No se eliminan archivos con priority >= 10
- [ ] Logs de eviction se registran correctamente

## Seguridad
- [ ] No hay SQL injection
- [ ] XSS está prevenido
- [ ] HTTPS funciona (si aplica)
- [ ] Rate limiting funciona
- [ ] Tokens JWT expiran correctamente

## Backups
- [ ] Backup diario se ejecuta
- [ ] Restore funciona correctamente
- [ ] Archivos y DB están sincronizados en backup

## Red
- [ ] Funciona en red WiFi local
- [ ] DNS local resuelve nombres
- [ ] QoS prioriza streaming
- [ ] Soporta 5% pérdida de paquetes

## UX
- [ ] Interfaz responsive (móvil/tablet/desktop)
- [ ] Mensajes de error claros
- [ ] Loading states apropiados
- [ ] Offline detection funciona
```

---

Este plan de testing asegura:
✅ Cobertura completa (unit, integration, E2E)
✅ Performance validado bajo carga
✅ Seguridad verificada
✅ Resiliencia ante fallos de red
✅ Funcionalidad crítica testeada antes de producción
