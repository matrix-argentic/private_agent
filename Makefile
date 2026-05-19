PORT            ?= 8001
RAG_WEB_DIR     = web/rag
UV              = uv run python main.py

.PHONY: help mineru-build mineru-up mineru-down mineru-logs server rag-web retrieve chat test test-all test-integration milvus-up milvus-down milvus-logs langfuse-up langfuse-down langfuse-logs all

help: ## Show this help
	@echo "Usage: make <target>"
	@echo ""
	@sed -n 's/^\([a-z_-]*\):.*##\(.*\)/\1\t\2/p' $(MAKEFILE_LIST) | column -t -s $$'\t'

# ── MinerU ──────────────────────────────────────────────────────────────────

DOCKER_COMPOSE_MINERU  = docker compose -f docker/mineru/docker-compose.yaml
MINERU_DF_URL   = https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/docker/china/Dockerfile

mineru-build: ## Build MinerU Docker image (mineru:latest)
	curl -sL $(MINERU_DF_URL) -o docker/mineru/Dockerfile
	docker build -t mineru:latest -f docker/mineru/Dockerfile docker/mineru
	@echo "MinerU image built: mineru:latest"

mineru-up: ## Start MinerU PDF parsing service
	$(DOCKER_COMPOSE_MINERU) up -d mineru-api
	@echo "MinerU API: http://localhost:8000"

mineru-down: ## Stop MinerU service
	$(DOCKER_COMPOSE_MINERU) down

mineru-logs: ## Tail MinerU logs
	$(DOCKER_COMPOSE_MINERU) logs -f mineru-api

# ── Milvus ───────────────────────────────────────────────────────────────────

DOCKER_COMPOSE_MILVUS = docker compose -f docker/milvus/docker-compose.yaml

milvus-up: ## Start Milvus vector database (standalone + etcd + minio + attu)
	$(DOCKER_COMPOSE_MILVUS) up -d
	@echo "Milvus:      port 19530"
	@echo "Attu (Web):  http://localhost:3001"
	@echo "MinIO Admin: http://localhost:9001"

milvus-down: ## Stop Milvus service
	$(DOCKER_COMPOSE_MILVUS) down

milvus-logs: ## Tail Milvus logs
	$(DOCKER_COMPOSE_MILVUS) logs -f standalone

# ── Langfuse ─────────────────────────────────────────────────────────────────

DOCKER_COMPOSE_LANGFUSE = docker compose -f docker/langfuse/docker-compose.yaml

langfuse-up: ## Start Langfuse observability platform
	$(DOCKER_COMPOSE_LANGFUSE) up -d
	@echo "Langfuse Web: http://localhost:3000"

langfuse-down: ## Stop Langfuse service
	$(DOCKER_COMPOSE_LANGFUSE) down

langfuse-logs: ## Tail Langfuse logs
	$(DOCKER_COMPOSE_LANGFUSE) logs -f langfuse-web

# ── Server ───────────────────────────────────────────────────────────────────

server: ## Start HTTP server (default port 8001)
	$(UV) server --port $(PORT)

rag-web: ## Start RAG frontend (Next.js dev server)
	cd $(RAG_WEB_DIR) && pnpm dev

retrieve: ## Retrieve docs (usage: make retrieve query="你的问题")
	$(UV) retrieve -q "$(query)"

chat: ## Chat (usage: make chat query="你的问题")
	$(UV) chat -q "$(query)"

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run unit tests (skip integration)
	uv run pytest -v

test-all: ## Run ALL tests including integration
	uv run pytest -v -m ''

test-integration: ## Run integration tests only
	uv run pytest -v -m integration

# ── All ──────────────────────────────────────────────────────────────────────

all: mineru-up server ## Start MinerU + HTTP server
