COMPOSE := docker compose

.PHONY: help up down build rebuild restart logs shell ps

help: ## Mostra tutti i comandi disponibili
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Avvia i container in background
	$(COMPOSE) up -d

down: ## Ferma e rimuove i container
	$(COMPOSE) down

build: ## Build dell'immagine
	$(COMPOSE) build

rebuild: build ## Build + down + up: ricostruisce e riavvia tutto da zero
	$(COMPOSE) down
	$(COMPOSE) up -d

restart: ## Restart dei container
	$(COMPOSE) restart

logs: ## Log in tempo reale dell'API
	$(COMPOSE) logs -f appstore-api

shell: ## Shell interattiva nel container API
	$(COMPOSE) exec appstore-api bash

ps: ## Stato dei container
	$(COMPOSE) ps