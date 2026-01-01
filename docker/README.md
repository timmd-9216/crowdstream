# Docker Setup

This directory contains all Docker-related files for running CrowdStream services in containers.

## Files

- `Dockerfile` - Main Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `docker-start.sh` - Script to build and start services

## Quick Start

```bash
cd docker
./docker-start.sh
```

Or from the project root:

```bash
./docker/docker-start.sh
```

## Services

The Docker setup runs:
- **Dashboard**: http://localhost:8082
- **Cosmic Journey Visualizer**: http://localhost:8091

## View Logs

```bash
cd docker
docker-compose logs -f
```

Or view individual service logs:

```bash
docker-compose exec crowdstream-services tail -f /app/logs/movement_dashboard.log
docker-compose exec crowdstream-services tail -f /app/logs/cosmic.log
docker-compose exec crowdstream-services tail -f /app/logs/detector.log
```

## Stop Services

```bash
cd docker
docker-compose down
```

## Building Manually

```bash
cd docker
docker-compose build
docker-compose up -d
```

## Configuration

The `docker-compose.yml` file:
- Builds from `Dockerfile` in this directory
- Maps webcam device `/dev/video0` to container
- Mounts `../logs` directory for log persistence
- Exposes ports 8082 (Dashboard) and 8091 (Visualizer)

## Notes

- The Dockerfile uses the project root as build context
- Scripts are copied from `scripts/` directory
- Logs are persisted in `../logs` relative to docker directory


