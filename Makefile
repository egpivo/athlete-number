SHELL := /bin/bash

.PHONY: build start logs stop restart clean

# Build and start the services
build:
	@echo -e "\033[1;92mBuilding and starting Docker Compose services...\033[0m"
	@docker compose up --build -d

# Start services (without rebuilding)
start:
	@echo -e "\033[1;92mStarting Docker Compose services...\033[0m"
	@docker compose up -d

# Check logs of running services
logs:
	@echo -e "\033[1;93mShowing logs for Docker Compose services...\033[0m"
	@docker compose logs -f

# Stop services
stop:
	@echo -e "\033[1;91mStopping Docker Compose services...\033[0m"
	@docker compose down

# Restart services (stop & start)
restart: stop start

# Clean up stopped containers and unused images
clean:
	@echo -e "\033[1;91mCleaning up unused Docker resources...\033[0m"
	@docker system prune -af
