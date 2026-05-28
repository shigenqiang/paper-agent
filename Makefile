.PHONY: start backend install clean help
.PHONY: paper topic search docs
.PHONY: docker-build docker-tag-latest docker-login docker-push
.PHONY: ghcr-login ghcr-build ghcr-push ghcr hub
.PHONY: paper-full paper-phase paper-test paper-gen paper-full-hitl
.PHONY: paper-full-test paper-langgraph-test
.PHONY: paper-test-router paper-test-diagnostic paper-test-topic
.PHONY: paper-test-literature paper-test-methodology paper-test-writing
.PHONY: paper-test-polish paper-test-crawler paper-test-selector
.PHONY: paper-test-qa paper-test-all-nodes
.PHONY: qa-service qa-demo auto-improver monitor

# ============ Config ============
BACKEND_PORT = 8000

# Docker Hub config
DOCKER_IMAGE_NAME ?= paper-agent
DOCKER_TAG ?= latest

# GitHub Container Registry config
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

ghcr: ghcr-login ghcr-build ghcr-push
hub: docker-login docker-push

# ============ Start ============

start:
	@echo "Starting backend API server (port $(BACKEND_PORT))..."
	python -m src.main

backend:
	@echo "Starting backend API server (port $(BACKEND_PORT))..."
	python -m src.main

# ============ Install ============

install:
	pip install -e .

# ============ Tools ============

clean:
	rm -rf .pytest_cache __pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete
	rm -rf output/monitoring/*.json output/paper.md

# ============ Agent Commands ============

paper:
	python demos/run_full_paper.py "$(TOPIC)"

topic:
	python -c "import asyncio; from demos.run_demo import demo_topic; asyncio.run(demo_topic())"

# ============ Paper Generation (modular) ============

paper-full:
	python demos/full_paper/runner.py "$(TOPIC)"

paper-full-hitl:
	python demos/full_paper/runner.py "$(TOPIC)" --hitl

paper-phase:
	@python demos/full_paper/test_runner.py $(PHASE)

paper-test:
	python demos/full_paper/test_runner.py --full

paper-full-test:
	cd . && python -m demos.full_paper.test_e2e_workflow

paper-gen:
	cd . && python -m demos.full_paper.runner --paper-only "$(TOPIC)"

paper-langgraph-test:
	cd . && python -m demos.full_paper.test_langgraph

# ============ LangGraph Node Unit Tests ============

paper-test-router:
	cd . && python -m demos.full_paper.test_langgraph --node router

paper-test-diagnostic:
	cd . && python -m demos.full_paper.test_langgraph --node diagnostic

paper-test-topic:
	cd . && python -m demos.full_paper.test_langgraph --node topic

paper-test-literature:
	cd . && python -m demos.full_paper.test_langgraph --node literature

paper-test-methodology:
	cd . && python -m demos.full_paper.test_langgraph --node methodology

paper-test-writing:
	cd . && python -m demos.full_paper.test_langgraph --node writing

paper-test-polish:
	cd . && python -m demos.full_paper.test_langgraph --node polish

paper-test-crawler:
	cd . && python -m demos.full_paper.test_langgraph --node crawler

paper-test-selector:
	cd . && python -m demos.full_paper.test_langgraph --node selector

paper-test-qa:
	cd . && python -m demos.full_paper.test_langgraph --node qa

paper-test-all-nodes:
	cd . && python -m demos.full_paper.test_langgraph --all

# ============ QA & Monitoring ============

qa-service:
	python scripts/start_qa_service.py

qa-demo:
	python -c "import asyncio; from src.agents_v2.qa_service import run_demo; asyncio.run(run_demo())"

auto-improver:
	python scripts/start_auto_improver.py

monitor:
	python -c "import asyncio; from src.agents_v2.monitoring.auto_improver import AutoImprover; asyncio.run(AutoImprover(check_interval=5.0).start())"

# ============ Docs ============

docs:
	@echo "API docs: http://localhost:8000/docs"

help:
	@echo Available commands
	@echo ---
	@echo Start: make start / make backend
	@echo Install: make install
	@echo Paper: make paper TOPIC=... / make paper-full TOPIC=...
	@echo Paper HITL: make paper-full-hitl TOPIC=...
	@echo Paper phases: make paper-phase PHASE=diagnostic
	@echo LangGraph Test: make paper-full-test / make paper-langgraph-test
	@echo Node Tests:
	@echo   make paper-test-router / make paper-test-diagnostic
	@echo   make paper-test-topic / make paper-test-literature
	@echo   make paper-test-methodology / make paper-test-writing
	@echo   make paper-test-polish / make paper-test-crawler
	@echo   make paper-test-selector / make paper-test-qa
	@echo   make paper-test-all-nodes
	@echo QA: make qa-service / make qa-demo
	@echo Monitor: make auto-improver / make monitor
	@echo Docker: make ghcr / make docker-build
	@echo Tools: make clean / make docs
