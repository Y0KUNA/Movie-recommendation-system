# 🎬 Recommendation System - Tái Cấu Trúc Microservices

## ✅ Những gì đã hoàn thành

Dự án của bạn đã được **tái cấu trúc từ monolith sang Microservices Architecture** với các đặc điểm sau:

### 📦 Cấu Trúc Mới

```
microservices/
├── api-gateway/              ← Entry point (Port 5000)
├── movie-service/            ← Quản lý phim (Port 5001)
├── recommendation-service/   ← Gợi ý phim (Port 5002)
├── vector-service/           ← Xử lý embeddings (Port 5003)
├── common/                   ← Shared code (models, config, utils)
├── tests/                    ← Unit & integration tests
├── docker-compose.yml        ← Orchestration
├── README.md                 ← Chi tiết API docs
└── SETUP.md                  ← Hướng dẫn setup
```

## 🏗️ 4 Microservices

### 1. **API Gateway** (Port 5000) - Cổng vào
- ✅ Điều hướng request tới các service
- ✅ Serve web interface (templates + static files)
- ✅ Xử lý CORS headers
- ✅ Health check tất cả services
- ✅ Entry point duy nhất cho client

### 2. **Movie Service** (Port 5001) - Quản lý dữ liệu
- ✅ Load & cache dữ liệu từ CSV
- ✅ Tìm kiếm phim (name, genre, director, etc.)
- ✅ Lấy chi tiết phim
- ✅ Lọc phim theo category
- ✅ Repository pattern cho data access

### 3. **Recommendation Service** (Port 5002) - Gợi ý thông minh
- ✅ Gợi ý dựa trên vector similarity
- ✅ Gợi ý dựa trên genre
- ✅ Hybrid recommendations
- ✅ Personalized dựa trên multiple preferences
- ✅ Trending movies

### 4. **Vector Service** (Port 5003) - Xử lý embeddings
- ✅ Load pre-computed vectors từ NPZ
- ✅ Tính cosine similarity
- ✅ Tìm phim tương tự
- ✅ Batch similarity operations
- ✅ Efficient vector computations

## 🚀 Cách Chạy

### Option 1: Docker Compose (Easiest)
```powershell
cd microservices
docker-compose up --build
# Access: http://localhost:5000
```

### Option 2: Batch Script
```powershell
cd microservices
.\run_all_services.bat
```

### Option 3: Manual
```powershell
# Terminal 1
cd microservices\movie-service
python app.py

# Terminal 2
cd microservices\vector-service
python app.py

# Terminal 3
cd microservices\recommendation-service
python app.py

# Terminal 4
cd microservices\api-gateway
python app.py
```

## 📡 API Routes

### 🔗 Qua Gateway (http://localhost:5000)

#### Phim
```
GET /api/movies                           # Danh sách phim
GET /api/movies?search=avengers           # Tìm kiếm
GET /api/movies/<id>                      # Chi tiết
GET /api/movies/search/by-genre           # Filter genre
```

#### Gợi ý
```
GET /api/recommendations/similar          # Phim tương tự
GET /api/recommendations/trending         # Phim hot
POST /api/recommendations/personalized    # Gợi ý cá nhân
```

#### Health
```
GET /health                               # Gateway status
GET /health/services                      # Tất cả services status
```

## 📝 Ví dụ Request

### Lấy danh sách phim
```bash
curl "http://localhost:5000/api/movies?page=1&per_page=20"
```

### Tìm phim tương tự
```bash
curl "http://localhost:5000/api/recommendations/similar?movie_id=tt0068646&method=vector&top_k=10"
```

### Gợi ý cá nhân
```bash
curl -X POST http://localhost:5000/api/recommendations/personalized \
  -H "Content-Type: application/json" \
  -d '{"liked_movies": ["tt0068646", "tt0071562"], "top_k": 10}'
```

### Check sức khỏe
```bash
curl http://localhost:5000/health/services
```

## 🎯 Lợi ích Microservices

| Lợi ích | Chi tiết |
|---------|---------|
| **Scalability** | Scale từng service độc lập theo nhu cầu |
| **Maintainability** | Code tách biệt, dễ bảo trì |
| **Flexibility** | Dễ thêm/sửa/xóa features |
| **Resilience** | Failure không lan rộng |
| **Testing** | Test từng service riêng lẻ |
| **Deployment** | Deploy nhanh, an toàn hơn |
| **Technology** | Dùng tech khác nhau cho mỗi service |

## 📂 Shared Code (Common)

```python
# models.py - Data structures
- Movie
- PaginatedResponse

# config.py - Configuration
- DevelopmentConfig
- ProductionConfig
- Service ports & URLs

# utils.py - Helper functions
- ServiceClient (HTTP inter-service calls)
- clean_field()
- parse_rating()
- calculate_total_pages()
```

## 🔄 Data Flow

```
Browser Request
    ↓
API Gateway (5000)
    ↓
Route to appropriate service
    ├→ Movie Service (5001) - Get data
    ├→ Vector Service (5003) - Compute similarity
    └→ Recommendation Service (5002) - Generate recommendations
    ↓
Combine results
    ↓
Return to Browser
```

## 🧪 Testing

```powershell
# Install pytest
pip install pytest

# Run unit tests
pytest microservices/tests/test_common.py -v

# Run integration tests (needs all services running)
pytest microservices/tests/test_integration.py -v
```

## 🐳 Docker Support

Mỗi service có Dockerfile riêng:
- Optimized image size
- Fast startup time
- Isolated dependencies

## 🌱 Next Steps (Recommendations)

1. **Database**: Thay CSV bằng PostgreSQL/MongoDB
   ```python
   # Store movie data in DB instead of CSV
   # Add ORM (SQLAlchemy) untuk easier queries
   ```

2. **Caching**: Add Redis
   ```python
   # Cache popular searches & recommendations
   # Reduce response time significantly
   ```

3. **Message Queue**: Add RabbitMQ
   ```python
   # Async processing for heavy computations
   # Decouple services further
   ```

4. **API Documentation**: Swagger/OpenAPI
   ```python
   # Auto-generated API docs
   # Easy for client integration
   ```

5. **Monitoring**: Prometheus + Grafana
   ```python
   # Real-time metrics & monitoring
   # Alerts for service failures
   ```

6. **Load Balancer**: Nginx
   ```python
   # Distribute traffic
   # High availability
   ```

7. **Kubernetes**: Container orchestration
   ```yaml
   # Production-ready deployment
   # Auto-scaling & self-healing
   ```

## 📚 Documentation Files

- **MICROSERVICES_GUIDE.md** - Complete overview (IN PROJECT ROOT)
- **microservices/README.md** - Detailed API documentation
- **microservices/SETUP.md** - Setup instructions
- Inline code documentation in each file

## ✨ Enhancements Made

✅ **Separation of Concerns** - Each service has single responsibility
✅ **Scalability** - Independent scaling per service
✅ **Code Organization** - Clear structure, easy navigation
✅ **Reusability** - Shared common code
✅ **Testing** - Test suite included
✅ **Docker Ready** - Containerization support
✅ **Configuration** - Centralized config management
✅ **Documentation** - Comprehensive docs & examples
✅ **Health Checks** - Monitor service status
✅ **Error Handling** - Proper error responses

---

**🎉 Dự án đã sẵn sàng để phát triển theo kiến trúc Microservices!**

Để bắt đầu: `cd microservices && docker-compose up --build`
