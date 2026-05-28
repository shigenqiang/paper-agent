# ============================================
# Paper Agent Dockerfile - 优化版
# 支持多阶段构建、GPU加速、增量更新
# ============================================

# ---- 阶段1: Builder ----
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（优先利用缓存）
COPY pyproject.toml requirements.txt ./

# 安装Python依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- 阶段2: Runtime ----
FROM python:3.11-slim as runtime

# 安全: 创建非root用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# 从builder复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 只复制运行时需要的依赖
# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制源代码（利用Docker缓存）
COPY src/ ./src/
COPY docs/ ./docs/
COPY tests/ ./tests/
COPY readme.md .
COPY config.yaml .
COPY .env.example .env

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HTTP_PROXY=${HTTP_PROXY:-}
ENV HTTPS_PROXY=${HTTPS_PROXY:-}

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认启动命令 - 使用 src.service 入口
CMD ["python", "-m", "src.service"]


# ============================================
# GPU 支持 (可选)
# 使用: docker build -f Dockerfile --target runtime-gpu -t paper-agent:latest .
# ============================================
# ---- 阶段2: GPU Runtime ----
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04 as runtime-gpu

# 设置工作目录
WORKDIR /app

# 安全: 创建非root用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 安装Python和虚拟环境
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制并安装依赖
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY docs/ ./docs/
COPY tests/ ./tests/
COPY readme.md .
COPY config.yaml .
COPY .env.example .env

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HTTP_PROXY=${HTTP_PROXY:-}
ENV HTTPS_PROXY=${HTTPS_PROXY:-}
ENV NVIDIA_VISIBLE_DEVICES=all

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# GPU启动命令 - 使用 src.service 入口
CMD ["python", "-m", "src.service"]


# ============================================
# 轻量级版本 (可选)
# 使用: docker build -f Dockerfile --target runtime-light -t paper-agent:light .
# ============================================
# ---- 阶段2: Light Runtime ----
FROM python:3.11-alpine as runtime-light

WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY pyproject.toml requirements.txt ./

# 只安装核心依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pydantic langchain-core requests && \
    pip cache purge

COPY src/ ./src/
COPY readme.md .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

CMD ["python", "-m", "src.service"]