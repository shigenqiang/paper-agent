.PHONY: service install lint clean
.PHONY: test test-all test-01 test-02 test-03 test-04 test-05 test-06 test-07 test-08 test-09 test-10 test-11 test-12 test-13 test-14 test-15
.PHONY: frontend-dev frontend-build frontend-install
.PHONY: up down docker-build docker-push docker-login
.PHONY: ghcr-build ghcr-push ghcr-login ghcr hub
.PHONY: help

# ============ Config ============
PYTHON   ?= D:\anaconda\python.exe
PORT     ?= 8000
IMAGE    ?= paper-agent
TAG      ?= latest
GHCR_USER ?= shigenqiang
GHCR_IMG  = ghcr.io/$(GHCR_USER)/paper-agent

# ============ Service ============

service:
	@$(PYTHON) -c "import subprocess;s=subprocess.run(['netstat','-ano'],capture_output=True,text=True);[subprocess.run(['taskkill','/F','/PID',l.split()[-1]],capture_output=True) for l in s.stdout.splitlines() if ':$(PORT)' in l and 'LISTEN' in l and l.split()[-1].isdigit()]"
	$(PYTHON) -m src.service --port $(PORT)

# ============ API ============

PROJECT  ?= 测试项目
QUERY    ?= sparse functional data
LIMIT    ?= 10

search:
	$(PYTHON) -c "import urllib.request,json,urllib.parse; d=json.dumps({'query':'$(QUERY)','sources':['openalex','arxiv'],'limit':$(LIMIT)}).encode(); p=urllib.parse.quote('$(PROJECT)'); r=urllib.request.Request(f'http://localhost:$(PORT)/api/rw/projects/{p}/papers/search',data=d,headers={'Content-Type':'application/json'}); print(json.dumps(json.loads(urllib.request.urlopen(r).read()),indent=2,ensure_ascii=False))"

projects:
	$(PYTHON) -c "import urllib.request,json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:$(PORT)/api/rw/projects').read()),indent=2,ensure_ascii=False))"

health:
	$(PYTHON) -c "import urllib.request; print(urllib.request.urlopen('http://localhost:$(PORT)/api/health').read().decode())"

# ============ Data ============

migrate:
	$(PYTHON) -m scripts.migrate_storage

migrate-dry-run:
	$(PYTHON) -m scripts.migrate_storage --dry-run

# ============ Frontend ============

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# ============ Dev ============

install:
	$(PYTHON) -m pip install -e .

lint:
	$(PYTHON) -m ruff check src/ --fix

clean:
	rm -rf .pytest_cache __pycache__ src/**/__pycache__ **/__pycache__
	find . -name "*.pyc" -delete
	rm -rf logs/*.log output/monitoring/*.json

# ============ Tests ============
# 通过 run_tests.py 解决 Windows 中文路径编码问题

test: test-all

test-all:
	$(PYTHON) run_tests.py

test-01:
	$(PYTHON) run_tests.py 01

test-02:
	$(PYTHON) run_tests.py 02

test-03:
	$(PYTHON) run_tests.py 03

test-04:
	$(PYTHON) run_tests.py 04

test-05:
	$(PYTHON) run_tests.py 05

test-06:
	$(PYTHON) run_tests.py 06

test-07:
	$(PYTHON) run_tests.py 07

test-08:
	$(PYTHON) run_tests.py 08

test-09:
	$(PYTHON) run_tests.py 09

test-10:
	$(PYTHON) run_tests.py 10

test-11:
	$(PYTHON) run_tests.py 11

test-12:
	$(PYTHON) run_tests.py 12

test-13:
	$(PYTHON) run_tests.py 13

test-14:
	$(PYTHON) run_tests.py 14

test-15:
	$(PYTHON) run_tests.py 15

# ============ Docker Compose ============

up:
	docker-compose up -d --build

down:
	docker-compose down

# ============ Docker ============

docker-build:
	docker build -t $(IMAGE):$(TAG) .

docker-login:
	docker login

docker-push: docker-build
	docker tag $(IMAGE):$(TAG) $(IMAGE):latest
	docker push $(IMAGE):$(TAG)
	docker push $(IMAGE):latest

ghcr-login:
	@echo "$(GHCR_PAT)" | docker login ghcr.io -u $(GHCR_USER) --password-stdin

ghcr-build:
	docker build -t $(GHCR_IMG):$(TAG) .

ghcr-push: ghcr-build
	docker push $(GHCR_IMG):$(TAG)
	docker push $(GHCR_IMG):latest

ghcr: ghcr-login ghcr-push
hub: docker-login docker-push

# ============ Help ============

help:
	@echo "Paper Knowledge-Base Analysis Agent"
	@echo "===================================="
	@echo ""
	@echo "Service:"
	@echo "  make service        启动服务 (端口 $(PORT))"
	@echo ""
	@echo "API:"
	@echo "  make health         健康检查"
	@echo "  make projects       项目列表"
	@echo "  make search         搜索论文 (PROJECT=xxx QUERY=xxx LIMIT=10)"
	@echo ""
	@echo "Data:"
	@echo "  make migrate        迁移平铺 JSON 到项目目录隔离"
	@echo "  make migrate-dry-run 预览迁移（不实际写入）"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install 安装前端依赖"
	@echo "  make frontend-dev     启动前端开发服务器 (端口 3000)"
	@echo "  make frontend-build   构建前端生产包"
	@echo ""
	@echo "Development:"
	@echo "  make install        安装项目依赖"
	@echo "  make lint           代码检查"
	@echo "  make clean          清理缓存和日志"
	@echo ""
	@echo "Tests:"
	@echo "  make test           运行全部测试 (= test-all)"
	@echo "  make test-01        01-核心模型与存储"
	@echo "  make test-02        02-项目服务"
	@echo "  make test-03        03-论文库搜索导入"
	@echo "  make test-04        04-PDF解析与分块"
	@echo "  make test-05        05-论文卡片生成"
	@echo "  make test-06        06-证据表"
	@echo "  make test-07        07-知识图谱"
	@echo "  make test-08        08-RetrievalScope"
	@echo "  make test-09        09-ScopeQA与RAG"
	@echo "  make test-10        10-综述生成"
	@echo "  make test-11        11-创新点报告"
	@echo "  make test-12        12-报告版本与导出"
	@echo "  make test-13        13-LLM提示词与结构化输出"
	@echo "  make test-14        14-API任务与前端联调"
	@echo "  make test-15        15-评估日志监控"
	@echo ""
	@echo "Docker Compose:"
	@echo "  make up              启动所有服务 (docker-compose up -d --build)"
	@echo "  make down            停止所有服务 (docker-compose down)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   构建镜像"
	@echo "  make docker-push    推送到 Docker Hub"
	@echo "  make ghcr           推送到 GitHub Container Registry"
	@echo ""
	@echo "Options:"
	@echo "  PORT=8000           服务端口"
	@echo "  PYTHON=path         Python 路径 (默认 anaconda)"
