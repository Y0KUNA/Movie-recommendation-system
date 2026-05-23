#!/bin/bash
# Script to run all microservices on Linux/Mac
# Usage: chmod +x run_all_services.sh && ./run_all_services.sh

# Check if running in the correct directory
if [ ! -d "api-gateway" ]; then
    echo "Error: Please run this script from the microservices directory"
    exit 1
fi

echo "Starting all microservices..."
echo ""

# Function to run service in background
run_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    
    echo "Starting $service_name on port $port..."
    (cd "$service_dir" && \
     pip install -r requirements.txt && \
     python app.py) &
    
    sleep 2
}

# Run all services
run_service "Movie Service" "movie-service" "5001"
run_service "Vector Service" "vector-service" "5003"
run_service "Recommendation Service" "recommendation-service" "5002"
run_service "API Gateway" "api-gateway" "5000"

echo ""
echo "All services are starting..."
echo ""
echo "Services URLs:"
echo "- API Gateway: http://localhost:5000"
echo "- Movie Service: http://localhost:5001"
echo "- Recommendation Service: http://localhost:5002"
echo "- Vector Service: http://localhost:5003"
echo ""
echo "Check service health: curl http://localhost:5000/health/services"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait
