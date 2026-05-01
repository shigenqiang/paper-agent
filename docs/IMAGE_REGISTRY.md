# 镜像仓库指南

本文档说明如何将 Docker 镜像推送到不同的镜像仓库。

---

## 1. GitHub Container Registry (ghcr.io)

适合与 GitHub 仓库集成，支持私有/公开镜像。

### 前置条件

1. GitHub 账号
2. 创建 Personal Access Token (PAT):
   - 进入 GitHub → Settings → Developer settings → Personal access tokens
   - 点击 `Generate new token (classic)`
   - 勾选 `write:packages` 权限
   - 复制生成的 token（以 `ghp_` 或 `gho_` 开头）

### 使用方式

```bash
# 一键推送（替换为你的用户名和 PAT）
make ghcr GHCR_USERNAME=shigenqiang GHCR_PAT=gho_xxxxx

# 指定版本
make ghcr GHCR_USERNAME=shigenqiang GHCR_PAT=gho_xxxxx DOCKER_TAG=v1.0
```

### 查看镜像

镜像地址: `ghcr.io/shigenqiang/paper-agent`

访问 GitHub 仓库的 Packages 页面:
```
https://github.com/shigenqiang/paper-agent/pkgs/container/paper-agent
```

### 拉取镜像

```bash
# 需要先登录
echo "YOUR_PAT" | docker login ghcr.io -u USERNAME --password-stdin

# 拉取
docker pull ghcr.io/shigenqiang/paper-agent:latest
```

---

## 2. Docker Hub

适合开源项目，公共镜像免费。

### 前置条件

1. Docker Hub 账号
2. 创建 Repository（可选，也可以在推送时自动创建）

### 使用方式

```bash
# 登录（会提示输入用户名密码）
make docker-login

# 推送
make hub DOCKER_IMAGE_NAME=shigenqiang/paper-agent DOCKER_TAG=v1.0

# 也可以手动登录后推送
docker login
docker build -t paper-agent:latest .
docker tag paper-agent:latest shigenqiang/paper-agent:v1.0
docker push shigenqiang/paper-agent:v1.0
```

### 查看镜像

登录 https://hub.docker.com 查看你的仓库。

### 拉取镜像

```bash
docker pull shigenqiang/paper-agent:latest
```

---

## 3. 使用配置文件（推荐）

为避免每次手动输入敏感信息，可以创建配置文件：

### .env 文件

```bash
# .env (添加到 .gitignore)
GHCR_USERNAME=shigenqiang
GHCR_PAT=your_github_pat_here
DOCKER_HUB_USERNAME=your_dockerhub_username
```

### Makefile 支持

```bash
# 从 .env 读取变量
make ghcr

# 或指定变量
make hub DOCKER_IMAGE_NAME=xxx
```

---

## 4. 镜像使用示例

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  paper-agent:
    image: ghcr.io/shigenqiang/paper-agent:latest
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=your_key
    restart: unless-stopped
```

### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paper-agent
spec:
  containers:
    - name: paper-agent
      image: ghcr.io/shigenqiang/paper-agent:latest
      ports:
        - containerPort: 8000
      env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
```

### 直接运行

```bash
# ghcr.io
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  ghcr.io/shigenqiang/paper-agent:latest

# Docker Hub
docker run -d -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  shigenqiang/paper-agent:latest
```

---

## 5. 维护

### 清理本地镜像

```bash
# 查看镜像
docker images

# 删除
docker rmi paper-agent:latest
docker rmi ghcr.io/shigenqiang/paper-agent:latest
```

### 更新镜像版本

```bash
# 重新构建并推送
make ghcr DOCKER_TAG=v1.1 GHCR_PAT=xxx
```

---

## 6. 权限说明

| 仓库 | 公开可见 | 私有可见 |
|------|---------|---------|
| ghcr.io | 仓库 owner 可见 | 需要登录 |
| Docker Hub | 所有人可见 | 需要登录 |