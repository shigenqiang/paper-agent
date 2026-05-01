.PHONY: test test-api test-server test-e2e test-quick test-verbose clean help
.PHONY: start backend frontend install install-frontend
.PHONY: kill-backend kill-frontend kill-ports
.PHONY: paper topic search docs
.PHONY: docker-build docker-tag-latest docker-login docker-push
.PHONY: ghcr-login ghcr-build ghcr-push ghcr hub

# ============ Config ============
# Port config
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# Docker Hub config (可选)
# 使用: make hub DOCKER_IMAGE_NAME=your-image DOCKER_TAG=v1.0
DOCKER_IMAGE_NAME ?= paper-agent
DOCKER_TAG ?= latest

# GitHub Container Registry config (用于推送 ghcr.io)
# 使用: make ghcr GHCR_USERNAME=xxx GHCR_PAT=xxx
GHCR_USERNAME ?= shigenqiang
GHCR_PAT ?=
GHCR_IMAGE_NAME = ghcr.io/$(GHCR_USERNAME)/paper-agent

# ============ Docker ============

docker-build:
	@echo "Building Docker image $(DOCKER_IMAGE_NAME):$(DOCKER_TAG)..."
	docker build -t $(DOCKER_IMAGE_NAME):$(DOCKER_TAG) .

docker-tag-latest:
	docker tag $(DOCKER_IMAGE_NAME):$(DOCKER_TAG) $(DOCKER_IMAGE_NAME):latest

docker-login:
	@echo "Logging in to Docker Hub..."
	docker login

docker-push: docker-build docker-tag-latest
	@echo "Pushing to Docker Hub..."
	docker push $(DOCKER_IMAGE_NAME):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE_NAME):latest

ghcr-login:
	@echo "Logging in to GitHub Container Registry..."
	@echo "$(GHCR_PAT)" | docker login ghcr.io -u $(GHCR_USERNAME) --password-stdin

ghcr-build:
	@echo "Building Docker image for ghcr.io..."
	docker build -t $(GHCR_IMAGE_NAME):$(DOCKER_TAG) .

ghcr-push:
	@echo "Pushing to GitHub Container Registry..."
	docker push $(GHCR_IMAGE_NAME):$(DOCKER_TAG)
	docker push $(GHCR_IMAGE_NAME):latest

# 一键推送到 GitHub Container Registry
# 必需参数: GHCR_USERNAME, GHCR_PAT
# 示例: make ghcr GHCR_USERNAME=shigenqiang GHCR_PAT=gho_xxxxx
ghcr: ghcr-login ghcr-build ghcr-push

# 一键推送到 Docker Hub
hub: docker-login docker-push

# ============ Start ============

start: kill-ports
	@echo "Starting frontend and backend..."
	@make -j2 backend frontend

backend: kill-backend
	@echo "Starting backend API server (port $(BACKEND_PORT))..."
	python -m src.main

frontend: kill-frontend
	@echo "Starting frontend dev server (port $(FRONTEND_PORT))..."
	cd frontend && npm run dev

# ============ Port Management ============

kill-ports:
	python scripts/kill_ports.py $(BACKEND_PORT) $(FRONTEND_PORT)

kill-backend:
	python scripts/kill_ports.py $(BACKEND_PORT)

kill-frontend:
	python scripts/kill_ports.py $(FRONTEND_PORT)

# ============ Test ============

test:
	python -m pytest tests/test_api_comprehensive.py tests/test_e2e_paper_generation.py -v --tb=short

test-api:
	python -m pytest tests/test_api_comprehensive.py -v --tb=short

test-server:
	python -m pytest tests/test_api_server.py -v -s --tb=short

test-e2e:
	python -m pytest tests/test_e2e_paper_generation.py -v -s --tb=short

test-quick:
	python -m pytest tests/test_api_comprehensive.py tests/test_e2e_paper_generation.py -v --tb=short -x

test-verbose:
	python -m pytest tests/test_api_comprehensive.py tests/test_e2e_paper_generation.py -v -s --tb=long

# ============ Install ============

install:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install-all: install install-frontend

# ============ Tools ============

clean:
	rm -rf .pytest_cache __pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete

# ============ Agent Commands ============

paper:
	python demos/run_full_paper.py "$(TOPIC)"

topic:
	python -c "import asyncio; from demos.run_demo import demo_topic; asyncio.run(demo_topic())"

search:
	python -c "import asyncio; from demos.run_demo import demo_paper_search; asyncio.run(demo_paper_search())"

docs:
	@echo "API文档: http://localhost:8000/docs"
	@start http://localhost:8000/docs 2>nul || open http://localhost:8000/docs 2>nul || echo "请手动打开: http://localhost:8000/docs"

help:
	@echo Available commands:
	@echo(
	@echo   Start:
	@echo     make start           Start frontend and backend
	@echo     make backend         Start backend API server (port 8000)
	@echo     make frontend        Start frontend dev server (port 5173)
	@echo(
	@echo   Agent Commands:
	@echo     make paper TOPIC='topic'  Full paper generation
	@echo     make topic               Topic selection demo
	@echo     make search              Paper search demo
	@echo     make docs                Open API documentation
	@echo(
	@echo   Port management:
	@echo     make kill-ports      Kill processes on ports
	@echo     make kill-backend    Kill process on backend port
	@echo     make kill-frontend   Kill process on frontend port
	@echo(
	@echo   Test:
	@echo     make test            Run all tests
	@echo     make test-api        Run API tests only
	@echo     make test-e2e        Run e2e tests only
	@echo(
	@echo   Install:
	@echo     make install         Install Python dependencies
	@echo     make install-frontend Install frontend dependencies
	@echo(
	@echo   Docker:
	@echo     make ghcr              Push to GitHub Container Registry (一键)
	@echo     make hub              Push to Docker Hub (一键)
	@echo     make docker-build     Build Docker image locally
	@echo     make ghcr-build       Build for ghcr.io
	@echo(
	@echo   Tools:
	@echo     make clean           Clean cache
	@echo     make help            Show this help
