# Diagramas de Arquitectura - CDN Offline

## 1. Flujo de Solicitud de Contenido

```mermaid
sequenceDiagram
    participant U as Usuario (Laptop)
    participant F as Frontend (React)
    participant A as API Server
    participant C as Cache (Redis)
    participant D as PostgreSQL
    participant S as Storage (FS)

    U->>F: Busca "Números Reales"
    F->>A: GET /api/search?q=numeros%20reales
    A->>C: Verificar cache
    
    alt Cache Hit
        C-->>A: Resultados cacheados
    else Cache Miss
        A->>D: Query full-text search
        D-->>A: Resultados
        A->>C: Guardar en cache (1h TTL)
    end
    
    A-->>F: JSON con resultados
    F-->>U: Muestra lista de videos
    
    U->>F: Click en video
    F->>A: GET /api/content/:id (metadata)
    A->>C: Verificar metadata en cache
    C-->>A: Metadata del video
    A-->>F: JSON con info del video
    
    F->>A: GET /api/stream/:id (video)
    Note over F,A: HTTP Range Request<br/>Range: bytes=0-1048575
    
    A->>D: Registrar acceso (access_log)
    A->>D: Incrementar access_count
    A->>S: Leer archivo desde disco
    S-->>A: Stream de bytes
    A-->>F: 206 Partial Content<br/>Content-Range: bytes 0-1048575/52428800
    F-->>U: Reproduce video
    
    loop Cada chunk del video
        F->>A: GET /api/stream/:id<br/>Range: bytes=1048576-2097151
        A->>S: Leer siguiente chunk
        S-->>A: Bytes
        A-->>F: 206 Partial Content
    end
```

---

## 2. Flujo de Upload de Contenido

```mermaid
sequenceDiagram
    participant T as Teacher
    participant F as Frontend
    participant A as API Server
    participant Q as Job Queue
    participant D as PostgreSQL
    participant S as Storage
    participant FF as FFmpeg

    T->>F: Sube video "Algebra.mp4"
    F->>A: POST /api/content/upload<br/>multipart/form-data
    
    A->>A: Validar Auth (JWT)
    A->>A: Validar permisos (teacher/admin)
    A->>A: Validar archivo (tipo, tamaño)
    
    A->>S: Guardar en /storage/temp/
    A->>A: Calcular SHA-256 hash
    
    A->>D: Verificar hash duplicado
    
    alt Duplicado encontrado
        D-->>A: Contenido existente
        A-->>F: 409 Conflict<br/>"Este video ya existe"
    else No duplicado
        A->>D: INSERT INTO content<br/>(status='processing')
        D-->>A: content_id
        
        A->>Q: Encolar job: transcode_video<br/>{content_id, file_path}
        A-->>F: 202 Accepted<br/>{id, status: 'processing'}
        
        par Procesamiento asíncrono
            Q->>FF: ffmpeg -i original.mp4<br/>-vf scale=1280:720 720p.mp4
            FF-->>Q: 720p.mp4 listo
            
            Q->>FF: ffmpeg -i original.mp4<br/>-vf scale=854:480 480p.mp4
            FF-->>Q: 480p.mp4 listo
            
            Q->>FF: ffmpeg -i original.mp4<br/>-ss 5 -vframes 1 thumb.jpg
            FF-->>Q: thumbnail listo
            
            Q->>S: Mover archivos a /storage/videos/{id}/
            Q->>D: UPDATE content<br/>SET status='active',<br/>quality_versions={...}
        end
        
        F->>A: (Polling) GET /api/content/:id
        A->>D: SELECT * FROM content
        D-->>A: {status: 'active'}
        A-->>F: Video listo para usar
    end
```

---

## 3. Arquitectura de Componentes

```mermaid
graph TB
    subgraph "Cliente (Browser)"
        UI[React UI]
        Player[Video Player]
        Search[Search Component]
    end
    
    subgraph "API Server (Node.js)"
        Router[Express Router]
        Auth[Auth Middleware]
        ContentAPI[Content API]
        StreamAPI[Stream API]
        UploadAPI[Upload API]
    end
    
    subgraph "Servicios"
        ContentSvc[Content Service]
        StorageSvc[Storage Service]
        EvictionSvc[Eviction Service]
        SyncSvc[Sync Service]
    end
    
    subgraph "Capa de Datos"
        Cache[(Redis)]
        DB[(PostgreSQL)]
        FS[File System<br/>/storage/]
    end
    
    subgraph "Background Jobs"
        Queue[Bull Queue]
        Transcode[Transcode Worker]
        Evict[Eviction Worker]
    end
    
    UI --> Router
    Player --> StreamAPI
    Search --> ContentAPI
    
    Router --> Auth
    Auth --> ContentAPI
    Auth --> StreamAPI
    Auth --> UploadAPI
    
    ContentAPI --> ContentSvc
    StreamAPI --> StorageSvc
    UploadAPI --> StorageSvc
    
    ContentSvc --> Cache
    ContentSvc --> DB
    StorageSvc --> FS
    StorageSvc --> DB
    EvictionSvc --> DB
    EvictionSvc --> FS
    
    UploadAPI --> Queue
    Queue --> Transcode
    Queue --> Evict
    Transcode --> FS
    Transcode --> DB
    Evict --> FS
    Evict --> DB
    
    style UI fill:#3B82F6
    style Player fill:#3B82F6
    style DB fill:#10B981
    style Cache fill:#F59E0B
    style FS fill:#EF4444
```

