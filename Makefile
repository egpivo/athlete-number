SHELL := /bin/bash
EXECUTABLE := poetry run

.PHONY: clean install test-coverage start-service

# Clean up unnecessary files
clean:
	@echo -e "\033[1;90mCleaning up...\033[0m"
	@find . -type f -name '*.py[co]' -delete
	@find . -type d -name __pycache__ -delete
	@find . -type d -name .ipynb_checkpoints -exec rm -rf {} +
	@rm -rf build/ dist/ .eggs/
	@find . -name '*.egg-info' -exec rm -rf {} +
	@rm -f .coverage*
	@rm -rf .pytest_cache
	@rm -rf htmlcov/ coverage.xml

# Install dependencies using Poetry
install:
	@echo -e "\033[1;92mInstalling dependencies...\033[0m"
	@poetry install

# Run tests with coverage
test-coverage:
	@echo -e "\033[1;92mRunning tests with coverage...\033[0m"
	@$(EXECUTABLE) pytest --cov=file_translator --cov-report=term-missing

# Start the FastAPI service
start-service: install
	@echo -e "\033[1;92mStarting the FastAPI service in development mode...\033[0m"
	@$(EXECUTABLE) uvicorn athlete_number.main:app --host 0.0.0.0 --port 5566 --reload

# Start the FastAPI service (production mode with Gunicorn)
start-production: install
	@echo -e "\033[1;92mStarting the FastAPI service in production mode...\033[0m"
	@./scripts/start.sh
