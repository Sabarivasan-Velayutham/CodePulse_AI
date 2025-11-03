#!/bin/bash

# CodeFlow Catalyst - Quick Start Script
# Starts all services and prepares for demo

set -e  # Exit on error

echo "=========================================="
echo "🚀 CodeFlow Catalyst - Quick Start"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo "📋 Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker."
    exit 1
fi
print_success "Docker installed"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.10+."
    exit 1
fi
print_success "Python 3 installed"

# Check Node
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install Node.js 18+."
    exit 1
fi
print_success "Node.js installed"

# Check Java
if ! command -v java &> /dev/null; then
    print_error "Java not found. Please install Java 11+."
    exit 1
fi
print_success "Java installed"

echo ""
echo "=========================================="
echo "🔧 Setting up services..."
echo "=========================================="
echo ""

# Start Neo4j
echo "1️⃣  Starting Neo4j database..."
docker-compose up -d neo4j
sleep 10
print_success "Neo4j started (http://localhost:7474)"

# Check if Neo4j is ready
echo "   Waiting for Neo4j to be ready..."
for i in {1..10}; do
    if docker exec codeflow-neo4j cypher-shell -u neo4j -p codeflow123 "RETURN 1" &> /dev/null; then
        print_success "Neo4j is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        print_error "Neo4j failed to start"
        exit 1
    fi
    sleep 2
done

# Initialize Neo4j with sample data
echo ""
echo "2️⃣  Initializing sample data..."
cd sample-repo
if [ -f "init_neo4j.py" ]; then
    python3 init_neo4j.py << EOF
yes
EOF
    print_success "Sample data loaded"
else
    print_warning "init_neo4j.py not found, skipping data initialization"
fi
cd ..

# Install backend dependencies
echo ""
echo "3️⃣  Installing backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
print_success "Backend dependencies installed"
cd ..

# Install frontend dependencies
echo ""
echo "4️⃣  Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install --silent
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi
cd ..

# Check GEMINI_API_KEY
echo ""
echo "5️⃣  Checking environment variables..."
if [ -z "$GEMINI_API_KEY" ]; then
    print_warning "GEMINI_API_KEY not set"
    echo "   Please set it in backend/.env file"
    echo "   Or export GEMINI_API_KEY=your_key_here"
else
    print_success "GEMINI_API_KEY configured"
fi

echo ""
echo "=========================================="
echo "🎯 Starting services..."
echo "=========================================="
echo ""

# Start backend
echo "6️⃣  Starting backend server..."
cd backend
source venv/bin/activate
python app/main.py &
BACKEND_PID=$!
cd ..
sleep 5

# Check if backend started
if ps -p $BACKEND_PID > /dev/null; then
    print_success "Backend started (http://localhost:8000)"
else
    print_error "Backend failed to start"
    exit 1
fi

# Start frontend
echo ""
echo "7️⃣  Starting frontend server..."
cd frontend
BROWSER=none npm start &
FRONTEND_PID=$!
cd ..
sleep 10

# Check if frontend started
if ps -p $FRONTEND_PID > /dev/null; then
    print_success "Frontend started (http://localhost:3000)"
else
    print_error "Frontend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All services started successfully!"
echo "=========================================="
echo ""
echo "📊 Service URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   Neo4j:     http://localhost:7474"
echo ""
echo "📖 API Documentation:"
echo "   Swagger UI: http://localhost:8000/docs"
echo ""
echo "🎬 Ready for demo!"
echo ""
echo "💡 Tips:"
echo "   - Run: python scripts/demo_runner.py (for demo scenarios)"
echo "   - Run: python tests/integration_test.py (to test system)"
echo "   - Press Ctrl+C to stop all services"
echo ""

# Save PIDs for cleanup
echo "$BACKEND_PID" > /tmp/codeflow_backend.pid
echo "$FRONTEND_PID" > /tmp/codeflow_frontend.pid

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose down; echo '✅ All services stopped'; exit 0" INT

# Keep script running
wait
