#!/bin/bash

# Docker startup script for all CrowdStream services

echo "=== Building and Starting CrowdStream Services in Docker ==="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Build and start services
docker-compose up --build -d

echo ""
echo "=== Services Starting ==="
echo ""
echo "📊 Dashboard:       http://localhost:8082"
echo "🌌 Cosmic Journey:  http://localhost:8091"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To view individual service logs:"
echo "  docker-compose exec crowdstream-services tail -f /app/logs/movement_dashboard.log"
echo "  docker-compose exec crowdstream-services tail -f /app/logs/cosmic.log"
echo "  docker-compose exec crowdstream-services tail -f /app/logs/detector.log"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
