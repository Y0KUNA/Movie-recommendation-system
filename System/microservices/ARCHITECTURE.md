# Microservices Architecture - Chi tiết Kỹ thuật

## 📋 Tổng Quan Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                       CLIENT LAYER                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Web Browser (http://localhost:5000)                    │   │
│  │  - index.html / script.js / style.css                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTP/REST
                 ▼
         ┌───────────────────┐
         │   API GATEWAY     │
         │   (Port 5000)     │
         │                   │
         │ ✓ Route requests  │
         │ ✓ Serve web UI    │
         │ ✓ CORS handling   │
         │ ✓ Health checks   │
         └─────┬─────┬──────┬┘
               │     │      │
        ┌──────┘     │      └──────┐
        │            │             │
        ▼            ▼             ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  MOVIE   │ │  VECTOR  │ │ RECOMM.  │
   │ SERVICE  │ │ SERVICE  │ │ SERVICE  │
   │5001      │ │5003      │ │5002      │
   │          │ │          │ │          │
   │• Search  │ │• Embed.  │ │• Suggest │
   │• Filter  │ │• Sim.    │ │• Trend   │
   │• Detail  │ │• Batch   │ │• Personal│
   └────┬─────┘ └──────────┘ └────┬─────┘
        │                          │
        └──────────────┬───────────┘
                       ▼
             ┌──────────────────┐
             │   DATA LAYER     │
             │                  │
             │• imdb_movies.csv │
             │• movie_vectors   │
             │  .npz            │
             └──────────────────┘
```

## 🔌 Service Communication

### Communication Patterns

```
1. SYNCHRONOUS (HTTP/REST)
   ┌─────────────────────────────────────────┐
   │ Client → Gateway                        │
   │          → Movie Service                │
   │          → Vector Service               │
   │          → Recommendation Service       │
   │ ← Returns combined result               │
   └─────────────────────────────────────────┘

2. SERVICE-TO-SERVICE
   ┌─────────────────────────────────────────┐
   │ Recommendation Service                  │
   │    ↓                                    │
   │ Calls Movie Service API                 │
   │    ↓                                    │
   │ Calls Vector Service API                │
   │    ↓                                    │
   │ Combines & Returns                      │
   └─────────────────────────────────────────┘

3. SHARED CODE (common/)
   ┌─────────────────────────────────────────┐
   │ All Services Import:                    │
   │ - models.py (Data structures)           │
   │ - config.py (Configuration)             │
   │ - utils.py (Helper functions)           │
   └─────────────────────────────────────────┘
```

## 📐 Service Responsibilities

### API Gateway (Port 5000)
```python
RESPONSIBILITIES:
  ✓ Single entry point for all requests
  ✓ Route to appropriate microservice
  ✓ Serve web interface (HTML/CSS/JS)
  ✓ Add CORS headers
  ✓ Handle OPTIONS (preflight)
  ✓ Health check orchestration
  ✓ Error handling & logging

DEPENDENCIES:
  - Flask (HTTP server)
  - requests (HTTP client)
  - common module

KEY METHODS:
  - add_cors_headers() - CORS middleware
  - get_movies() - Proxy to Movie Service
  - get_movie_detail() - Proxy to Movie Service
  - get_similar() - Proxy to Recommendation Service
  - get_trending() - Proxy to Recommendation Service
  - get_personalized() - Proxy to Recommendation Service
  - check_all_services() - Health monitoring
```

### Movie Service (Port 5001)
```python
RESPONSIBILITIES:
  ✓ Load movie data from CSV
  ✓ Cache data in memory
  ✓ Search movies by multiple fields
  ✓ Filter & sort movies
  ✓ Return paginated results
  ✓ Provide movie details by ID

ARCHITECTURE:
  MovieRepository (Data Access Layer)
    ├─ load_movies() → Load from CSV
    ├─ get_all_movies() → Get cached data
    ├─ get_movie_by_id(id) → Direct lookup
    ├─ search_movies(query, field) → Search
    ├─ filter_by_genre(genre) → Filter
    ├─ filter_by_director(director) → Filter
    └─ sort_by_rating(movies) → Sort
  
  MovieService (Business Logic Layer)
    ├─ get_all_movies_paginated()
    ├─ search_movies_paginated()
    ├─ get_movie_detail()
    └─ get_recommendations_based_on_similarity()

DEPENDENCIES:
  - Flask (HTTP server)
  - csv (Data reading)
  - common module