---

## 4. Modelo de Datos (ER Simplificado)

```mermaid
erDiagram
    USERS ||--o{ CONTENT : creates
    USERS ||--o{ ACCESS_LOG : accesses
    USERS ||--o{ PERMISSIONS : has
    
    CONTENT ||--o{ ACCESS_LOG : tracks
    CONTENT ||--o{ PERMISSIONS : controls
    CONTENT }o--|| CATEGORIES : belongs_to
    CONTENT }o--o{ TAGS : has
    
    CONTENT ||--o{ EVICTION_LOG : evicts
    CONTENT ||--o{ SYNC_STATUS : syncs
    
    USERS {
        uuid id PK
        string username UK
        string password_hash
        string role
        boolean is_active
    }
    
    CONTENT {
        uuid id PK
        string title
        string type
        uuid category_id FK
        string file_path
        bigint file_size
        string file_hash
        int access_count
        timestamp last_accessed
        timestamp deleted_at
    }
    
    CATEGORIES {
        uuid id PK
        string name
        string slug UK
        uuid parent_id FK
    }
    
    TAGS {
        uuid id PK
        string name UK
        int usage_count
    }
    
    ACCESS_LOG {
        uuid id PK
        uuid content_id FK
        uuid user_id FK
        timestamp accessed_at
        int duration_watched
    }
    
    PERMISSIONS {
        uuid id PK
        uuid user_id FK
        uuid content_id FK
        boolean can_read
        boolean can_update
        boolean can_delete
    }
    
    EVICTION_LOG {
        uuid id PK
        uuid content_id
        string reason
        timestamp evicted_at
    }
```

---

## 5. Flujo de Eviction (LRU)

```mermaid
flowchart TD
    Start([Cron Job: Cada hora]) --> CheckDisk{Disco > 80%?}
    
    CheckDisk -->|No| End([Terminar])
    CheckDisk -->|Sí| CalcTarget[Calcular espacio a liberar<br/>Target: llevar a 60% uso]
    
    CalcTarget --> QueryCandidates[Query: SELECT contenido con<br/>- priority < 10<br/>- ORDER BY retention_score ASC]
    
    QueryCandidates --> IterateCandidates{Hay candidatos?}
    
    IterateCandidates -->|No| Alert[Alerta: No hay espacio<br/>y no hay qué borrar]
    IterateCandidates -->|Sí| CheckSpace{Espacio liberado<br/>>= Target?}
    
    CheckSpace -->|No| GetNext[Tomar siguiente candidato]
    CheckSpace -->|Sí| LogStats[Log: Liberados X GB,<br/>Y archivos eliminados]
    
    GetNext --> Archive[Copiar a /storage/archived/]
    Archive --> UpdateDB[(UPDATE content<br/>SET deleted_at = NOW)]
    UpdateDB --> LogEviction[(INSERT INTO eviction_log)]
    LogEviction --> DeleteFile[Eliminar archivo original]
    DeleteFile --> UpdateSpace[Actualizar espacio liberado]
    UpdateSpace --> CheckSpace
    
    LogStats --> End
    Alert --> End
    
    style CheckDisk fill:#F59E0B
    style CheckSpace fill:#F59E0B
    style DeleteFile fill:#EF4444
    style Archive fill:#10B981
```

---

## 6. Arquitectura Física de Red

```mermaid
graph TB
    subgraph "Servidor Central"
        Server[PC Linux<br/>Core i5, 16GB RAM]
        Server --- PG[PostgreSQL]
        Server --- Redis[Redis Cache]
        Server --- App[Node.js API]
        Server --- Storage[HDD 500GB<br/>Storage]
    end
    
    Server -->|Ethernet| Router[Router/Gateway<br/>192.168.1.1]
    
    Router -->|WiFi| AP1[Access Point #1<br/>Zona A - Aula 101]
    Router -->|WiFi| AP2[Access Point #2<br/>Zona B - Aula 102]
    Router -->|WiFi| AP3[Access Point #3<br/>Zona C - Biblioteca]
    
    AP1 -.->|WiFi| Client1[Laptops<br/>Estudiantes]
    AP1 -.->|WiFi| Client2[Tablets<br/>Estudiantes]
    
    AP2 -.->|WiFi| Client3[Laptops<br/>Teachers]
    
    AP3 -.->|WiFi| Client4[Dispositivos<br/>Biblioteca]
    
    subgraph "Backup (Opcional)"
        Backup[Disco Externo<br/>1TB USB]
    end
    
    Server -.->|USB| Backup
    
    style Server fill:#3B82F6
    style Router fill:#10B981
    style AP1 fill:#F59E0B
    style AP2 fill:#F59E0B
    style AP3 fill:#F59E0B
    style Backup fill:#6B7280
```

