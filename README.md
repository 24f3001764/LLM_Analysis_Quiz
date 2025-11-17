---
title: LLM_Analysis_Quiz
emoji: 👁
colorFrom: purple
colorTo: green
sdk: docker
pinned: false
---

# LLM Analysis Quiz

A FastAPI application for analyzing and processing quizzes using Playwright.

## 🚀 Features

- **FastAPI** for high-performance API endpoints
- **Playwright** for browser automation
- **Docker** containerization for easy deployment
- **Logging** with rotation and different log levels
- **Health checks** for monitoring
- **Environment-based configuration**
- **API documentation** with Swagger UI and ReDoc

## 🛠 Prerequisites

- Python 3.9+
- [Poetry](https://python-poetry.org/) for dependency management
- Docker (for containerized deployment)
- Playwright browsers (installed automatically)

## 🏗 Local Development

### Option 1: Using Poetry (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd llm-analysis-quiz
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Install Playwright browsers**:
   ```bash
   poetry run playwright install --with-deps
   ```

4. **Create a `.env` file** (copy from `.env.example` if available):
   ```env
   DEBUG=True
   ENVIRONMENT=development
   SECRET_KEY=your-secret-key
   QUIZ_SECRET=your-quiz-secret
   ```

5. **Run the application**:
   ```bash
   poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Option 2: Using Docker

1. **Build the Docker image**:
   ```bash
   docker build -t llm-quiz .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 --env-file .env llm-quiz
   ```

## 🌐 API Documentation

Once the application is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

Run tests with:
```bash
poetry run pytest
```

## 📦 Deployment

### Hugging Face Spaces

1. Push your code to a Git repository
2. Create a new Space on Hugging Face
3. Configure the Space:
   - Select "Docker" as the Space SDK
   - Set the Dockerfile path to `Dockerfile`
   - Set the port to `8000`
   - Set the health check path to `/health`
   - Add required environment variables in the Space settings

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `ENVIRONMENT` | `production` | Application environment |
| `SECRET_KEY` | - | Secret key for security |
| `QUIZ_SECRET` | - | Secret for quiz authentication |
| `HOST` | `0.0.0.0` | Host to bind to |
| `PORT` | `8000` | Port to listen on |

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Logs**: Stored in `/app/logs/` in the container

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
