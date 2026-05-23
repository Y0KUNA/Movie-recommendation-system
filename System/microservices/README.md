# Microservices Architecture Documentation

## Cấu trúc dự án

```
microservices/
├── api-gateway/                 # Entry point - Port 5000
│   ├── app.py                   # Flask Gateway
│   ├── requirements.txt
│   └── Dockerfile
├── movie-service/               # Quản lý dữ liệu phim - Port 5001
│   ├── app.py
│   ├── movie_service.py
│   ├── requirements.txt
│   └── Dockerfile
├── recommendation-service/      # Gợi ý phim - Port 5002
│   ├── app.py
│   ├── recommendation_service.py
│   ├── requirements.txt
│   └── Dockerfile
├── vector-service/              # Xử lý embeddings - Port 5003
│   ├── app.py
│   ├── vector_service.py
│   ├── requirements.txt
│   └── Dockerfile
├── common/                       # Shared utilities
│   ├── models.py                # Data models
│   ├── config.py                # Configuration
│   └── utils.py                 # Helper functions
├── docker-compose.yml           # Orchestration
└── README.md
```

## Các Microservices

### 1. API Gateway (Port 5000)
**Trách nhiệm:**
- Entry point cho client
- Điều hướng request tới các service
- Xử lý CORS headers
- Serve static files và templates
- Health check tất cả services

**Endpoints:**
- `GET /` - Trang chủ
- `GET /health` - Health check gateway
- `GET /health/services` - Health check tất cả services
- `GET /api/movies` - Lấy danh sách phim
- `GET /api/movies/<id>` - Chi tiết phim
- `GET /api/recommendations/similar` - Phim tương tự
- `GET /api/recommendations/trending` - Phim hot
- `POST /api/recommendations/personalized` - Gợi ý cá nhân

### 2. Movie Service (Port 5001)
**Trách nhiệm:**
- Đọc và cache dữ liệu phim từ CSV
- Tìm kiếm phim theo criteria
- Lấy thông tin chi tiết phim
- Lọc phim theo genre, director, etc.

**Endpoints:**
- `GET /api/movies` - Paginated movies
- `GET /api/movies/<id>` - Movie detail
- `GET /api/movies/<id>/similar` - Similar movies
- `GET /api/movies/search/by-genre` - Search by genre

### 3. Vector Service (Port 5003)
**Trách nhiệm:**
- Load vector embeddings từ movie_vectors.npz
- Tính toán cosine similarity giữa phim
- Tìm phim tương tự dựa trên vector

**Endpoints:**
- `GET /api/vectors/similar` - Similar movies by vector
- `GET /api/vectors/similarity` - Similarity score
- `POST /api/vectors/batch-similar` - Batch similarity

### 4. Recommendation Service (Port 5002)
**Trách nhiệm:**
- Gợi ý phim dựa trên vector similarity
- Gợi ý dựa trên genre
- Gợi ý hybrid
- Gợi ý cá nhân dựa trên multiple liked movies

**Endpoints:**
- `GET /api/recommendations/similar` - Similar movies
- `GET /api/recommendations/trending` - Trending movies
- `POST /api/recommendations/personalized` - Personalized recommendations

## Chạy ứng dụng

### Cách 1: Sử dụng Docker Compose (Recommended)

```bash
cd microservices
docker-compose up --build
```

Services sẽ khởi động tại:
- API Gateway: http://localhost:5000
- Movie Service: http://localhost:5001
- Recommendation Service: http://localhost:5002
- Vector Service: http://localhost:5003

### Cách 2: Chạy từng service riêng

Trong PowerShell, chạy các commands sau ở các terminal khác nhau:

```powershell
# Terminal 1 - Movie Service
cd microservices\movie-service
pip install -r requirements.txt
python app.py

# Terminal 2 - Vector Service
cd microservices\vector-service
pip install -r requirements.txt
python app.py

# Terminal 3 - Recommendation Service
cd microservices\recommendation-service
pip install -r requirements.txt
python app.py

# Terminal 4 - API Gateway
cd microservices\api-gateway
pip install -r requirements.txt
python app.py
```

## Environment Variables

Có thể set các env vars để config:

```env
FLASK_ENV=development
DEBUG=True
MOVIE_SERVICE_PORT=5001
RECOMMENDATION_SERVICE_PORT=5002
VECTOR_SERVICE_PORT=5003
GATEWAY_PORT=5000
MOVIE_SERVICE_URL=http://localhost:5001
RECOMMENDATION_SERVICE_URL=http://localhost:5002
VECTOR_SERVICE_URL=http://localhost:5003
```

## API Examples

### 1. Lấy danh sách phim
```bash
curl "http://localhost:5000/api/movies?page=1&per_page=20"
```

### 2. Tìm kiếm phim
```bash
curl "http://localhost:5000/api/movies?search=avengers&field=movie_name"
```

### 3. Lấy phim tương tự
```bash
curl "http://localhost:5000/api/recommendations/similar?movie_id=tt0068646&method=vector&top_k=10"
```

### 4. Gợi ý cá nhân
```bash
curl -X POST http://localhost:5000/api/recommendations/personalized \
  -H "Content-Type: application/json" \
  -d '{"liked_movies": ["tt0068646", "tt0071562"], "top_k": 10}'
```

### 5. Health check
```bash
curl "http://localhost:5000/health/services"
```

## Lợi ích của Microservices Architecture

1. **Scalability**: Có thể scale từng service độc lập
2. **Maintainability**: Code tách biệt theo chức năng
3. **Flexibility**: Có thể update/deploy từng service riêng
4. **Resilience**: Failure của một service không ảnh hưởng toàn bộ hệ thống
5. **Technology Diversity**: Có thể dùng khác tech stack cho mỗi service
6. **Easy Testing**: Dễ test từng service riêng biệt
7. **CI/CD**: Faster deployment pipeline

## Thêm features mới

Để thêm feature mới, bạn có thể:
1. Tạo service mới trong `microservices/`
2. Implement business logic trong service đó
3. Expose endpoints để Gateway call
4. Thêm health check endpoint
5. Update docker-compose.yml để orchestrate service mới
6. Update API Gateway để proxy requests tới service mới

## Troubleshooting

### Services không connect được nhau
- Kiểm tra docker network: `docker network ls`
- Verify service URLs trong environment variables

### Data file not found
- Kiểm tra volume mappings trong docker-compose.yml
- Đảm bảo `web/` folder có các CSV files

### Port already in use
- Change ports trong docker-compose.yml hoặc environment variables

## Phát triển thêm

Có thể thêm các features sau:
- Database (PostgreSQL/MongoDB) thay cho CSV
- Caching layer (Redis) cho performance
- Message queue (RabbitMQ) cho async processing
- API documentation (Swagger/OpenAPI)
- Logging aggregation (ELK Stack)
- Monitoring (Prometheus + Grafana)
- Load balancer (Nginx)
- Kubernetes orchestration
