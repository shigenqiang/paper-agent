# Paper Agent - 统一管理

## 快速开始

### 安装 make（可选）

```bash
choco install make
```

### 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

## 启动服务

### 方式一：使用 Makefile

```bash
make start           # 同时启动前端和后端
make backend         # 只启动后端 (:8000)
make frontend        # 只启动前端 (:5173)
```

### 方式二：使用 Python 脚本

```bash
python tests/run_all_tests.py start        # 同时启动前端和后端
python tests/run_all_tests.py backend      # 只启动后端
python tests/run_all_tests.py frontend     # 只启动前端
```

### 方式三：手动启动

```bash
# 终端 1：启动后端
python -m src.main

# 终端 2：启动前端
cd frontend && npm run dev
```

## 运行测试

### 方式一：使用 Makefile

```bash
make test            # 运行所有测试
make test-api        # 只运行 API 测试
make test-e2e        # 只运行端到端测试
make test-quick      # 快速测试（遇错即停）
make test-verbose    # 详细输出
```

### 方式二：使用 Python 脚本

```bash
python tests/run_all_tests.py test         # 运行所有测试
python tests/run_all_tests.py test-api     # 只运行 API 测试
python tests/run_all_tests.py test-e2e     # 只运行端到端测试
python tests/run_all_tests.py test-quick   # 快速测试
```

### 方式三：直接用 pytest

```bash
python -m pytest tests/test_api_comprehensive.py tests/test_e2e_paper_generation.py -v
```

## 命令对照表

| 功能 | Makefile | Python 脚本 |
|------|----------|------------|
| 同时启动前后端 | `make start` | `python tests/run_all_tests.py start` |
| 启动后端 | `make backend` | `python tests/run_all_tests.py backend` |
| 启动前端 | `make frontend` | `python tests/run_all_tests.py frontend` |
| 运行所有测试 | `make test` | `python tests/run_all_tests.py test` |
| API 测试 | `make test-api` | `python tests/run_all_tests.py test-api` |
| 端到端测试 | `make test-e2e` | `python tests/run_all_tests.py test-e2e` |
| 快速测试 | `make test-quick` | `python tests/run_all_tests.py test-quick` |
| 清理缓存 | `make clean` | - |

## 测试覆盖范围

| 测试文件 | 测试数 | 说明 |
|---------|:------:|------|
| `test_api_comprehensive.py` | 28 | API 接口单元测试 |
| `test_e2e_paper_generation.py` | 11 | 端到端论文生成全链路测试 |

## 端到端测试流程

```
输入: 论文主题
  │
  ├─ Step 1: OutlineAgent 生成大纲
  ├─ Step 2: DraftWriterAgent 逐章生成草稿
  ├─ Step 3: LanguagePolisherAgent 润色各章
  └─ 输出: 完整论文
```
