# Using Local MongoDB Installation

This guide shows how to use your existing local MongoDB installation instead of the Docker container.

## Prerequisites

- MongoDB installed and running on your system
- MongoDB accessible on `localhost:27017` (default port)

## Step 1: Verify MongoDB is Running

```bash
# Check if MongoDB is running
mongosh mongodb://localhost:27017/

# Or check service status
# Windows
sc query MongoDB

# Linux/Mac
sudo systemctl status mongod
# or
ps aux | grep mongod
```

## Step 2: Configure Connection

### For Listener (Running Locally)

The listener script already defaults to `localhost:27017`:

```bash
# Default connection (no changes needed)
python scripts/mongodb_schema_listener.py

# Or set explicitly
export MONGO_URI="mongodb://localhost:27017/"
python scripts/mongodb_schema_listener.py
```

### For Backend (Running in Docker)

The backend in Docker needs to connect to your host MongoDB. It's already configured to use `host.docker.internal`:

```bash
# In docker-compose.yml, MongoDB URI is set to:
MONGO_URI=mongodb://host.docker.internal:27017/
```

**Note**: `host.docker.internal` works on:
- ✅ Docker Desktop (Windows/Mac)
- ✅ Docker Desktop (Linux with special config)
- ❌ Native Docker on Linux (use `172.17.0.1` or your host IP)

### For Linux Native Docker

If you're using native Docker on Linux, update `docker-compose.yml`:

```yaml
environment:
  - MONGO_URI=mongodb://172.17.0.1:27017/  # Docker bridge network gateway
```

Or find your host IP:

```bash
# Get Docker bridge gateway IP
docker network inspect bridge | grep Gateway
```

## Step 3: Load Sample Data

```bash
# Make sure MongoDB is running
mongosh mongodb://localhost:27017/

# Load data (connects to localhost by default)
python scripts/load_mongodb_data.py
```

## Step 4: Start Services

### Option A: Backend in Docker, MongoDB Local

```bash
# Start backend (MongoDB service is commented out in docker-compose.yml)
docker-compose up -d backend frontend neo4j

# Start MongoDB listener locally
python scripts/mongodb_schema_listener.py
```

### Option B: Everything Local

```bash
# Start backend locally (not in Docker)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start MongoDB listener locally
python scripts/mongodb_schema_listener.py
```

## Step 5: Test Connection

### Test from Listener

```bash
python scripts/mongodb_schema_listener.py
# Should show: ✅ Connected to MongoDB
```

### Test from Backend (if in Docker)

```bash
# Check backend logs
docker-compose logs backend | grep MongoDB

# Or test manually
docker exec -it codeflow-backend python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://host.docker.internal:27017/', serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print('✅ MongoDB connection successful')
"
```

## Configuration Summary

### Environment Variables

| Variable | Local MongoDB | Docker MongoDB |
|----------|---------------|----------------|
| `MONGO_URI` (Listener) | `mongodb://localhost:27017/` | `mongodb://localhost:27017/` |
| `MONGO_URI` (Backend in Docker) | `mongodb://host.docker.internal:27017/` | `mongodb://mongodb:27017/` |
| `MONGO_DB` | `banking_db` | `banking_db` |

### docker-compose.yml

The MongoDB service is now **commented out** by default. To use Docker MongoDB instead:

1. Uncomment the `mongodb:` service block
2. Change backend `MONGO_URI` to `mongodb://mongodb:27017/`
3. Restart: `docker-compose up -d`

## Troubleshooting

### Issue: Backend can't connect to local MongoDB

**Symptom**: `Connection refused` or timeout errors

**Solution**:
1. Verify MongoDB is running: `mongosh mongodb://localhost:27017/`
2. Check MongoDB is listening on all interfaces:
   ```yaml
   # In MongoDB config (mongod.conf)
   net:
     bindIp: 0.0.0.0  # Allow connections from Docker
   ```
3. For Linux native Docker, use `172.17.0.1` instead of `host.docker.internal`

### Issue: Listener can't connect

**Symptom**: `ConnectionFailure` error

**Solution**:
```bash
# Test connection manually
mongosh mongodb://localhost:27017/

# Check MongoDB is running
# Windows
net start MongoDB

# Linux/Mac
sudo systemctl start mongod
```

### Issue: Firewall blocking connection

**Solution**:
- Allow port 27017 in your firewall
- Or use `127.0.0.1` instead of `localhost` (if MongoDB only binds to localhost)

## Quick Start with Local MongoDB

```bash
# 1. Ensure MongoDB is running
mongosh mongodb://localhost:27017/

# 2. Load sample data
python scripts/load_mongodb_data.py

# 3. Start backend (if using Docker)
docker-compose up -d backend frontend neo4j

# 4. Start MongoDB listener
python scripts/mongodb_schema_listener.py

# 5. Make schema changes in MongoDB
mongosh mongodb://localhost:27017/
use banking_db
db.transactions.createIndex({amount: 1})

# 6. View results at http://localhost:3000
```

## Benefits of Using Local MongoDB

✅ **No Docker overhead** - Direct connection, faster  
✅ **Use existing setup** - No need to manage another container  
✅ **Easier debugging** - Direct access to MongoDB logs  
✅ **Persistent data** - Data stays in your MongoDB instance  

The system works exactly the same whether MongoDB is in Docker or local!

