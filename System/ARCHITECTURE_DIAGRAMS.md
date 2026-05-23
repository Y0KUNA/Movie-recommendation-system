# 📊 VISUAL ARCHITECTURE DIAGRAMS

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                         CLIENT LAYER                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Web Browser                                             │   │
│  │  • HTML/CSS/JavaScript                                   │   │
│  │  • RESTful API calls                                     │   │
│  │  • Real-time interactions                                │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │ HTTP/REST
                              │ JSON
                              ▼
            ┌──────────────────────────────────┐
            │                                  │
            │      API GATEWAY (5000)          │
            │      ├─ Request Router           │
            │      ├─ Static File Server       │
            │      ├─ CORS Middleware          │
            │      ├─ Health Aggregator        │
            │      └─ Error Formatter          │
            │                                  │
            └───┬──────────────┬──────────┬────┘
                │              │          │
        ┌───────┴──┐   ┌──────┴────┐  ┌──┴──────┐
        │           │   │           │  │         │
        ▼           ▼   ▼           ▼  ▼         ▼
    ┌────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐
    │ MOVIE  │ │ VECTOR │ │RECOMMEND.│ │ HEALTH  │
    │SERVICE │ │SERVICE │ │ SERVICE  │ │ CHECK   │
    │(5001)  │ │(5003)  │ │  (5002)  │ │         │
    └────┬───┘ └────┬───┘ └────┬─────┘ └─────────┘
         │          │          │
         │          │          └────────────┐
         │          │                       │
         │          └───────────┐           │
         │                      │           │
         ▼                      ▼           ▼
    ┌──────────┐       ┌────────────┐  ┌──────────┐
    │  LOAD    │       │   LOAD     │  │  CALL    │
    │   CSV   │       │    NPZ     │  │ SERVICES │
    │  & CACHE │       │  & CACHE   │  │ & MERGE  │
    └──────────┘       └────────────┘  └──────────┘
         │                   │
         ▼                   ▼
    ┌──────────────────────────────┐
    │   DATA LAYER                 │
    │                              │
    │ • imdb_movies_3000.csv       │
    │ • movie_vectors.npz          │
    │ • Pre-computed embeddings    │
    │ • Movie metadata             │
    └──────────────────────────────┘
```

## 2. Service Communication Flow

```
┌─────────────────────────────────────────────────────────┐
│                 CLIENT REQUEST                         │
│              GET /recommendations                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   API GATEWAY (5000)   │
        │                        │
        │ 1. Parse request       │
        │ 2. Route decision      │
        └────────┬───────────────┘
                 │
                 ▼
        ┌─────────────────────────────┐
        │ RECOMMENDATION SERVICE      │
        │ (5002)                      │
        │                             │
        │ get_personalized_recs()     │
        └────────┬────────┬───────────┘
                 │        │
        ┌────────┘        └────────┐
        │                          │
        ▼                          ▼
    ┌──────────────┐        ┌──────────────┐
    │   VECTOR     │        │    MOVIE     │
    │   SERVICE    │        │   SERVICE    │
    │   (5003)     │        │   (5001)     │
    │              │        │              │
    │ find_similar │        │ get_movie_   │
    │_movies()     │        │ detail()     │
    │              │        │              │
    └──────┬───────┘        └──────┬───────┘
           │                       │
           │ Returns:              │ Returns:
           │ [(id, score),...]     │ {movie_data}
           │                       │
           └───────────┬───────────┘
                       │
                       ▼
        ┌─────────────────────────────┐
        │ RECOMMENDATION SERVICE      │
        │                             │
        │ Aggregate & rank results    │
        │ Combine movie data + scores │
        │                             │
        └────────┬────────────────────┘
                 │
                 ▼
        ┌─────────────────────────┐
        │   API GATEWAY (5000)    │
        │                         │
        │ Format response         │
        │ Add CORS headers        │
        └────────┬────────────────┘
                 │
                 ▼
        ┌─────────────────────────┐
        │   CLIENT RESPONSE       │
        │   JSON with results     │
        └─────────────────────────┘
