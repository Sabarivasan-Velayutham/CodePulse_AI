# CodePulse AI - Intelligent Code & Database Impact Analysis Platform

> **AI-powered real-time analysis of code changes and database schema modifications with automated risk assessment and dependency visualization**

---

## 📋 Overview

**CodePulse AI** (also known as **CodeFlow Catalyst**) is an intelligent impact analysis platform that automatically detects and analyzes code changes and database schema modifications in real-time. The system provides comprehensive risk assessment, dependency mapping, and actionable recommendations to prevent production failures before they happen.

### Problem Statement

In modern software development, especially in financial and enterprise applications:
- **Schema changes** can break production systems if not properly analyzed
- **Code changes** have cascading effects that are difficult to track manually
- **Dependency analysis** is time-consuming and error-prone
- **Risk assessment** lacks context-aware intelligence
- **No unified view** of code-to-code and code-to-database relationships

### Our Solution

CodePulse AI provides:
- ✅ **Automatic Detection**: Zero-config monitoring for PostgreSQL and MongoDB schema changes
- ✅ **Real-time Analysis**: Event-driven architecture with instant notifications
- ✅ **AI-Powered Insights**: Google Gemini 1.5 Flash for context-aware risk assessment
- ✅ **Multi-Database Support**: Unified analysis for SQL (PostgreSQL) and NoSQL (MongoDB)
- ✅ **Dependency Visualization**: Interactive Neo4j graph with D3.js rendering
- ✅ **Intelligent Risk Scoring**: Multi-factor algorithm (Technical, Domain, AI, Temporal)

---

## 🏗️ Architecture

### System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   GitHub    │────▶│  FastAPI     │────▶│   DEPENDS   │
│  Webhooks   │     │   Backend    │     │   Analyzer  │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐     ┌─────────────┐
                     │  PostgreSQL │     │   Neo4j     │
                     │   Triggers   │     │  Graph DB   │
                     └──────────────┘     └─────────────┘
                            │                     │
                     ┌──────────────┐             │
                     │   MongoDB    │             │
                     │Change Streams│             │
                     └──────────────┘             │
                            │                     │
                            └─────────┬──────────┘
                                      ▼
                            ┌──────────────┐
                            │ Gemini AI    │
                            │  Analyzer    │
                            └──────────────┘
                                      │
                                      ▼
                            ┌──────────────┐
                            │ Risk Scorer  │
                            └──────────────┘
                                      │
                                      ▼
                            ┌──────────────┐
                            │ React UI +   │
                            │  D3.js Graph │
                            └──────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Code Analysis**: DEPENDS (multilang-depends) tool
- **AI/ML**: Google Gemini 1.5 Flash
- **Graph Database**: Neo4j Community Edition
- **Database Drivers**: 
  - `psycopg2` for PostgreSQL
  - `pymongo` for MongoDB

#### Frontend
- **Framework**: React 18
- **Visualization**: D3.js v7 (dependency graphs)
- **UI Library**: Material-UI v5
- **Charts**: Recharts (risk breakdown)

#### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Version Control**: Git/GitHub
- **API**: RESTful endpoints

### Core Components

#### 1. **Change Detection Layer**
- **PostgreSQL**: Event triggers (`ddl_command_end`, `sql_drop`) with `pg_notify`
- **MongoDB**: Change Streams on database/collections for real-time monitoring
- **GitHub**: Webhook integration for code commit analysis

#### 2. **Dependency Analysis Engine**
- **Code Parsing**: SQL queries, ORM patterns (Hibernate, SQLAlchemy), heuristic detection
- **Database Relationships**: Foreign keys, views, triggers, references
- **Graph Storage**: Neo4j stores all relationships (code-to-code, code-to-database)

#### 3. **AI Analysis Module**
- **Context Understanding**: Semantic analysis of code changes
- **Impact Assessment**: Identifies security, performance, compliance risks
- **Recommendations**: Actionable deployment advice

#### 4. **Risk Scoring Algorithm**
- **Technical Risk (0-4)**: Dependency depth, code complexity, affected modules
- **Domain Risk (0-3)**: Table/collection criticality, business impact
- **AI Risk (0-2)**: AI-identified concerns and semantic risks
- **Temporal Risk (multiplier)**: Time-based factors (deployment windows, etc.)

