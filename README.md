# Financial Document Analyzer

A comprehensive financial document analysis system that processes corporate reports, financial statements, and investment documents using AI-powered analysis agents. This is a production-grade system built with modern full-stack technologies and enterprise-level practices.

## 🚀 Features

- **AI-Powered Analysis**: Advanced financial document analysis using CrewAI agents
- **Multi-Format Support**: Process PDF documents, financial reports, and investment documents
- **Secure Authentication**: JWT-based authentication with role-based access control
- **Real-time Processing**: Background job processing with Redis queue system
- **Scalable Architecture**: Docker-based microservices with load balancing
- **Modern UI**: React-based frontend with TailwindCSS and responsive design
- **Database Integration**: MongoDB for document storage and analysis history
- **Caching Layer**: Redis caching for improved performance
- **Observability**: LLM monitoring and system observability tools

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: MongoDB with Motor driver
- **Cache**: Redis
- **AI/ML**: CrewAI, LangChain, OpenAI
- **Authentication**: JWT with Passlib
- **Background Jobs**: Redis-based job queue
- **Monitoring**: OpenTelemetry, Sentry

### Frontend
- **Framework**: React 19
- **Styling**: TailwindCSS, Shadcn UI components
- **State Management**: Zustand
- **Routing**: React Router DOM
- **Forms**: React Hook Form with Zod validation

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Load Balancer**: Nginx
- **Runtime**: Python 3.11, Node.js 18+

## 📋 Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.11.x** (Required for optimal performance and compatibility)
- **Node.js 18+** (for frontend development)
- **Docker** and **Docker Compose**
- **PNPM** (recommended for frontend package management)
- **uv** (fast Python package and project manager: https://docs.astral.sh/uv/)

## 🔧 Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd financial-document-analyzer
```

### 2. Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Install dependencies using uv:

```bash
uv sync
```

# Note: uv sync will automatically create a virtual environment (.venv) if it doesn't exist and install dependencies from pyproject.toml and uv.lock

3. Create a `.env` file from the example:

```bash
cp .env.example .env
```

4. Update the `.env` file with your environment-specific values:
   - Database connection strings
   - API keys for AI services (OpenAI, Cohere, etc.)
   - JWT secrets
   - Redis connection details

### 3. Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
pnpm install
# or npm install
```

3. Create a `.env` file from the example:

```bash
cp .env.example .env
```

4. Update the `.env` file with your environment-specific values.

### 4. Running Development Servers

#### Option A: Running Services Separately

1. **Backend** (in backend directory):
```bash
uv run python main.py
```

2. **Frontend** (in frontend directory):
```bash
pnpm dev
```

#### Option B: Using Docker for Development

1. Run the entire stack with Docker Compose:

```bash
docker-compose up --build
```

This will start MongoDB, Redis, Backend API, Nginx load balancer, Worker, and Frontend services.

### 5. Adding Sample Documents

The system analyzes financial documents like Tesla's Q2 2025 financial update.

**To add Tesla's financial document:**
1. Download the Tesla Q2 2025 update from: https://www.tesla.com/sites/default/files/downloads/TSLA-Q2-2025-Update.pdf
2. Save it as `data/TSLA-Q2-2025-Update.pdf` in the project directory
3. Or upload any financial PDF through the API endpoint or frontend interface

## 🏗️ Project Structure

```
financial-document-analyzer/
├── backend/
│   ├── agents.py          # AI agents for document analysis
│   ├── config.py          # Configuration settings
│   ├── db.py              # Database connection and setup
│   ├── main.py            # Main FastAPI application
│   ├── services/          # API route definitions
│   ├── repositories/      # Database operations
│   └── tools.py           # AI tools for agents
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── data/                  # Sample documents
├── docker-compose.yml     # Multi-service orchestration
├── Dockerfile.backend     # Backend container
├── Dockerfile.frontend    # Frontend container
├── Dockerfile.worker      # Worker container
└── nginx-lb.conf          # Load balancer configuration
```

## 🚀 Production Deployment

### Production Docker Deployment

The application is designed for containerized deployment using Docker Compose.

1. **Build and Deploy**:

```bash
# Build and start all services in production mode
docker-compose up --build -d
```

2. **Environment Configuration**:

Update the environment variables in the `docker-compose.yml` file for production, including:
- Production database connection strings
- Production API keys
- Security headers and environment settings
- SSL certificates for HTTPS

3. **Service Scaling**:

The backend service is configured with multiple replicas for load distribution. Scale as needed:

```bash
docker-compose up --scale backend=3
```

### Production URLs

- **Frontend**: `http://localhost:3000` (or behind nginx: `http://localhost:8080`)
- **Backend API**: `http://localhost:8000`
- **MongoDB**: `http://localhost:27017`
- **Redis**: `http://localhost:6379`

### Security Considerations

- JWT-based authentication with secure tokens
- Rate limiting and request validation
- Input sanitization and file upload security
- Secure environment variable management
- CORS policy configured for production domains only

### Monitoring and Observability

- **LLM Observability**: Integrated tools to monitor LLM calls and tool usage
- **Error Tracking**: Sentry for production error monitoring
- **API Logging**: Structured logging for debugging and monitoring
- **Database Monitoring**: Connection pooling and query optimization

## 🧪 Testing

### Backend Tests

```bash
# From backend directory
uv run pytest
```

### Frontend Tests

```bash
# From frontend directory
pnpm test
```

## 🔧 Configuration

### Environment Variables

The application uses environment variables for configuration. Key variables include:

**Backend (.env):**
- `MONGODB_URI`: MongoDB connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: JWT secret for authentication
- `OPENAI_API_KEY`: OpenAI API key
- `COHERE_API_KEY`: Cohere API key (if using Cohere)

**Frontend (.env):**
- `VITE_API_URL`: Backend API base URL
- `VITE_APP_TITLE`: Application title

## 🤖 AI Agents and Tools

The system utilizes several AI agents for financial document analysis:

- **Research Analyst**: Analyzes financial documents and extracts key information
- **Financial Advisor**: Provides investment recommendations and risk assessment
- **Market Analyst**: Analyzes market trends and insights
- **Report Generator**: Creates comprehensive analysis reports

Each agent uses specialized tools for:
- PDF document processing
- Web research
- Financial calculations
- Sentiment analysis

## 📊 Data Flow

1. User uploads financial document via frontend or API
2. Document is stored securely and queued for processing
3. AI agents analyze document content using CrewAI framework
4. Analysis results are stored in MongoDB
5. Results are cached in Redis for fast retrieval
6. Frontend displays results in an interactive dashboard

## 🛡️ Security Features

- JWT-based authentication with secure token management
- Role-based access control (Admin, Viewer)
- Input validation and sanitization
- Secure file upload with type and size restrictions
- Rate limiting to prevent abuse
- HTTPS enforcement in production
- Environment variable security

## 🐛 Known Issues and Debugging

This repository contains intentionally planted bugs and inefficiencies as part of a debugging challenge. Key areas to audit:

- Every line of code contains potential bugs
- Performance inefficiencies throughout the codebase
- Security vulnerabilities in authentication and input validation
- Error handling gaps in document processing
- Database query optimizations needed
- Memory management in document processing

## 📈 Performance Optimizations

- Redis caching for frequently accessed data
- Background job processing for document analysis
- Database connection pooling
- Memory-efficient document processing
- Async/await patterns throughout the codebase
- Query optimization and indexing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support, please open an issue in the GitHub repository.