---

## 7. Pipeline CI/CD

```mermaid
flowchart LR
    A[Git Push] --> B{GitHub Actions}
    
    B --> C[Install Dependencies]
    C --> D[Lint Code]
    D --> E[Unit Tests]
    E --> F[Integration Tests]
    
    F --> G{Tests Pass?}
    
    G -->|No| H[Notify Developer<br/>❌ Build Failed]
    G -->|Sí| I[Build Docker Images]
    
    I --> J[Push to Registry]
    J --> K{Branch?}
    
    K -->|main| L[Deploy to Production<br/>Server Local]
    K -->|develop| M[Deploy to Staging]
    
    L --> N[Run E2E Tests]
    M --> O[Run E2E Tests]
    
    N --> P{E2E Pass?}
    O --> P
    
    P -->|No| Q[Rollback]
    P -->|Sí| R[✅ Deploy Success]
    
    style G fill:#F59E0B
    style P fill:#F59E0B
    style R fill:#10B981
    style H fill:#EF4444
    style Q fill:#EF4444
```

---

## 8. Diagrama de Estados del Contenido

```mermaid
stateDiagram-v2
    [*] --> Uploading: Teacher uploads file
    
    Uploading --> Processing: File saved in temp
    Processing --> Active: Transcode complete
    Processing --> Failed: Transcode error
    
    Active --> Archived: Manual archive by admin
    Active --> Evicted: Automatic eviction (LRU)
    
    Evicted --> Archived: Moved to cold storage
    Archived --> Active: Restore from archive
    
    Failed --> Processing: Retry upload
    Failed --> [*]: Delete failed upload
    
    Archived --> [*]: Permanent delete (after 30 days)
```

---

## 9. Threat Model (Seguridad)

```mermaid
graph TB
    subgraph "Threats"
        T1[Unauthorized Access]
        T2[SQL Injection]
        T3[XSS Attacks]
        T4[DoS Attacks]
        T5[Data Corruption]
    end
    
    subgraph "Mitigations"
        M1[JWT Authentication<br/>+ Role-Based Access]
        M2[Prepared Statements<br/>+ Input Validation]
        M3[Content Sanitization<br/>+ CSP Headers]
        M4[Rate Limiting<br/>+ Request Throttling]
        M5[File Hashing<br/>+ Automated Backups]
    end
    
    T1 -.->|mitigated by| M1
    T2 -.->|mitigated by| M2
    T3 -.->|mitigated by| M3
    T4 -.->|mitigated by| M4
    T5 -.->|mitigated by| M5
    
    style T1 fill:#EF4444
    style T2 fill:#EF4444
    style T3 fill:#EF4444
    style T4 fill:#EF4444
    style T5 fill:#EF4444
    
    style M1 fill:#10B981
    style M2 fill:#10B981
    style M3 fill:#10B981
    style M4 fill:#10B981
    style M5 fill:#10B981
```

---

## 10. Monitoreo y Observabilidad

```mermaid
graph LR
    subgraph "Sistema"
        API[API Server]
        DB[(Database)]
        Storage[Storage]
    end
    
    subgraph "Métricas"
        API --> M1[Request Rate<br/>Response Time]
        Database --> M2[Query Performance<br/>Connection Pool]
        Storage --> M3[Disk Usage<br/>I/O Throughput]
    end
    
    subgraph "Logs"
        API --> L1[Access Logs]
        API --> L2[Error Logs]
        Storage --> L3[Eviction Logs]
    end
    
    subgraph "Alertas"
        M3 --> A1{Disk > 80%?}
        M2 --> A2{Slow Queries?}
        L2 --> A3{Error Rate High?}
        
        A1 -->|Sí| Notify[Send Alert<br/>to Admin]
        A2 -->|Sí| Notify
        A3 -->|Sí| Notify
    end
    
    Notify --> Admin[Admin Dashboard<br/>Email/Slack]
    
    style Notify fill:#F59E0B
    style Admin fill:#3B82F6
```

---

Estos diagramas proporcionan una visualización completa de:
- ✅ Flujos de datos y procesos
- ✅ Arquitectura de componentes
- ✅ Modelo de datos
- ✅ Decisiones de diseño
- ✅ Consideraciones de seguridad
- ✅ Estrategias de monitoreo