#### 5. **Visualization Dashboard**
- **Interactive Graphs**: D3.js force-directed graphs
- **Risk Heatmaps**: Color-coded nodes by risk level
- **Drill-down**: Detailed view of dependencies and relationships

---

## 🔄 Data Flow

### Code Change Analysis Flow

1. **Trigger**: Developer commits code to GitHub
2. **Webhook**: GitHub sends webhook to FastAPI backend
3. **Dependency Analysis**: DEPENDS tool analyzes code dependencies
4. **Database Dependencies**: SQL extractor finds database table/collection usage
5. **Graph Storage**: Dependencies stored in Neo4j
6. **AI Analysis**: Gemini analyzes impact and risks
7. **Risk Scoring**: Multi-factor algorithm calculates risk score
8. **Display**: React dashboard shows results with interactive graph

### Schema Change Analysis Flow

#### PostgreSQL:
1. **Schema Change**: DDL command executed (ALTER TABLE, CREATE INDEX, etc.)
2. **Event Trigger**: PostgreSQL event trigger fires
3. **Notification**: `pg_notify` sends notification to listener
4. **Listener**: Python script receives notification
5. **Backend API**: POST to `/api/v1/schema/webhook`
6. **Analysis**: 
   - Parse SQL statement (with enhancement for incomplete SQL)
   - Find code files using the table/column
   - Query PostgreSQL for relationships (foreign keys, views, triggers)
   - Store in Neo4j
   - Run AI analysis
   - Calculate risk score
7. **Display**: Dashboard shows analysis results

#### MongoDB:
1. **Schema Change**: Collection created/dropped or index created/dropped
2. **Change Stream**: MongoDB Change Stream detects change
3. **Listener**: Python script receives change event
4. **Backend API**: POST to `/api/v1/schema/webhook` with `database_type: "mongodb"`
5. **Analysis**:
   - Parse MongoDB operation statement
   - Find code files using the collection (MongoDB-specific patterns)
   - Query MongoDB for relationships (reference fields)
   - Store in Neo4j (using `USES_COLLECTION` relationships)
   - Run AI analysis
   - Calculate risk score
6. **Display**: Dashboard shows MongoDB-specific analysis (Collections, Fields, Indexes)

---

## 🚀 Execution Details

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 16.x or higher
- **Docker**: 20.x or higher
- **Docker Compose**: 2.x or higher
- **PostgreSQL**: 12+ (for schema change detection)
- **MongoDB**: 4.4+ (for schema change detection)
- **Neo4j**: 5.x (via Docker Compose)

### Environment Variables

Create a `.env` file in the root directory:

```env
# Backend
GEMINI_API_KEY=your_gemini_api_key_here
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_DB=banking_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=banking_db

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

### Setup Instructions

#### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (only once)
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (only once)
npm install
```

#### 3. Start Services

```bash
# From root directory, start Docker services
docker-compose up -d backend

# View backend logs
docker-compose logs -f backend
```

#### 4. Start Backend Server

```bash
# From backend directory (with venv activated)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 5. Start Frontend Server

```bash
# From frontend directory
cd frontend
npm start
```

The frontend will open at `http://localhost:3000`

### Verify Setup

```bash
# Run pre-flight check
python tests/test_scenarios.py

# Should show: All systems ready
```

### Access Points

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Backend Health Check**: http://localhost:8000/health

---

## 📊 Usage Examples

### 1. Analyze Code Change

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
    "repository": "banking-app",
    "diff": "- return amount * 0.03;\n+ return amount * 0.025 + 15.0;"
  }'
```

### 2. Analyze Schema Change (PostgreSQL)

```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "ALTER TABLE transactions ADD COLUMN fraud_score DECIMAL(5,2)",
    "database_name": "banking_db",
    "repository": "banking-app"
  }'
```

### 3. Analyze Schema Change (MongoDB)

```bash
curl -X POST http://localhost:8000/api/v1/schema/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sql_statement": "db.transactions.createIndex({amount: 1, processed_at: -1})",
    "database_name": "mongodb_banking_db",
    "database_type": "mongodb",
    "repository": "banking-app-mongodb"
  }'
```

### 4. Load Sample Data

```bash
# Load PostgreSQL sample data
python scripts/load_demo_data.py

