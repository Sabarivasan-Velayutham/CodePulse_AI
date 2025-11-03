#!/bin/bash

echo "🛑 Stopping CodeFlow Catalyst services..."

# Kill backend
if [ -f /tmp/codeflow_backend.pid ]; then
    kill $(cat /tmp/codeflow_backend.pid) 2>/dev/null
    rm /tmp/codeflow_backend.pid
    echo "✅ Backend stopped"
fi

# Kill frontend
if [ -f /tmp/codeflow_frontend.pid ]; then
    kill $(cat /tmp/codeflow_frontend.pid) 2>/dev/null
    rm /tmp/codeflow_frontend.pid
    echo "✅ Frontend stopped"
fi

# Stop Docker containers
docker-compose down
echo "✅ Neo4j stopped"

echo "✅ All services stopped"