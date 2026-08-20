# Vedrix Makefile
# Common development and deployment commands

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

.PHONY: help install dev build test lint clean up logs db-migrate db-backup db-restore deploy-staging deploy-prod

# ─────────────────────────────────────────────────────────
# Development Commands
# ─────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "Vedrix Makefile"
	@echo "==============="
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install all dependencies"
	@echo "  make dev            - Start development servers"
	@echo "  make build          - Build frontend for production"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linting"
	@echo ""
	@echo "Database:"
	@echo "  make db-start       - Start PostgreSQL & Redis"
	@echo "  make db-migrate     - Apply PostgreSQL Alembic migrations"
	@echo "  make db-backup      - Backup PostgreSQL database"
	@echo "  make db-restore     - Restore database"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start all services with Docker"
	@echo "  make docker-down    - Stop all services"
	@echo "  make docker-logs    - View logs"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-staging - Deploy to staging"
	@echo "  make deploy-prod    - Deploy to production"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make prune          - Clean up Docker resources"
	@echo ""

install: ## Install all dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@cd backend && pip install -r requirements.txt
	@echo "$(GREEN)Installing frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)Installation complete!$(NC)"

dev: ## Start development servers (requires run_dev.py)
	@echo "$(BLUE)Starting Vedrix development servers...$(NC)"
	@python run_dev.py

build: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)Build complete!$(NC)"

test: ## Run all tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@cd backend && python -m pytest tests/ -v
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd frontend && npm test

lint: ## Run linting
	@echo "$(BLUE)Running backend lint...$(NC)"
	@cd backend && ruff check app/
	@echo "$(BLUE)Running frontend lint...$(NC)"
	@cd frontend && npm run lint

# ─────────────────────────────────────────────────────────
# Database Commands
# ─────────────────────────────────────────────────────────

db-migrate: ## Apply PostgreSQL Alembic migrations
	@echo "$(BLUE)Applying PostgreSQL migrations...$(NC)"
	@./scripts/migrate-postgres.sh

# DATABASE_URL must point to the target PostgreSQL instance. The script does not
# read or import the retired SQLite database.


db-start: ## Start PostgreSQL and Redis with Docker
	@echo "$(BLUE)Starting database services...$(NC)"
	@docker-compose up -d db redis

db-backup: ## Backup PostgreSQL database using DATABASE_URL or the local production container
	@echo "$(YELLOW)Backing up PostgreSQL database...$(NC)"
	@mkdir -p backups
	@if [ -n "$(DATABASE_URL)" ]; then \
		pg_dump --format=custom --file=backups/vedrix_$$(date +%Y%m%d_%H%M%S).dump "$(DATABASE_URL)"; \
	else \
		docker exec vedrix-db-prod pg_dump -U postgres -d vedrix_prod --format=custom > backups/vedrix_$$(date +%Y%m%d_%H%M%S).dump; \
	fi
	@echo "$(GREEN)PostgreSQL backup completed!$(NC)"

db-restore: ## Restore database (requires filename)
	@echo "$(YELLOW)Restoring database...$(NC)"
	@docker exec -i vedrix-db-prod psql -U postgres vedrix_prod < backups/$(FILE)
	@echo "$(GREEN)Database restored!$(NC)"

# ─────────────────────────────────────────────────────────
# Docker Commands
# ─────────────────────────────────────────────────────────

docker-up: ## Start all services with Docker
	@echo "$(BLUE)Starting Docker services...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  Backend: http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Database: localhost:5432"
	@echo "  Redis: localhost:6379"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	@docker-compose down

docker-logs: ## View logs
	@echo "$(BLUE)Viewing logs (Ctrl+C to exit)...$(NC)"
	@docker-compose logs -f

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker-compose build --parallel

# ─────────────────────────────────────────────────────────
# Deployment Commands
# ─────────────────────────────────────────────────────────

deploy-staging: ## Deploy to staging
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	@docker-compose -f docker-compose.staging.yml up -d
	@echo "$(GREEN)Deployed to staging!$(NC)"

deploy-prod: ## Deploy to production
	@echo "$(RED)Deploying to production...$(NC)"
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)Deployed to production!$(NC)"

# ─────────────────────────────────────────────────────────
# Cleanup Commands
# ─────────────────────────────────────────────────────────

clean: ## Remove build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@cd frontend && rm -rf dist node_modules/.vite
	@cd backend && rm -rf __pycache__ .pytest_cache
	@echo "$(GREEN)Cleaned!$(NC)"

prune: ## Clean up Docker resources
	@echo "$(BLUE)Pruning Docker resources...$(NC)"
	@docker system prune -af --volumes
	@echo "$(GREEN)Pruned!$(NC)"

logs: ## View application logs
	@echo "$(BLUE)Viewing application logs...$(NC)"
	@docker-compose logs -f backend

shell-backend: ## Shell into backend container
	@docker exec -it vedrix-backend-prod /bin/bash

shell-db: ## Shell into database container
	@docker exec -it vedrix-db-prod psql -U postgres -d vedrix_prod