# Load MongoDB sample data
python scripts/load_mongodb_data.py
```

### 5. Start Schema Change Listeners

```bash
# PostgreSQL listener
python scripts/postgres_schema_listener.py

# MongoDB listener
python scripts/mongodb_schema_listener.py
```

---

## 🔍 Key Features

### 1. **Automatic Schema Change Detection**

#### PostgreSQL
- Uses event triggers (`ddl_command_end`, `sql_drop`)
- Real-time notifications via `pg_notify`
- Handles incomplete SQL from triggers (enhances with system catalog queries)

#### MongoDB
- Uses Change Streams for real-time monitoring
- Detects collection creation/dropping and index changes
- Falls back to lightweight polling if replica set unavailable

### 2. **Intelligent Dependency Analysis**

- **Code Parsing**: Extracts SQL queries, ORM patterns, heuristic table/collection usage
- **Database Relationships**: Foreign keys, views, triggers, references
- **Graph Storage**: Neo4j stores all relationships for querying and visualization

### 3. **AI-Powered Impact Analysis**

- **Context Understanding**: Analyzes code semantics and business logic
- **Risk Identification**: Security, performance, compliance concerns
- **Recommendations**: Actionable deployment advice

### 4. **Multi-Factor Risk Scoring**

- **Technical Risk (0-4)**: Dependency depth, code complexity
- **Domain Risk (0-3)**: Table/collection criticality, business impact
- **AI Risk (0-2)**: AI-identified semantic risks
- **Temporal Risk (multiplier)**: Time-based factors

### 5. **Interactive Visualization**

- **Dependency Graphs**: D3.js force-directed graphs
- **Risk Heatmaps**: Color-coded nodes (LOW/MEDIUM/HIGH/CRITICAL)
- **Drill-down**: Detailed view of dependencies and relationships

### 6. **Database-Agnostic Analysis**

- **PostgreSQL**: Tables, columns, foreign keys, views, triggers
- **MongoDB**: Collections, fields, indexes, references
- **Unified Interface**: Same analysis pipeline for both database types

---

## 📁 Project Structure

```
CodePulse_AI/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── engine/           # Core analysis engines
│   │   │   ├── ai_analyzer.py
│   │   │   ├── risk_scorer.py
│   │   │   ├── orchestrator.py
│   │   │   └── schema_orchestrator.py
│   │   ├── services/         # Service layer
│   │   │   ├── depends_wrapper.py
│   │   │   ├── sql_extractor.py
│   │   │   ├── schema_analyzer.py
│   │   │   └── mongodb_schema_analyzer.py
│   │   ├── utils/            # Utilities
│   │   │   └── neo4j_client.py
│   │   └── main.py          # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── AnalysisCard/
│   │   │   ├── DependencyGraph/
│   │   │   └── RiskScore/
│   │   ├── services/        # API services
│   │   └── App.jsx
│   └── package.json
├── scripts/
│   ├── postgres_schema_listener.py
│   ├── mongodb_schema_listener.py
│   ├── load_demo_data.py
│   └── load_mongodb_data.py
├── sample-repo/
│   ├── banking-app/         # PostgreSQL code samples
│   ├── banking-app-mongodb/  # MongoDB code samples
│   └── python-analytics/    # Python code samples
├── docs/                     # Documentation
├── tests/                    # Test scripts
├── docker-compose.yml
└── README.md
```

---

## 🎯 Use Cases

### 1. **Pre-Deployment Risk Assessment**
Before deploying a schema change, understand:
- Which code files will be affected
- What database relationships exist
- What risks are involved
- Recommended deployment strategy

### 2. **Code Change Impact Analysis**
When modifying code, identify:
- Downstream dependencies
- Database impacts
- Breaking changes
- Risk level

### 3. **Database Migration Planning**
Plan database migrations by:
- Identifying all affected code
- Understanding relationships
- Assessing migration complexity
- Getting AI recommendations

### 4. **Compliance & Audit**
Maintain compliance by:
- Tracking all schema changes
- Documenting dependencies
- Risk assessment for regulatory changes
- Audit trail in Neo4j

---

## 🔧 Configuration

### PostgreSQL Schema Change Detection

1. **Set up event triggers** (run once):
```bash
psql -U postgres -d banking_db -f docs/postgres-trigger-setup.sql
```

2. **Start listener**:
```bash
python scripts/postgres_schema_listener.py
```

### MongoDB Schema Change Detection

1. **Set up notification collection** (run once):
```bash
mongosh mongodb://localhost:27017/banking_db < docs/mongodb-trigger-setup.js
```

2. **Start listener**:
```bash
python scripts/mongodb_schema_listener.py
```

### GitHub Webhook Integration

1. **Configure webhook** in GitHub repository settings:
   - URL: `http://your-backend-url/api/v1/webhook/github`
   - Content type: `application/json`
   - Events: `push`

