# CodeFlow Catalyst - Technical Architecture

## System Overview
```
[GitHub Webhook] → [FastAPI Backend] → [DEPENDS Tool] → [Neo4j Graph]
                           ↓
                    [Gemini AI Analysis]
                           ↓
                    [Risk Scoring Engine]
                           ↓
                    [React Dashboard]
```

## Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **Analysis Tool:** DEPENDS (multilang-depends)
- **AI/ML:** Google Gemini 1.5 Flash
- **Database:** Neo4j Community Edition
- **Language:** Python 3.10+

### Frontend
- **Framework:** React 18
- **Visualization:** D3.js v7
- **UI Library:** Material-UI v5
- **Charts:** Recharts

### Infrastructure
- **Containerization:** Docker & Docker Compose
- **Version Control:** Git/GitHub

## Data Flow

1. **Trigger:** Developer commits code to GitHub
2. **Webhook:** GitHub sends webhook to FastAPI
3. **Analysis:** DEPENDS tool analyzes code dependencies
4. **Storage:** Dependencies stored in Neo4j graph
5. **AI Analysis:** Gemini analyzes impact and risks
6. **Scoring:** Custom algorithm calculates risk score
7. **Display:** React dashboard shows results

## API Endpoints

### POST /api/v1/webhook/github
Receives GitHub webhook events

### POST /api/v1/analyze
Triggers manual code analysis

### GET /api/v1/analysis/{id}
Retrieves analysis results

### GET /api/v1/graph/{file}
Gets dependency graph for file

## Database Schema (Neo4j)

### Nodes
- `Module`: Code files/classes
- `Method`: Functions/methods
- `DataTable`: Database tables
- `API`: API endpoints

### Relationships
- `CALLS`: Method calls
- `IMPORTS`: Import dependencies
- `READS/WRITES`: Data access
- `DEPENDS_ON`: General dependency

## Security
- API key authentication
- CORS configuration
- Input validation
- Rate limiting (future)