# Backend - AI Test Case Generator

FastAPI-based backend service for AI-powered test case generation from SRS documents and UI screenshots.

![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Database](https://img.shields.io/badge/database-PostgreSQL-336791)

## 🏗️ Architecture

This backend consists of two main components:

1. **REST API Server**: FastAPI application that handles file uploads and job management
2. **Background Worker**: Kafka consumer that processes jobs and generates test cases using LLM

```
┌──────────────┐      ┌──────────────┐      ┌─────────────┐
│   FastAPI    │─────▶│  PostgreSQL  │      │    MinIO    │
│     API      │      │   Database   │      │   Storage   │
└──────────────┘      └──────────────┘      └─────────────┘
       │                                            ▲
       │                                            │
       ▼                                            │
┌──────────────┐                                   │
│    Kafka     │                                   │
│    Queue     │                                   │
└──────────────┘                                   │
       │                                            │
       ▼                                            │
┌──────────────┐                                   │
│  Background  │───────────────────────────────────┘
│    Worker    │
└──────────────┘
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy database models
│   ├── database.py            # Database configuration
│   ├── kafka_producer.py      # Kafka producer helper
│   ├── storage.py             # MinIO integration
│   └── routers/
│       ├── upload.py          # File upload endpoints
│       └── jobs.py            # Job management endpoints
├── worker/
│   ├── __init__.py
│   ├── main.py                # Worker entry point
│   ├── processor.py           # Job processing logic
│   ├── llm.py                 # LLM integration (OpenRouter)
│   ├── models.py              # Pydantic models for worker
│   └── storage.py             # MinIO helpers for worker
├── .env.example               # Environment variables template
├── .gitignore
├── Dockerfile                 # Worker container image
├── main.py                    # FastAPI application entry point
├── migrate_db.py              # Database migration script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL running on `localhost:5432`
- Kafka running on `localhost:19093`
- MinIO running on `localhost:9000`
- OpenRouter API key ([get one here](https://openrouter.ai/))

> **Note**: All infrastructure services are typically started using the [infrastructure](https://github.com/AI-based-Test-Case-Generation/infrastructure) repository.

### 1. Clone the Repository

```bash
git clone https://github.com/AI-based-Test-Case-Generation/backend.git
cd backend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/testcase_db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:19093

# MinIO
MINIO_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# LLM Settings
USE_LLM=true
```

### 4. Initialize Database

```bash
python migrate_db.py
```

### 5. Start the API Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔌 API Endpoints

### Health Check
```bash
GET /health
```

### Upload Files
```bash
POST /api/v1/upload
Content-Type: multipart/form-data

Parameters:
- file: Document file (PDF, DOCX, TXT)
- images: UI screenshots (optional, multiple)
```

### List Jobs
```bash
GET /api/v1/jobs
```

### Get Job Details
```bash
GET /api/v1/jobs/{job_id}
```

### Get Test Cases
```bash
GET /api/v1/jobs/{job_id}/testcases
```

### Cancel Job
```bash
POST /api/v1/jobs/{job_id}/cancel
```

## 🔧 Background Worker

The background worker processes jobs from the Kafka queue. It can be run in two ways:

### Option 1: Docker (Recommended)

The worker is typically run as a Docker container using the infrastructure setup:

```bash
# From the infrastructure repository
docker compose up -d worker
```

### Option 2: Local Development

```bash
python -m worker.main
```

## 🗄️ Database Schema

### Jobs Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| filename | VARCHAR | Original filename |
| file_path | VARCHAR | MinIO path |
| image_paths | JSON | Array of image paths |
| status | VARCHAR | PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED |
| error_message | TEXT | Error details if failed |
| created_at | TIMESTAMP | Job creation time |
| updated_at | TIMESTAMP | Last update time |

### Test Cases Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| job_id | INTEGER | Foreign key to jobs |
| test_id | VARCHAR | Test case identifier |
| description | TEXT | Test case description |
| preconditions | TEXT | Prerequisites |
| steps | JSON | Array of test steps |
| expected_output | TEXT | Expected result |
| priority | VARCHAR | HIGH, MEDIUM, LOW |
| category | VARCHAR | FUNCTIONAL, UI, INTEGRATION, etc. |
| created_at | TIMESTAMP | Creation time |

## 🧪 Testing

### Manual API Testing

```bash
# Health check
curl http://localhost:8000/health

# Upload a document
curl -X POST \
  -F "file=@test_requirements.txt" \
  http://localhost:8000/api/v1/upload

# Check job status
curl http://localhost:8000/api/v1/jobs/1

# Get test cases
curl http://localhost:8000/api/v1/jobs/1/testcases
```

### Interactive API Testing

Open http://localhost:8000/docs in your browser for Swagger UI with interactive API testing.

## 🔐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address | `localhost:19093` |
| `MINIO_URL` | MinIO server URL | `http://localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | `minioadmin` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `USE_LLM` | Enable LLM for test generation | `true` |

## 🛠️ Development

### Code Structure

- **`app/`**: REST API implementation
  - `models.py`: SQLAlchemy ORM models
  - `database.py`: Database session management
  - `storage.py`: MinIO file operations
  - `kafka_producer.py`: Kafka message publishing
  - `routers/`: API endpoint definitions

- **`worker/`**: Background job processor
  - `main.py`: Kafka consumer setup
  - `processor.py`: Job processing logic
  - `llm.py`: OpenRouter LLM integration
  - `storage.py`: Worker-specific MinIO operations

### Adding New Endpoints

1. Create a new router in `app/routers/`
2. Define your endpoints using FastAPI decorators
3. Register the router in `main.py`

### Customizing Test Generation

Edit `worker/llm.py` to customize:
- LLM model selection
- Prompt engineering
- Test case format

Edit `worker/processor.py` to customize:
- Fallback test case generation
- Document processing logic
- Error handling

## 🐛 Troubleshooting

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -U user -h localhost -d testcase_db
```

### Kafka Connection Errors

```bash
# Verify Kafka is running
docker ps | grep kafka

# Check if topic exists (from infrastructure repo)
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### MinIO Connection Errors

```bash
# Verify MinIO is running
curl http://localhost:9000/minio/health/live

# Check bucket exists
docker exec minio mc ls myminio
```

### Worker Not Processing Jobs

```bash
# Check worker logs
docker logs -f worker

# Verify Kafka messages
# Open http://localhost:8080 to view Kafka UI
```

## 📦 Dependencies

Key dependencies:
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM for database operations
- **aiokafka**: Async Kafka client
- **boto3**: MinIO/S3 operations
- **openai**: OpenRouter API client
- **PyPDF2**: PDF parsing
- **python-docx**: DOCX parsing
- **psycopg2-binary**: PostgreSQL adapter

See `requirements.txt` for complete list.

## 🔄 Updates & Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Database Migrations

When modifying models in `app/models.py`:

```bash
# For now, manually update the database or re-run migrate_db.py
# TODO: Add Alembic for proper migrations
```

## 📝 API Response Examples

### Upload Response
```json
{
  "job_id": 1,
  "status": "PENDING",
  "filename": "requirements.pdf",
  "images_uploaded": 2,
  "created_at": "2025-12-03T12:00:00"
}
```

### Job Status Response
```json
{
  "id": 1,
  "filename": "requirements.pdf",
  "status": "COMPLETED",
  "created_at": "2025-12-03T12:00:00",
  "updated_at": "2025-12-03T12:05:00"
}
```

### Test Cases Response
```json
[
  {
    "test_id": "TC001",
    "description": "Verify user login with valid credentials",
    "preconditions": "User account exists in the system",
    "steps": [
      "Navigate to login page",
      "Enter valid username",
      "Enter valid password",
      "Click login button"
    ],
    "expected_output": "User is logged in and redirected to dashboard",
    "priority": "HIGH",
    "category": "FUNCTIONAL"
  }
]
```

## 🤝 Contributing

When contributing to this repository:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📄 License

MIT License

## 🔗 Related Repositories

- [Frontend](https://github.com/AI-based-Test-Case-Generation/frontend) - Next.js web application
- [Infrastructure](https://github.com/AI-based-Test-Case-Generation/infrastructure) - Docker Compose setup

---

**Part of the AI-based Test Case Generation project**