```

## 3. Service Responsibility Matrix

```
┌────────────────────────────────────────────────────────────────┐
│                    SERVICE RESPONSIBILITY                      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  API GATEWAY (5000)                                            │
│  ├─ Route incoming requests                                    │
│  ├─ Serve web interface (HTML/CSS/JS)                          │
│  ├─ Add CORS headers & security                                │
│  ├─ Check service health                                       │
│  └─ Format responses & errors                                  │
│                                                                │
│  ─────────────────────────────────────────────────────────    │
│                                                                │
│  MOVIE SERVICE (5001)                                          │
│  ├─ Load movies from CSV                                       │
│  ├─ Cache movies in memory                                     │
│  ├─ Search by movie_name, genre, director, etc.               │
│  ├─ Filter & sort movies                                       │
│  ├─ Return paginated results                                   │
│  └─ Provide movie details by ID                                │
│                                                                │
│  ─────────────────────────────────────────────────────────    │
│                                                                │
│  VECTOR SERVICE (5003)                                         │
│  ├─ Load embeddings from NPZ file                              │
│  ├─ Cache vectors in memory                                    │
│  ├─ Compute cosine similarity                                  │
│  ├─ Find top-k similar movies                                  │
│  ├─ Support batch operations                                   │
│  └─ Optimize for speed                                         │
│                                                                │
│  ─────────────────────────────────────────────────────────    │
│                                                                │
│  RECOMMENDATION SERVICE (5002)                                 │
│  ├─ Orchestrate recommendations                                │
│  ├─ Call Movie Service for data                                │
│  ├─ Call Vector Service for similarity                         │
│  ├─ Implement multiple algorithms:                             │
│  │  ├─ Vector-based (ML)                                       │
│  │  ├─ Genre-based (content)                                   │
│  │  └─ Hybrid (combined)                                       │
│  ├─ Personalize for users                                      │
│  ├─ Return trending movies                                     │
│  └─ Aggregate & rank results                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 4. Data Flow Architecture

```
DATA SOURCES
    │
    ├─ CSV File                NPZ File
    │  (imdb_movies_3000.csv)  (movie_vectors.npz)
    │
    ├──────┬────────────────────────┬──────────┐
    │      │                        │          │
    ▼      ▼                        ▼          ▼
    │      │                        │          │
┌───────────────────┐    ┌──────────────────────┐
│  MOVIE SERVICE    │    │  VECTOR SERVICE      │
├───────────────────┤    ├──────────────────────┤
│ 1. Load CSV       │    │ 1. Load NPZ          │
│ 2. Parse rows     │    │ 2. Load vectors      │
│ 3. Clean data     │    │ 3. Convert sparse    │
│ 4. Cache in dict  │    │ 4. Create index      │
│ 5. Create index   │    │ 5. Cache in memory   │
│    by movie_id    │    │                      │
└────────┬──────────┘    └──────────┬───────────┘
         │                          │
         │ Provides:                │ Provides:
         │ - Movie data             │ - Vector data
         │ - Search results         │ - Similarity scores
         │ - Filtered lists         │ - Top-k similar
         │ - Paginated results      │ - Batch results
         │                          │
         └────────┬─────────────────┘
                  │
                  ▼
        ┌─────────────────────────┐
        │RECOMMENDATION SERVICE   │
        ├─────────────────────────┤
        │ Combines data:          │
        │ 1. Gets similar IDs     │
        │ 2. Gets movie details   │
        │ 3. Merges results       │
        │ 4. Ranks by score       │
        │ 5. Returns top-k        │
        └────────┬────────────────┘
                 │
                 ▼
        ┌─────────────────────────┐
        │    RESPONSE TO CLIENT   │
        │ {                       │
        │   movie_id,             │
        │   movie_name,           │
        │   similarity_score,     │
        │   ... metadata          │
        │ }[]                     │
        └─────────────────────────┘
```

## 5. Deployment Architecture

```
DEVELOPMENT (Local)
────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────┐
│                    Docker Desktop                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ Container 1 │  │ Container 2 │  │ Container 3 │   │
│  │  Gateway    │  │   Movie     │  │   Vector    │   │
│  │  :5000      │  │   Service   │  │   Service   │   │
│  │             │  │   :5001     │  │   :5003     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                        │
│  ┌────────────────────────────────┐                   │
│  │      Container 4               │                   │
│  │   Recommendation Service       │                   │
│  │        :5002                   │                   │
│  └────────────────────────────────┘                   │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │       Shared Network: microservices-network    │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
└────────────────────────────────────────────────────────┘


FUTURE - PRODUCTION (Kubernetes)
────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────┐
│                 Kubernetes Cluster                     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌────────────────────────────────────┐               │
│  │          Ingress (LoadBalancer)    │               │
│  │         api.example.com :80/443    │               │
│  └────────────┬───────────────────────┘               │
│               │                                        │
│    ┌──────────┴─────────────┬──────────────┐           │
│    │                        │              │           │
│    ▼                        ▼              ▼           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ API Gateway  │  │ Movie Service│  │ Vector Svc   │ │
│  │ Replicas: 3  │  │ Replicas: 2  │  │ Replicas: 2  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌────────────────────────────────┐                   │
│  │ Recommendation Service         │                   │
│  │ Replicas: 1                    │                   │
│  └────────────────────────────────┘                   │
│                                                        │
│  ┌────────────────────────────────┐                   │
│  │ PostgreSQL StatefulSet         │                   │
│  └────────────────────────────────┘                   │
│  ┌────────────────────────────────┐                   │
│  │ Redis Cache                    │                   │
│  └────────────────────────────────┘                   │
│  ┌────────────────────────────────┐                   │
│  │ RabbitMQ Message Queue         │                   │
│  └────────────────────────────────┘                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## 6. Request Processing Pipeline

```
REQUEST LIFECYCLE
──────────────────────────────────────────────────────────

1. CLIENT
   ├─ Browser sends HTTP request
   └─ Example: GET /api/recommendations/similar?movie_id=tt0068646

