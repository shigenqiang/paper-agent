.PHONY: service test install lint clean
.PHONY: docker-build docker-push docker-login
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

# ============ Dev ============

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ --fix

clean:
	rm -rf .pytest_cache __pycache__ src/**/__pycache__ **/__pycache__
	find . -name "*.pyc" -delete
	rm -rf logs/*.log output/monitoring/*.json

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
	@echo "Development:"
	@echo "  make install        安装项目依赖"
	@echo "  make test           运行测试"
	@echo "  make lint           代码检查"
	@echo "  make clean          清理缓存和日志"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   构建镜像"
	@echo "  make docker-push    推送到 Docker Hub"
	@echo "  make ghcr           推送到 GitHub Container Registry"
	@echo ""
	@echo "Options:"
	@echo "  PORT=8000           服务端口"
	@echo "  PYTHON=path         Python 路径 (默认 anaconda)"
