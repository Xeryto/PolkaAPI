.PHONY: help install run test clean format lint db-init db-migrate

help: ## Show this help message
	@echo "PolkaAPI - Authentication Backend"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Run the development server
	python main.py

run-dev: ## Run the development server with auto-reload
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test: ## Run the API test script
	python test_api.py

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete

format: ## Format code with black and isort
	black .
	isort .

lint: ## Run linting checks
	flake8 .
	mypy .

db-init: ## Initialize database with migrations and sample data
	alembic upgrade head
	python populate_data.py

db-migrate: ## Apply all pending migrations
	alembic upgrade head

db-migration: ## Create new migration (use: make db-migration message='description')
	alembic revision --autogenerate -m "$(message)"

docs: ## Open API documentation in browser
	@echo "Opening API documentation..."
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"
	@echo "Make sure the server is running first!" 