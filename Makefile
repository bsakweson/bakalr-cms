.PHONY: help install setup migrate run-backend run-frontend run dev stop clean test lint format docker-up docker-down docker-logs check-docker install-docker seed seed-reset

# Default target
help:
	@echo "Bakalr CMS - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install        - Install all dependencies (backend + frontend)"
	@echo "  make setup          - Complete setup (install + migrate)"
	@echo "  make migrate        - Run database migrations"
	@echo "  make check-docker   - Check if Docker and Docker Compose are installed"
	@echo "  make install-docker - Show instructions to install Docker"
	@echo ""
	@echo "Development:"
	@echo "  make run            - Run full stack (backend + frontend)"
	@echo "  make dev            - Alias for 'make run'"
	@echo "  make run-backend    - Run backend only (port 8000)"
	@echo "  make run-frontend   - Run frontend only (port 3000)"
	@echo "  make stop           - Stop all running servers"
	@echo ""
	@echo "Database & Seeding:"
	@echo "  make seed           - Seed sample data (keeps existing data)"
	@echo "  make seed-reset     - Reset and reseed all content data"
	@echo "  make reset-db       - Reset entire database (WARNING: deletes all data)"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           - Run all tests"
	@echo "  make test-backend   - Run backend tests only"
	@echo "  make test-frontend  - Run frontend tests only"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code (black + prettier)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start all services with Docker Compose"
	@echo "  make docker-down    - Stop Docker services"
	@echo "  make docker-logs    - View Docker logs"
	@echo "  make docker-build   - Rebuild Docker images"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean cache and temp files"

# Installation
install:
	@echo "📦 Installing backend dependencies..."
	@poetry install
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "✅ All dependencies installed"

# Complete setup
setup: install migrate
	@echo "✅ Setup complete! Run 'make run' to start the app"

# Database migrations
migrate:
	@echo "🗄️  Running database migrations..."
	@poetry run alembic upgrade head
	@echo "✅ Migrations complete"

# Run backend
run-backend:
	@echo "🚀 Starting backend server on http://localhost:8000..."
	@echo "📚 API docs: http://localhost:8000/api/docs"
	@poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
run-frontend:
	@echo "🚀 Starting frontend server on http://localhost:3000..."
	@cd frontend && npm run dev

# Run both (requires tmux or run in separate terminals)
run:
	@echo "🚀 Starting full stack..."
	@echo "⚠️  Note: This will run in foreground. Use 'make docker-up' for background or run in separate terminals:"
	@echo "   Terminal 1: make run-backend"
	@echo "   Terminal 2: make run-frontend"
	@echo ""
	@echo "Starting backend..."
	@make run-backend

dev: run

# Stop servers
stop:
	@echo "🛑 Stopping servers..."
	@-lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@-lsof -ti:3000 | xargs kill -9 2>/dev/null || true
	@echo "✅ Servers stopped"

# Testing
test:
	@echo "🧪 Running all tests..."
	@make test-backend
	@make test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	@poetry run pytest -v

test-frontend:
	@echo "🧪 Running frontend tests..."
	@cd frontend && npm test

# Code quality
lint:
	@echo "🔍 Running linters..."
	@poetry run flake8 backend
	@cd frontend && npm run lint

format:
	@echo "✨ Formatting code..."
	@poetry run black backend
	@cd frontend && npm run format 2>/dev/null || echo "⚠️  Frontend format script not found"

# Check Docker installation
check-docker:
	@echo "🔍 Checking Docker installation..."
	@command -v docker >/dev/null 2>&1 && echo "✅ Docker is installed: $$(docker --version)" || echo "❌ Docker is not installed"
	@command -v docker-compose >/dev/null 2>&1 && echo "✅ Docker Compose is installed: $$(docker-compose --version)" || echo "❌ Docker Compose is not installed"
	@if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then \
		echo ""; \
		echo "✅ All Docker components are ready!"; \
		echo "   Run 'make docker-up' to start services"; \
	else \
		echo ""; \
		echo "⚠️  Run 'make install-docker' for installation instructions"; \
	fi

# Docker installation instructions
install-docker:
	@echo "🐳 Docker Installation Instructions"
	@echo ""
	@echo "macOS:"
	@echo "  1. Download Docker Desktop: https://www.docker.com/products/docker-desktop"
	@echo "  2. Install and start Docker Desktop"
	@echo "  3. Docker Compose is included with Docker Desktop"
	@echo ""
	@echo "  Or using Homebrew:"
	@echo "     brew install --cask docker"
	@echo ""
	@echo "Linux (Ubuntu/Debian):"
	@echo "  # Install Docker"
	@echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
	@echo "  sudo sh get-docker.sh"
	@echo "  sudo usermod -aG docker \$$USER"
	@echo ""
	@echo "  # Install Docker Compose"
	@echo "  sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$$(uname -s)-\$$(uname -m)\" -o /usr/local/bin/docker-compose"
	@echo "  sudo chmod +x /usr/local/bin/docker-compose"
	@echo ""
	@echo "After installation, run 'make check-docker' to verify"

# Docker commands
docker-up: check-docker
	@if command -v docker-compose >/dev/null 2>&1; then \
		echo "🐳 Starting Docker services..."; \
		docker-compose up -d; \
		echo "✅ Services starting..."; \
		echo "   Backend:  http://localhost:8000"; \
		echo "   Frontend: http://localhost:3000"; \
		echo "   API Docs: http://localhost:8000/api/docs"; \
	else \
		echo "❌ Docker Compose not found. Run 'make install-docker' for instructions"; \
		exit 1; \
	fi

docker-down:
	@echo "🐳 Stopping Docker services..."
	@docker-compose down

docker-logs:
	@docker-compose logs -f

docker-build:
	@echo "🐳 Building Docker images..."
	@docker-compose build

# Utilities
clean:
	@echo "🧹 Cleaning cache and temp files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@cd frontend && rm -rf .next node_modules/.cache 2>/dev/null || true
	@echo "✅ Cleaned"

reset-db:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🗄️  Resetting database..."; \
		rm -f bakalr_cms.db; \
		poetry run alembic upgrade head; \
		echo "✅ Database reset complete"; \
	else \
		echo "❌ Cancelled"; \
	fi

# Seeding
seed:
	@echo "🌱 Seeding sample data..."
	@echo "   (Requires SEED_ADMIN_PASSWORD environment variable)"
	@poetry run python seeds/seed_runner.py
	@echo "✅ Seeding complete"

seed-reset:
	@echo "🌱 Resetting and reseeding all content data..."
	@echo "   (Requires SEED_ADMIN_PASSWORD environment variable)"
	@poetry run python seeds/seed_runner.py --reset
	@echo "✅ Reset and seeding complete"
