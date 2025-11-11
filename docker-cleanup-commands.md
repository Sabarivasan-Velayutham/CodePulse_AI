# Docker Cleanup and Rebuild Commands

## ✅ Configuration Status
- **sample-repo**: ✅ Properly configured at line 37: `./sample-repo:/sample-repo`
- **All volumes**: ✅ Correctly mounted
- **Restart policies**: ✅ Added to all services

## 🧹 Complete Cleanup and Rebuild Commands

### Option 1: Complete Clean (Recommended - Removes Everything)

```bash
# Stop all containers
docker-compose down

# Remove all containers, networks, and volumes
docker-compose down -v

# Remove all unused Docker resources (images, containers, networks, build cache)
docker system prune -a --volumes

# Remove specific images if needed
docker rmi codeflow-backend codeflow-frontend 2>/dev/null || true

# Rebuild without cache
docker-compose build --no-cache

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 2: Quick Clean (Keeps Volumes - Preserves Neo4j Data)

```bash
# Stop containers
docker-compose down

# Remove containers and networks (keeps volumes)
docker-compose down

# Remove build cache only
docker builder prune -a -f

# Rebuild without cache
docker-compose build --no-cache

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 3: Selective Service Rebuild

```bash
# Stop specific service
docker-compose stop backend

# Remove specific container
docker-compose rm -f backend

# Rebuild specific service without cache
docker-compose build --no-cache backend

# Start specific service
docker-compose up -d backend

# View logs for specific service
docker-compose logs -f backend
```

## 📊 Check Docker Disk Usage

```bash
# Check disk usage
docker system df

# Detailed view
docker system df -v
```

## 🗑️ Remove Unused Resources Only

```bash
# Remove unused containers, networks, images (dangling)
docker system prune

# Remove unused images (not just dangling)
docker image prune -a

# Remove unused volumes (CAREFUL - removes Neo4j data if not in use)
docker volume prune

# Remove build cache
docker builder prune
```

## 🔄 Quick Restart (No Cleanup)

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
```

## 📝 Useful Monitoring Commands

```bash
# View running containers
docker-compose ps

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Check container resource usage
docker stats

# Enter container shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 🚀 Full Rebuild Script (Windows PowerShell)

Save as `rebuild-docker.ps1`:

```powershell
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "Removing unused resources..." -ForegroundColor Yellow
docker system prune -f

Write-Host "Rebuilding without cache..." -ForegroundColor Yellow
docker-compose build --no-cache

Write-Host "Starting services..." -ForegroundColor Green
docker-compose up -d

Write-Host "Viewing logs..." -ForegroundColor Cyan
docker-compose logs -f
```

## 🚀 Full Rebuild Script (Linux/Mac Bash)

Save as `rebuild-docker.sh`:

```bash
#!/bin/bash

echo "Stopping containers..."
docker-compose down

echo "Removing unused resources..."
docker system prune -f

echo "Rebuilding without cache..."
docker-compose build --no-cache

echo "Starting services..."
docker-compose up -d

echo "Viewing logs..."
docker-compose logs -f
```

## ⚠️ Important Notes

1. **Neo4j Data**: If you use `docker-compose down -v`, it will **DELETE** Neo4j data volumes. Use `docker-compose down` to keep data.

2. **Environment Variables**: Make sure you have a `.env` file in the root directory with:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. **sample-repo**: Already properly mounted at `/sample-repo` inside the container.

4. **Port Conflicts**: If ports 3000, 8000, 7474, or 7687 are in use, stop the conflicting services first.

## 🔍 Verify Configuration

```bash
# Check if sample-repo is accessible in container
docker-compose exec backend ls -la /sample-repo

# Check if tools are accessible
docker-compose exec backend ls -la /tools

# Check environment variables
docker-compose exec backend env | grep GEMINI
```