```

### Vector Service (Port 5003)
```python
RESPONSIBILITIES:
  ✓ Load pre-computed embeddings (NPZ)
  ✓ Compute cosine similarity
  ✓ Find similar movies
  ✓ Handle batch operations

ARCHITECTURE:
  VectorRepository (Vector Data Access)
    ├─ load_vectors() → Load NPZ file
    ├─ get_movie_vector(id) → Get vector
    └─ get_vectors() → Get all vectors
  
  VectorService (Similarity Logic)
    ├─ compute_similarity(id1, id2)
    ├─ find_similar_movies(id, top_k)
    └─ batch_find_similar(ids, top_k)

DEPENDENCIES:
  - Flask (HTTP server)
  - numpy (Array operations)
  - scipy (Sparse matrices)
  - scikit-learn (Similarity)
  - requests (Service communication)
  - common module
```

### Recommendation Service (Port 5002)
```python
RESPONSIBILITIES:
  ✓ Orchestrate recommendations
  ✓ Call Movie & Vector Services
  ✓ Combine results intelligently
  ✓ Personalize recommendations

RECOMMENDATION METHODS:

  1. VECTOR-BASED (Similarity)
     → Calls Vector Service
     → Gets similar embeddings
     → Fetches movie details from Movie Service
     → Returns: [(movie, score), ...]

  2. GENRE-BASED
     → Calls Movie Service
     → Searches by genre
     → Sorts by rating
     → Returns: [movie, ...]

  3. HYBRID
     → Combines vector + genre
     → Removes duplicates
     → Merges results
     → Returns: [movie, ...]

  4. PERSONALIZED (Multi-preference)
     → Takes multiple liked movies
     → Gets similar for each
     → Aggregates scores
     → Returns top-k combined

ARCHITECTURE:
  RecommendationService
    ├─ get_similar_by_vector()
    ├─ get_similar_by_genre()
    ├─ get_personalized_recommendations()
    ├─ get_trending_recommendations()
    └─ get_recommendations_by_user_preference()

DEPENDENCIES:
  - Flask (HTTP server)
  - requests (Service communication)
  - common module
```

## 🔄 Request Flow Examples

### Example 1: Get Similar Movies
```
Client: GET /api/recommendations/similar?movie_id=tt0068646&top_k=10

Flow:
1. API Gateway (5000)
   └→ /api/recommendations/similar
      └→ calls Recommendation Service

2. Recommendation Service (5002)
   └→ get_similar_by_vector()
      ├→ calls Movie Service: /api/movies/tt0068646
      │  (Get movie details & metadata)
      │
      └→ calls Vector Service: /api/vectors/similar?movie_id=tt0068646
         (Compute similarity for top-k)

3. Vector Service (5003)
   └→ find_similar_movies()
      └→ Compute cosine similarity
         └→ Return [(id1, 0.95), (id2, 0.93), ...]

4. Recommendation Service (5002)
   └→ For each similar movie_id:
      └→ calls Movie Service: /api/movies/<id>
         └→ Get full movie details

5. Recommendation Service (5002)
   └→ Combine results with similarity scores

6. API Gateway (5000)
   └→ Format response
      └→ Return to client
```

### Example 2: Search & Paginate
```
Client: GET /api/movies?search=action&field=genre&page=1&per_page=20

Flow:
1. API Gateway (5000)
   └→ /api/movies?search=action&field=genre&...
      └→ calls Movie Service

2. Movie Service (5001)
   └→ search_movies_paginated()
      ├→ repository.search_movies("action", "genre")
      │  └→ Returns all matching movies
      │
      ├→ repository.sort_by_rating()
      │  └→ Sort by rating descending
      │
      ├→ Slice for pagination
      │  (start=0, end=20)
      │
      └→ Return paginated response with metadata

3. API Gateway (5000)
   └→ Return to client
```

### Example 3: Personalized Recommendations
```
Client: POST /api/recommendations/personalized
Body: {"liked_movies": ["tt0068646", "tt0071562"], "top_k": 10}

Flow:
1. API Gateway (5000)
   └→ /api/recommendations/personalized
      └→ calls Recommendation Service

2. Recommendation Service (5002)
   └→ get_recommendations_by_user_preference()
      │
      ├→ For each liked_movie:
      │  └→ calls Vector Service: /api/vectors/similar
      │     └→ Get similar movies & scores
      │
      ├→ Aggregate all recommendations
      │  └→ Sum similarity scores for duplicates
      │
      ├→ Sort by total score
      │  └→ Remove original liked movies
      │
      ├→ For each result:
      │  └→ calls Movie Service: /api/movies/<id>
      │     └→ Get full movie details
      │
      └→ Return top-k with highest scores

