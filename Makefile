.PHONY: help install dev prod logs stop clean backend-dev frontend-dev

help:
	@echo "SchemaFlow AI - Development Commands"
	@echo "====================================="
	@echo "make dev            - Start development environment"
	@echo "make prod           - Start production environment"
	@echo "make install        - Install all dependencies"
	@echo "make logs           - View Docker logs"
	@echo "make stop           - Stop all services"
	@echo "make clean          - Clean up Docker resources"
	@echo ""

dev:
	@echo "Starting development environment..."
	docker-compose up

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

install: install-backend install-frontend
	@echo "✅ All dependencies installed"

prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up --build -d

logs:
	@docker-compose logs -f

backend-logs:
	@docker-compose logs -f backend

frontend-logs:
	@docker-compose logs -f frontend

stop:
	@echo "Stopping services..."
	docker-compose down

clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f

backend-dev:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm start