2. GATEWAY (5000)
   ├─ Receive request
   ├─ Check CORS
   ├─ Parse parameters
   ├─ Validate input
   ├─ Determine routing
   └─ Forward to service

3. SERVICE (5002 - Recommendation)
   ├─ Receive request from Gateway
   ├─ Validate parameters
   ├─ Call Vector Service (5003)
   │  ├─ POST /api/vectors/similar?movie_id=...
   │  └─ Receive: [(id1, 0.95), (id2, 0.93), ...]
   │
   ├─ Call Movie Service (5001) for each result
   │  ├─ GET /api/movies/id1
   │  ├─ GET /api/movies/id2
   │  └─ Receive: [movie_data1, movie_data2, ...]
   │
   ├─ Merge results
   │  ├─ Combine movie data with scores
   │  └─ Rank by relevance
   │
   └─ Return JSON response to Gateway

4. GATEWAY (5000)
   ├─ Receive response from service
   ├─ Add CORS headers
   ├─ Format response
   └─ Send to client

5. CLIENT
   ├─ Receive JSON
   ├─ Parse response
   ├─ Render results
   └─ Display to user
```

## 7. Code Organization Layers

```
┌─────────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Web UI (HTML/CSS/JavaScript)                     │  │
│  │  ├─ index.html (UI structure)                     │  │
│  │  ├─ style.css (styling)                           │  │
│  │  └─ script.js (interactions & API calls)          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    API LAYER                            │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────┐  │
│  │ Gateway Routes │ │ Service Routes │ │ Endpoints  │  │
│  └────────────────┘ └────────────────┘ └────────────┘  │
│     (app.py in each service)                            │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER                       │
│  ┌─────────────────┐ ┌──────────────┐ ┌────────────┐   │
│  │MovieService     │ │VectorService │ │Recommend.. │   │
│  │- search         │ │- similarity  │ │Service     │   │
│  │- filter         │ │- find_similar│ │- orchestrate    │
│  │- sort           │ │- batch       │ │  recommendations │
│  └─────────────────┘ └──────────────┘ └────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              REPOSITORY/DATA LAYER                      │
│  ┌──────────────────┐ ┌─────────────────┐              │
│  │MovieRepository   │ │VectorRepository │              │
│  │- load_movies()   │ │- load_vectors() │              │
│  │- cache           │ │- cache          │              │
│  │- query           │ │- query          │              │
│  └──────────────────┘ └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              SHARED UTILITIES                           │
│  ┌──────────┐ ┌────────┐ ┌────────────┐                │
│  │ models.py│ │config.py│ │utils.py    │               │
│  │- Movie   │ │- Config │ │- ServiceClient│            │
│  │- Response│ │- getenv │ │- helpers   │               │
│  └──────────┘ └────────┘ └────────────┘                │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              DATA STORAGE LAYER                         │
│  ┌──────────────────┐ ┌────────────────┐               │
│  │ CSV Files        │ │ NPZ Vectors    │               │
│  │- Movies metadata │ │- Embeddings    │               │
│  │- Movie details   │ │- Pre-computed  │               │
│  └──────────────────┘ └────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## 8. Component Dependency Graph

```
┌─────────────────────────────────────────────────────────┐
│                    API GATEWAY                          │
│ ├─ depends on: Flask, requests, common                 │
│ └─ calls: Movie Service, Vector Service,               │
│           Recommendation Service                       │
└───────────┬──────────────────────────────────────────────┘
            │
            ├─────────────────────┬──────────────┐
            │                     │              │
            ▼                     ▼              ▼
    ┌────────────────┐   ┌─────────────────┐  ┌───────────┐
    │ MOVIE SERVICE  │   │ VECTOR SERVICE  │  │RECOMMEND. │
    │                │   │                 │  │ SERVICE   │
    │ depends on:    │   │ depends on:     │  │           │
    │- Flask         │   │- Flask          │  │ depends   │
    │- csv           │   │- requests       │  │ on:       │
    │- common        │   │- numpy          │  │- Flask    │
    │- requests      │   │- scipy          │  │- requests │
    │                │   │- scikit-learn   │  │- common   │
    │ calls:         │   │- common         │  │           │
    │- none          │   │                 │  │ calls:    │
    │                │   │ calls:          │  │- Movie    │
    └─────┬──────────┘   │- none           │  │  Service  │
          │              │                 │  │- Vector   │
          │              └────────┬─────────┘  │  Service  │
          │                       │            │           │
          │                       │            └─────┬─────┘
          │                       │                  │
          └───────────────────────┼──────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────┐
                    │   COMMON UTILITIES   │
                    │                      │
                    │- models.py           │
                    │- config.py           │
                    │- utils.py            │
                    │  ├─ ServiceClient    │
                    │  ├─ clean_field()    │
                    │  ├─ parse_rating()   │
                    │  └─ etc              │
                    └──────────────────────┘
```

---

**All diagrams show the interconnected microservices architecture with clear data flows and responsibilities.**