3. API Gateway (5000)
   └→ Return to client
```

## 🗄️ Data Models

### Movie Object
```python
@dataclass
class Movie:
    movie_id: str              # Unique IMDb ID
    movie_name: str            # Title
    year: Optional[str]        # Release year
    certificate: Optional[str] # Rating (PG, R, etc.)
    runtime: Optional[str]     # Minutes
    genre: Optional[str]       # Comma-separated genres
    rating: Optional[str]      # IMDb rating (0-10)
    description: Optional[str] # Plot summary
    director: Optional[str]    # Director name(s)
    director_id: Optional[str] # IMDb director ID(s)
    star: Optional[str]        # Actor name(s)
    star_id: Optional[str]     # IMDb actor ID(s)
    votes: Optional[str]       # Number of votes
    gross: Optional[str]       # Box office in $
    poster: Optional[str]      # Poster URL

    Methods:
      - to_dict() → Convert to JSON-serializable dict
```

### PaginatedResponse Object
```python
@dataclass
class PaginatedResponse:
    data: List[dict]           # List of items
    total: int                 # Total items in DB
    page: int                  # Current page
    per_page: int              # Items per page
    total_pages: int           # Total pages

    Methods:
      - to_dict() → Convert to JSON-serializable dict
```

## ⚙️ Configuration Management

### Config Hierarchy
```python
Config (Base)
├── DevelopmentConfig (debug=True)
└── ProductionConfig (debug=False)

Environment Variables:
  - FLASK_ENV (development|production)
  - DEBUG (True|False)
  - MOVIE_SERVICE_PORT (5001)
  - RECOMMENDATION_SERVICE_PORT (5002)
  - VECTOR_SERVICE_PORT (5003)
  - GATEWAY_PORT (5000)
  - MOVIE_SERVICE_URL (http://...)
  - RECOMMENDATION_SERVICE_URL (http://...)
  - VECTOR_SERVICE_URL (http://...)
  - MOVIES_CSV (path)
  - MOVIE_VECTORS_NPZ (path)
```

## 🧩 Shared Utilities (common/)

### models.py
```python
- Movie dataclass
- PaginatedResponse dataclass
- JSON serialization methods
```

### config.py
```python
- Config class (base)
- DevelopmentConfig
- ProductionConfig
- get_config(env) function
```

### utils.py
```python
- ServiceClient class (HTTP requests)
  - get() method
  - post() method
  - Error handling

- Utility functions:
  - clean_field(value) → Clean CSV fields
  - parse_rating(rating) → Convert to float
  - calculate_total_pages() → Calculate pagination
```

## 🚀 Deployment Architecture

### Local Development
```
Docker Desktop
└── docker-compose (4 containers)
    ├── movie-service:5001
    ├── vector-service:5003
    ├── recommendation-service:5002
    └── api-gateway:5000
```

### Production (Future)
```
Kubernetes Cluster
├── Ingress (Load Balancer)
├── API Gateway Pod (replicas: 3)
├── Movie Service Pod (replicas: 2)
├── Recommendation Service Pod (replicas: 1)
├── Vector Service Pod (replicas: 2)
├── PostgreSQL StatefulSet
├── Redis Cache
├── RabbitMQ Message Queue
└── ELK Stack (Logging)
```

## 📊 Performance Considerations

### Movie Service
```
✓ In-memory caching: Load CSV once, keep in memory
✓ Dictionary lookup: O(1) access by ID
✓ Pagination: Only return needed records
```

### Vector Service
```
✓ Load NPZ once: Load vectors on startup
✓ Cosine similarity: O(n) for top-k
✓ Sparse matrices: Memory efficient
✓ Batch operations: Process multiple at once
```

### Recommendation Service
```
✓ Service orchestration: Call services as needed
✓ Result caching: Cache similar results
✓ Aggregation: Efficient scoring combination
```

## 🔐 Future Security Enhancements

```
1. Authentication
   - JWT tokens
   - API keys

2. Authorization
   - Role-based access control (RBAC)
   - Permission checking

3. Rate Limiting
   - Per-user limits
   - Per-IP limits

4. Input Validation
   - Schema validation
   - SQL injection prevention

5. HTTPS/TLS
   - Encrypted communication
   - SSL certificates
```

---

**Kiến trúc được thiết kế để:**
- ✅ Scale độc lập
- ✅ Deploy dễ dàng
- ✅ Maintain lâu dài
- ✅ Test toàn diện
- ✅ Mở rộng sau này
