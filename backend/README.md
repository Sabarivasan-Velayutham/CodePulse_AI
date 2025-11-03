# CodeFlow Catalyst - Backend

## Quick Start

### Prerequisites
- Python 3.10+
- Java 11+ (for DEPENDS tool)
- Docker (for Neo4j)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start Neo4j
docker-compose up -d neo4j

# Initialize sample data
python ../sample-repo/init_neo4j.py

# Run backend
python app/main.py
```

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Trigger Analysis
```bash
POST /api/v1/analyze
Content-Type: application/json

{
  "file_path": "src/payment/PaymentProcessor.java",
  "repository": "banking-app",
  "diff": "code diff here"
}
```

#### Get Analysis
```bash
GET /api/v1/analysis/{id}
```

#### List Analyses
```bash
GET /api/v1/analyses?limit=10
```

#### Get Dependency Graph
```bash
GET /api/v1/graph/{file_name}
```

#### GitHub Webhook
```bash
POST /api/v1/webhook/github
Content-Type: application/json

{
  "event": "push",
  "repository": "repo-name",
  "commit_sha": "abc123",
  "author": "user@email.com",
  "branch": "main",
  "files_changed": [...],
  "diff": "..."
}
```

### Testing

#### Unit Tests
```bash
pytest tests/
```

#### Integration Test
```bash
# Run webhook simulator
python app/utils/webhook_simulator.py scenario1_fee_change

# Check result
curl http://localhost:8000/api/v1/analyses
```

### Architecture
````
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/                 # API endpoints
│   │   ├── webhooks.py      # Webhook handlers
│   │   └── analysis.py      # Analysis endpoints
│   ├── engine/              # Analysis engine
│   │   ├── orchestrator.py  # Main orchestrator
│   │   ├── ai_analyzer.py   # AI analysis
│   │   └── risk_scorer.py   # Risk scoring
│   ├── services/            # External services
│   │   └── depends_wrapper.py  # DEPENDS integration
│   ├── models/              # Data models
│   │   └── schemas.py       # Pydantic schemas
│   └── utils/               # Utilities
│       ├── neo4j_client.py  # Neo4j connection
│       ├── cache.py         # Caching
│       └── logger.py        # Logging

Environment Variables

````
GEMINI_API_KEY: Google Gemini API key
NEO4J_URI: Neo4j connection URI
NEO4J_USER: Neo4j username
NEO4J_PASSWORD: Neo4j password
DEPENDS_JAR_PATH: Path to DEPENDS jar file
````

Troubleshooting
Issue: DEPENDS not found
bash# Download DEPENDS
cd tools/depends
wget https://github.com/multilang-depends/depends/releases/download/v0.9.7/depends-0.9.7.jar
Issue: Neo4j connection failed
bash# Check Neo4j is running
docker ps | grep neo4j

# Start if not running
docker-compose up -d neo4j

# Check logs
docker logs codeflow-neo4j
Issue: Gemini API error
bash# Verify API key
echo $GEMINI_API_KEY

# Test API
python << EOF
import google.generativeai as genai
import os
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Hello")
print(response.text)
EOF
````
````

**✅ TESTING CHECKPOINT 2.5:**
````bash
# Verify documentation
cat backend/README.md
# Should show complete documentation
````

---
````
Completed:
✅ API endpoints created
✅ Webhook handler implemented
✅ Webhook simulator for demo
✅ Response caching added
✅ Request logging implemented
✅ Complete documentation

Test commands:
```
$ python app/main.py
$ curl http://localhost:8000/api/v1/analyses
$ python app/utils/webhook_simulator.py scenario1_fee_change
````