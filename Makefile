.PHONY: test test-api test-server test-e2e test-quick test-verbose clean help
.PHONY: start backend frontend install install-frontend
.PHONY: kill-backend kill-frontend kill-ports
.PHONY: paper topic search docs
.PHONY: docker-build docker-tag-latest docker-login docker-push
.PHONY: ghcr-login ghcr-build ghcr-push ghcr hub
.PHONY: paper-full paper-phase paper-test

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

# ============ Paper Generation (模块化) ============

# 全链路论文生成 (基于 UnifiedWorkflow)
# 用法: make paper-full TOPIC="人工智能在教育领域"
paper-full:
	python demos/full_paper/runner.py "$(TOPIC)"

# 全链路论文生成 + HITL 模式
# 触发 HITL 时会暂停等待人工介入
paper-full-hitl:
	python demos/full_paper/runner.py "$(TOPIC)" --hitl

# 测试单个阶段
# 用法: make paper-phase PHASE=diagnostic
paper-phase:
	@python demos/full_paper/test_runner.py $(PHASE)

# 测试完整流程（使用旧的 phases 模式）
paper-test:
	python demos/full_paper/test_runner.py --full

# 测试 LangGraph Workflow（全链路单元测试）
# 运行 test_e2e_workflow.py 验证工作流结构和节点
paper-full-test:
	cd . && python -m demos.full_paper.test_e2e_workflow

# 测试 LangGraph Workflow 结构和边路由
paper-langgraph-test:
	cd . && python -m demos.full_paper.test_langgraph

# ============ LangGraph Node 单元测试 ============
# 测试各个节点的独立功能

# 路由节点测试
paper-test-router:
	cd . && python -m demos.full_paper.test_langgraph --node router

# 诊断节点测试
paper-test-diagnostic:
	cd . && python -m demos.full_paper.test_langgraph --node diagnostic

# 选题节点测试
paper-test-topic:
	cd . && python -m demos.full_paper.test_langgraph --node topic

# 文献节点测试
paper-test-literature:
	cd . && python -m demos.full_paper.test_langgraph --node literature

# 方法论节点测试
paper-test-methodology:
	cd . && python -m demos.full_paper.test_langgraph --node methodology

# 写作节点测试
paper-test-writing:
	cd . && python -m demos.full_paper.test_langgraph --node writing

# 润色节点测试
paper-test-polish:
	cd . && python -m demos.full_paper.test_langgraph --node polish

# 爬虫节点测试
paper-test-crawler:
	cd . && python -m demos.full_paper.test_langgraph --node crawler

# 选择器节点测试
paper-test-selector:
	cd . && python -m demos.full_paper.test_langgraph --node selector

# QA 节点测试
paper-test-qa:
	cd . && python -m demos.full_paper.test_langgraph --node qa

# 运行所有 LangGraph Node 单元测试
paper-test-all-nodes:
	cd . && python -m demos.full_paper.test_langgraph --all

docs:
	@echo "API文档: http://localhost:8000/docs"
	@start http://localhost:8000/docs 2>nul || open http://localhost:8000/docs 2>nul || echo "请手动打开: http://localhost:8000/docs"

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
	@echo Port mgmt: make kill-ports / make kill-backend / make kill-frontend
	@echo Test cmds: make test / make test-api / make test-e2e
	@echo Docker: make ghcr / make docker-build
	@echo Tools: make clean