2. **Backend automatically processes** commits and analyzes changes

---

## 📈 API Endpoints

### Code Analysis

- `POST /api/v1/analyze` - Analyze code change
- `GET /api/v1/analysis/{id}` - Get analysis results
- `GET /api/v1/graph/{file}` - Get dependency graph for file

### Schema Analysis

- `POST /api/v1/schema/analyze` - Analyze schema change (synchronous)
- `POST /api/v1/schema/webhook` - Schema change webhook (asynchronous)
- `GET /api/v1/schema/analysis/{id}` - Get schema analysis results

### Dependency Graph

- `GET /api/v1/graph/table/{table_name}` - Get table dependency graph
- `GET /api/v1/graph/file/{file_name}` - Get file dependency graph

### Health & Status

- `GET /health` - Health check
- `GET /api/v1/analyses` - List all analyses

---

## 🧪 Testing

### Run Test Scenarios

```bash
python tests/test_scenarios.py
```

### Test Individual Components

```bash
# Test PostgreSQL connection
python -c "from app.utils.postgres_client import test_connection; test_connection()"

# Test MongoDB connection
python -c "from app.utils.mongodb_client import test_connection; test_connection()"

# Test Neo4j connection
python -c "from app.utils.neo4j_client import test_connection; test_connection()"
```

---

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Backend not starting
- Check Docker services: `docker-compose ps`
- Check logs: `docker-compose logs backend`
- Verify environment variables in `.env`

**Problem**: AI analysis failing
- Verify `GEMINI_API_KEY` in `.env`
- Check API quota/limits
- System falls back to rule-based analysis if AI fails

### Frontend Issues

**Problem**: Frontend not connecting to backend
- Verify `REACT_APP_API_URL` in `.env`
- Check CORS settings in backend
- Verify backend is running on port 8000

### Database Issues

**Problem**: PostgreSQL listener not detecting changes
- Verify event triggers are installed
- Check PostgreSQL connection settings
- Ensure listener script is running

**Problem**: MongoDB listener not detecting changes
- Verify Change Streams are available (replica set)
- Check MongoDB connection URI
- Ensure listener script is running

### Neo4j Issues

**Problem**: Graph not displaying
- Verify Neo4j is running: `docker-compose ps neo4j`
- Check Neo4j connection in `.env`
- Access Neo4j browser at http://localhost:7474

---

## 🚧 Future Enhancements

- [ ] Support for more databases (MySQL, Oracle, etc.)
- [ ] Real-time collaboration features
- [ ] Integration with CI/CD pipelines (Jenkins, GitLab CI, etc.)
- [ ] Advanced AI models for better context understanding
- [ ] Historical trend analysis
- [ ] Automated test generation based on changes
- [ ] Integration with issue tracking systems (Jira, GitHub Issues)

---

## 📝 License

This project is developed for a hackathon competition.

---

## 👥 Contributors

Developed as part of a hackathon project.

---

## 📚 Additional Documentation

- [Architecture Details](docs/architecture.md)
- [PostgreSQL Setup Guide](docs/database-schema-analysis-setup.md)
- [MongoDB Setup Guide](docs/MONGODB_SETUP_GUIDE.md)
- [MongoDB Change Streams](docs/MONGODB_CHANGE_STREAMS_SETUP.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)

---

## 🎯 Quick Start Summary

1. **Setup**: Install dependencies, configure `.env`, start Docker services
2. **Start**: Run backend (`uvicorn`), frontend (`npm start`), listeners
3. **Test**: Make a schema change or code commit
4. **View**: Check dashboard at http://localhost:3000
5. **Explore**: View dependency graphs and risk scores

---

**For detailed setup instructions, see the [Execution Details](#-execution-details) section above.**
