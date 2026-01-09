# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Microservices-purple)]()
[![Queue](https://img.shields.io/badge/Queue-Celery%20%7C%20Redis-red)]()

**NovelGen-Enterprise (NGE)** 是一款企业级、高可用的长篇小说生成系统。它不仅仅是一个简单的 LLM 包装器，而是一个基于 **LangGraph** 的复杂多智能体协作系统，旨在解决长篇生成中的逻辑连贯性、人物一致性和风格统一性问题。

系统采用 **DeepSeek (逻辑中枢)** 与 **Gemini (文学工匠)** 的双模型架构，结合 **Celery + Redis** 分布式任务队列和 **PostgreSQL (pgvector)** 向量数据库，支持多用户、多项目、多分支的高并发生成。

---

## ✨ 核心特性

### 🧠 深度智能架构
- **双模型协同**: DeepSeek 负责大纲拆解、逻辑审查和剧情推演；Gemini 负责正文撰写、文风模仿和长文本扩写。
- **LangGraph 状态机**: 摒弃简单的线性 Chain，采用循环图结构 (Cyclic Graph)，实现 Plan -> Write -> Review -> Revise 的自我修正循环。
- **RAG 上下文增强**: 基于 pgvector 的语义检索，精准提取与当前场景相关的世界观设定和历史伏笔。

### ⚡ 企业级工程能力
- **分布式任务队列**: 集成 **Celery + Redis**，支持任务持久化、削峰填谷和异步处理，彻底解决长文本生成时的超时和任务丢失问题。
- **实时流式输出 (SSE)**: 支持 Server-Sent Events 协议，实时推送生成过程中的 Token 流和状态变更，提供类似 ChatGPT 的打字机体验。
- **多线剧情分支 (Multi-Branch)**: 支持平行宇宙（IF 线）生成。系统自动维护不同分支的人物状态快照，确保在切换分支时，人物的心情、技能和关系能够正确回溯。
- **全链路可观测**: 详细的日志记录和状态监控，随时掌握每个 Agent 的决策过程。

### 🛠 完善的配套设施
- **RESTful API**: 基于 FastAPI 构建的标准接口，支持 Swagger 文档。
- **可视化 Dashboard**: 提供基于 Vue.js 的管理界面，支持小说管理、大纲编辑、章节预览和生成控制。
- **Docker 化部署**: 提供完整的 Docker Compose 配置，一键拉起所有服务。
- **经典资料库**: 内置修真、赛博朋克、克苏鲁等经典网文设定库，支持 RAG 检索，辅助设定审查与大纲生成。

---

## 🏗 系统架构

```mermaid
graph TD
    User[用户/前端] -->|HTTP Request| API[FastAPI Server]
    User -->|SSE Stream| API
    API -->|Push Task| Redis[Redis Broker]
    API -->|Query| DB[(PostgreSQL)]
    
    Worker[Celery Worker] -->|Pull Task| Redis
    Worker -->|Update State| DB
    Worker -->|Publish Events| Redis
    
    subgraph "LangGraph Engine"
        Worker --> Architect[Architect Agent]
        Worker --> Writer[Writer Agent]
        Worker --> Reviewer[Reviewer Agent]
    end
    
    Architect & Writer & Reviewer -->|LLM Call| Models[Gemini / DeepSeek]
```

---

## 🚀 快速开始

### 前置要求
- **Docker & Docker Compose** (推荐)
- 或本地环境: Python 3.10+, PostgreSQL 16+ (pgvector), Redis 7+

### 方式一：Docker 一键部署 (推荐)

这是最简单的启动方式，适合快速体验和生产部署。

1.  **克隆项目**:
    ```bash
    git clone <repository_url>
    cd NovelGen-Enterprise
    ```

2.  **配置环境变量**:
    ```bash
    cp .env.example .env
    # 编辑 .env 文件，填入你的 API Key (GOOGLE_API_KEY, DEEPSEEK_API_KEY)
    # Docker 模式下，数据库和 Redis 地址通常无需修改
    ```

3.  **启动服务**:
    ```bash
    docker-compose up -d --build
    ```
    该命令将启动以下容器：
    - `app`: FastAPI 后端服务 (Port: 8000)
    - `worker`: Celery 任务执行器
    - `db`: PostgreSQL 数据库 (Port: 5432)
    - `redis`: Redis 消息队列 (Port: 6379)

4.  **访问服务**:
    - Web UI: [http://localhost:8000](http://localhost:8000)
    - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 方式二：本地开发环境搭建

如果你需要修改代码或进行调试，建议搭建本地环境。

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **启动基础设施**:
    确保本地已安装并启动 PostgreSQL 和 Redis。
    ```bash
    # 示例：使用 Docker 仅启动数据库和 Redis
    docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password --name pg vector-pg
    docker run -d -p 6379:6379 --name redis redis
    ```

3.  **配置环境变量**:
    编辑 `.env` 文件，确保数据库和 Redis 连接地址指向本地服务：
    ```ini
    DATABASE_URL=postgresql://postgres:password@localhost:5432/novelgen
    REDIS_URL=redis://localhost:6379/0
    ```

4.  **初始化数据库**:
    ```bash
    python -m src.scripts.migrate_db upgrade
    ```

5.  **启动 Celery Worker**:
    在一个新的终端窗口中运行：
    ```bash
    # Windows
    celery -A src.worker.celery_app worker --loglevel=info --pool=solo

    # Linux/Mac
    celery -A src.worker.celery_app worker --loglevel=info
    ```

6.  **启动 API 服务**:
    在另一个终端窗口中运行：
    ```bash
    python -m src.api.run_server
    ```

---

## 📖 使用指南

### 1. 命令行工具 (CLI)

NGE 提供了强大的 CLI 工具，用于快速测试和批处理。

*   **初始化小说**:
    ```bash
    python -m src.main init ./sample_inputs/novel_setup.txt --title "我的小说"
    ```

*   **生成章节**:
    ```bash
    python -m src.main run --novel-id 1
    ```

*   **切换分支**:
    ```bash
    python -m src.main run --novel-id 1 --branch "if_hero_dies"
    ```

### 2. API 接口

*   **触发生成任务**:
    `POST /generation/`
    ```json
    {
      "novel_id": 1,
      "branch_id": "main"
    }
    ```
    返回 `task_id`。

*   **实时流式订阅**:
    `GET /generation/stream/{task_id}`
    建立 SSE 连接，实时接收 `token` (生成内容) 和 `status` (当前步骤) 事件。

### 3. 资料库管理

*   **导入经典资料**:
    ```bash
    python -m src.scripts.seed_references
    ```
    这将自动导入内置的经典设定（如修真境界、赛博朋克元素等）到向量数据库。

*   **审查设定**:
    ```bash
    python -m src.scripts.review_setup ./sample_inputs/novel_setup.txt
    ```
    系统会自动检索相关资料，提供更专业的修改建议。

---

## 📂 项目结构

```
NovelGen-Enterprise/
├── src/
│   ├── agents/         # 智能体实现 (Architect, Writer, Reviewer...)
│   ├── api/            # FastAPI 路由与应用配置
│   ├── db/             # 数据库模型与迁移脚本
│   ├── services/       # 业务逻辑服务 (Redis Stream, State Loader)
│   ├── config.py       # 全局配置管理
│   ├── graph.py        # LangGraph 状态图定义
│   ├── tasks.py        # Celery 任务定义
│   ├── worker.py       # Celery App 实例
│   └── main.py         # CLI 入口
├── sample_inputs/      # 示例输入文件
├── docker-compose.yml  # 容器编排配置
├── Dockerfile          # 应用镜像构建
├── requirements.txt    # Python 依赖
└── README.md           # 本文档
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！在提交代码前，请确保：
1.  运行了所有单元测试。
2.  代码符合 PEP 8 规范。
3.  新增功能包含相应的文档说明。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
