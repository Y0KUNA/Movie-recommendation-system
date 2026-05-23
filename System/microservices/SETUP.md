# Development setup for Microservices

Để thiết lập và chạy dự án:

## 1. Install dependencies

```powershell
# For each service
cd api-gateway
pip install -r requirements.txt

cd ..\movie-service
pip install -r requirements.txt

cd ..\recommendation-service
pip install -r requirements.txt

cd ..\vector-service
pip install -r requirements.txt
```

## 2. Run with Docker Compose (Recommended)

```powershell
# Install Docker Desktop for Windows first

# From microservices directory
docker-compose up --build

# Access: http://localhost:5000
```

## 3. Run individually

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

## 4. Run using batch script

```powershell
cd microservices
.\run_all_services.bat
```

## Data requirements

Ensure these files exist in the `web/` folder:
- `imdb_movies_3000.csv` - Movie data
- `movie_vectors.npz` - Pre-computed embeddings

## API Documentation

Main Gateway runs on: **http://localhost:5000**

See README.md in microservices folder for detailed API documentation.
