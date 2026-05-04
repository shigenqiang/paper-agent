.PHONY: test test-api test-server test-e2e test-quick test-verbose clean help
.PHONY: start backend frontend install install-frontend
.PHONY: kill-backend kill-frontend kill-ports
.PHONY: paper topic search docs
.PHONY: docker-build docker-tag-latest docker-login docker-push
.PHONY: ghcr-login ghcr-build ghcr-push ghcr hub
.PHONY: paper-full paper-phase paper-test
.PHONY: test-acceptance test-perf test-parallel test-retry
.PHONY: qa-service qa-demo auto-improver monitor
.PHONY: clean paper topic outline draft run

# ============ Config ============
# Port config
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# Docker Hub config (optional)
# Usage: make hub DOCKER_IMAGE_NAME=your-image DOCKER_TAG=v1.0
DOCKER_IMAGE_NAME ?= paper-agent
DOCKER_TAG ?= latest

# GitHub Container Registry config
# Usage: make ghcr GHCR_USERNAME=xxx GHCR_PAT=xxx
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

# Push to GitHub Container Registry
# Required: GHCR_USERNAME, GHCR_PAT
ghcr: ghcr-login ghcr-build ghcr-push

# Push to Docker Hub
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

# ============ Acceptance & Performance Test ============

# Complete acceptance test (9 tests)
test-acceptance:
	python run_acceptance_test.py

# Paper generation performance test (stage timing)
test-perf:
	python test_perf.py

# Parallel chapter generation test
test-parallel:
	python test_parallel_verify.py

# ============ Install ============

install:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install-all: install install-frontend

# ============ QA & Monitoring Services ============

# QA持续问答服务（交互模式）
# 输入问题进行问答，输入 'quit' 退出
qa-service:
	python scripts/start_qa_service.py

# QA服务演示（预设问题循环）
qa-demo:
	python -c "import asyncio; from src.agents_v2.qa_service import run_demo; asyncio.run(run_demo())"

# 监控与自动改进系统
auto-improver:
	python scripts/start_auto_improver.py

# 监控演示模式（短间隔）
monitor:
	python -c "import asyncio; from src.agents_v2.monitoring.auto_improver import AutoImprover; asyncio.run(AutoImprover(check_interval=5.0).start())"

# ============ Autonomous Services (完全自主运行) ============

# QA自主进化系统 - 完全自主运行
# 自己生成问题、搜索文献、构建知识图谱、保存QA库

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

# Full pipeline paper generation (UnifiedWorkflow-based)
# Usage: make paper-full TOPIC="AI in education"
paper-full:
	python demos/full_paper/runner.py "$(TOPIC)"

# Full pipeline + HITL mode
paper-full-hitl:
	python demos/full_paper/runner.py "$(TOPIC)" --hitl

# Test single phase
# Usage: make paper-phase PHASE=diagnostic
paper-phase:
	@python demos/full_paper/test_runner.py $(PHASE)

# Test full flow (old phases mode)
paper-test:
	python demos/full_paper/test_runner.py --full

# Test LangGraph Workflow
paper-full-test:
	cd . && python -m demos.full_paper.test_e2e_workflow

# Paper only (no logs)
# Usage: make paper-gen TOPIC="your topic"
paper-gen:
	cd . && python -m demos.full_paper.runner --paper-only "$(TOPIC)"

# Test LangGraph structure and routing
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

docs:
	@echo "API docs: http://localhost:8000/docs"
	@start http://localhost:8000/docs 2>nul || open http://localhost:8000/docs 2>nul || echo "Manual: http://localhost:8000/docs"

help:
	@echo Available commands
	@echo ---
	@echo Start: make start / make backend / make frontend
	@echo Paper: make paper TOPIC=... / make paper-full TOPIC=...
	@echo Paper HITL: make paper-full-hitl TOPIC=...
	@echo Paper phases: make paper-phase PHASE=diagnostic
	@echo Test: make paper-test / make paper-full TOPIC=...
	@echo LangGraph Test: make paper-full-test / make paper-langgraph-test
	@echo Node Tests:
	@echo   make paper-test-router / make paper-test-diagnostic
	@echo   make paper-test-topic / make paper-test-literature
	@echo   make paper-test-methodology / make paper-test-writing
	@echo   make paper-test-polish / make paper-test-crawler
	@echo   make paper-test-selector / make paper-test-qa
	@echo   make paper-test-all-nodes
	@echo QA & Monitoring:
	@echo   make qa-service    - QA持续问答服务（交互）
	@echo   make qa-demo      - QA服务演示（预设问题）
	@echo   make auto-improver - 监控与自动改进系统
	@echo   make monitor      - 监控演示模式
	@echo Port mgmt: make kill-ports / make kill-backend / make kill-frontend
	@echo Test cmds: make test / make test-api / make test-e2e
	@echo   make test-acceptance / make test-perf
	@echo   make test-parallel / make test-retry
	@echo Docker: make ghcr / make docker-build
	@echo Tools: make clean