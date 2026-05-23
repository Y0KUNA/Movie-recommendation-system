# Recommendation System - Microservices Architecture

## 📁 Project Structure

```
Recommend-system/
├── microservices/                        # ← NEW MICROSERVICES ARCHITECTURE
│   ├── api-gateway/
│   │   ├── app.py                        # Gateway Flask app (Port 5000)
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── movie-service/
│   │   ├── app.py                        # Movie Service Flask app (Port 5001)
│   │   ├── movie_service.py              # Movie business logic
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── recommendation-service/
│   │   ├── app.py                        # Recommendation Flask app (Port 5002)
│   │   ├── recommendation_service.py     # Recommendation logic
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── vector-service/
│   │   ├── app.py                        # Vector Flask app (Port 5003)
│   │   ├── vector_service.py             # Vector operations
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── common/
│   │   ├── models.py                     # Shared data models
│   │   ├── config.py                     # Configuration management
│   │   ├── utils.py                      # Shared utilities
│   │   └── __init__.py
│   │
│   ├── tests/
│   │   ├── test_common.py                # Common utils tests
│   │   ├── test_integration.py           # Integration tests
│   │   ├── conftest.py                   # Pytest configuration
│   │   └── __init__.py
│   │
│   ├── docker-compose.yml                # Docker orchestration
│   ├── README.md                         # Detailed documentation
│   ├── SETUP.md                          # Setup guide
│   ├── run_all_services.bat              # Windows startup script
│   ├── run_all_services.sh               # Linux/Mac startup script
│   └── ARCHITECTURE.md
│
├── web/                                  # ← Original web folder (unchanged)
│   ├── app.py
│   ├── vector.py
│   ├── templates/
│   ├── static/
│   ├── imdb_movies_3000.csv
│   └── movie_vectors.npz
│
└── [Other original files...]
```

## 🎯 Architecture Overview

### Kiến trúc Microservices

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │   API Gateway      │  (Port 5000)
        │  - Router          │
        │  - Static files    │
        │  - CORS handler    │
        └─┬─────┬────────┬───┘
          │     │        │
    ┌─────▼──┬──▼──┬────▼──────┐
    │         │     │           │
    ▼         ▼     ▼           ▼
┌─────────┐ ┌──────────┐ ┌──────────────┐
│  Movie  │ │Recommend │ │   Vector     │
│Service  │ │Service   │ │   Service    │
│Port5001 │ │Port 5002 │ │   Port 5003  │
└────┬────┘ └──────────┘ └──────────────┘
     │
     ▼
┌──────────────┐
│ CSV Data File│
│  + NPZ       │
│  Vectors     │
└──────────────┘
```

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```powershell
cd microservices
docker-compose up --build
```

### Using Batch Script (Windows)
```powershell
cd microservices
.\run_all_services.bat
```

### Manual Setup
```powershell
# Service 1
cd microservices\movie-service
pip install -r requirements.txt
python app.py

# Service 2 (new terminal)
cd microservices\vector-service
pip install -r requirements.txt
python app.py

# Service 3 (new terminal)
cd microservices\recommendation-service
pip install -r requirements.txt
python app.py

# Service 4 (new terminal)
cd microservices\api-gateway
pip install -r requirements.txt
python app.py
```

## 📡 API Endpoints

### Gateway (Main Entry Point)
- `GET http://localhost:5000/` - Web interface
- `GET http://localhost:5000/health` - Health check
- `GET http://localhost:5000/health/services` - All services status

### Movie Endpoints
- `GET /api/movies` - List with pagination
- `GET /api/movies/<id>` - Movie detail
- `GET /api/movies/search/by-genre?genre=...` - Filter by genre

### Recommendation Endpoints
- `GET /api/recommendations/similar?movie_id=...` - Similar movies
- `GET /api/recommendations/trending` - Top rated
- `POST /api/recommendations/personalized` - User preferences

### Vector Endpoints
- `GET /api/vectors/similar?movie_id=...` - Vector similarity
- `GET /api/vectors/similarity?movie_id1=...&movie_id2=...` - Compare two

## 🔧 Service Responsibilities

| Service | Port | Role |
|---------|------|------|
| API Gateway | 5000 | Entry point, routing, static files |
| Movie Service | 5001 | Data management, search, filtering |
| Recommendation Service | 5002 | Recommendation logic, personalization |
| Vector Service | 5003 | Embeddings, similarity computation |

## ✨ Benefits

✅ **Scalability** - Scale services independently
✅ **Maintainability** - Clear separation of concerns
✅ **Flexibility** - Easy to modify/add features
✅ **Resilience** - Isolated failures
✅ **Testing** - Unit test each service
✅ **Deployment** - Faster CI/CD pipeline
✅ **Technology** - Mix and match tech stacks

## 📝 Configuration

Environment variables in `common/config.py`:
```python
MOVIE_SERVICE_PORT = 5001
RECOMMENDATION_SERVICE_PORT = 5002
VECTOR_SERVICE_PORT = 5003
GATEWAY_PORT = 5000
MOVIE_SERVICE_URL = 'http://localhost:5001'
# ... etc
```

## 🧪 Testing

```bash
# Common utilities tests
pytest tests/test_common.py -v

# Integration tests (requires all services running)
pytest tests/test_integration.py -v

# All tests
pytest tests/ -v
```

## 📚 Documentation

- `microservices/README.md` - Detailed API & architecture docs
- `microservices/SETUP.md` - Setup instructions
- Each service has inline code documentation

## 🐳 Docker & Container

Each service has its own Dockerfile optimized for:
- Minimal image size
- Fast startup
- Dependency isolation

Orchestrated via `docker-compose.yml` for easy management.

## 🔄 Data Flow Example

```
Client Request
    ↓
API Gateway (Route)
    ↓
Movie Service (Fetch data)
    ↓
Vector Service (Compute similarity)
    ↓
Recommendation Service (Combine & rank)
    ↓
API Gateway (Format response)
    ↓
Client Response
```

## 🚧 Future Enhancements

- [ ] Database (PostgreSQL/MongoDB)
- [ ] Redis caching layer
- [ ] Message queue (RabbitMQ)
- [ ] Swagger/OpenAPI docs
- [ ] ELK Stack logging
- [ ] Prometheus metrics
- [ ] Kubernetes deployment
- [ ] Load balancing
- [ ] Authentication/Authorization
- [ ] Rate limiting

## 📞 Support

For issues or questions:
1. Check logs in each service terminal
2. Verify all services are running: `curl http://localhost:5000/health/services`
3. Check data files exist in `web/` folder
4. Review service-specific README files
