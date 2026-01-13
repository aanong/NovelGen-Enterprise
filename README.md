# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Microservices-purple)]()
[![Queue](https://img.shields.io/badge/Queue-Celery%20%7C%20Redis-red)]()

**NovelGen-Enterprise (NGE)** 是一款企业级、高可用的长篇小说生成系统。它不仅仅是一个简单的 LLM 包装器，而是一个基于 **LangGraph** 的复杂多智能体协作系统，旨在解决长篇生成中的逻辑连贯性、人物一致性和风格统一性问题。

系统采用 **DeepSeek (逻辑中枢)** 与 **Gemini (文学工匠)** 的双模型架构，结合 **Celery + Redis** 分布式任务队列和 **PostgreSQL (pgvector)** 向量数据库，支持多用户、多项目、多分支的高并发生成。

---

## 📋 目录

- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
  - [前置要求](#前置要求)
  - [方式一：Docker 一键部署（推荐）](#方式一docker-一键部署推荐)
  - [方式二：本地开发环境搭建](#方式二本地开发环境搭建)
- [数据库初始化](#-数据库初始化)
- [数据初始化](#-数据初始化)
  - [导入小说设定](#1-导入小说设定)
  - [导入资料库](#2-导入资料库)
- [配置说明](#-配置说明)
- [使用指南](#-使用指南)
  - [命令行工具 (CLI)](#1-命令行工具-cli)
  - [API 接口](#2-api-接口)
  - [Web 界面](#3-web-界面)
- [项目结构](#-项目结构)
- [常见问题](#-常见问题)
- [开发指南](#-开发指南)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## ✨ 核心特性

### 🧠 深度智能架构
- **双模型协同**: DeepSeek 负责大纲拆解、逻辑审查和剧情推演；Gemini 负责正文撰写、文风模仿和长文本扩写。
- **LangGraph 状态机**: 摒弃简单的线性 Chain，采用循环图结构 (Cyclic Graph)，实现 Plan -> Write -> Review -> Revise 的自我修正循环。
- **RAG 上下文增强**: 基于 pgvector 的语义检索，精准提取与当前场景相关的世界观设定和历史伏笔。
- **Antigravity Rules**: 内置反重力规则系统，防止人物 OOC、逻辑硬伤和世界观崩坏。

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
        Worker --> Evolver[Evolver Agent]
    end
    
    Architect & Writer & Reviewer -->|LLM Call| Models[Gemini / DeepSeek]
    DB -->|Vector Search| RAG[RAG Engine]
```

---

## 🚀 快速开始

### 前置要求

#### Docker 部署（推荐）
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **至少 4GB 可用内存**

#### 本地开发环境
- **Python** 3.10+
- **PostgreSQL** 16+ (需安装 pgvector 扩展)
- **Redis** 7+
- **Git**

---

### 方式一：Docker 一键部署（推荐）

这是最简单的启动方式，适合快速体验和生产部署。

#### 步骤 1: 克隆项目

```bash
git clone https://github.com/aanong/NovelGen-Enterprise.git
cd NovelGen-Enterprise
```

#### 步骤 2: 配置环境变量

创建 `.env` 文件：

```bash
# 复制示例配置（如果存在）
# cp .env.example .env

# 或直接创建 .env 文件
cat > .env << EOF
# LLM API Keys (必需)
GOOGLE_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 数据库配置
POSTGRES_URL=postgresql://postgres:password@db:5432/novelgen
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=novelgen

# Redis 配置
REDIS_URL=redis://redis:6379/0

# 模型配置（可选，使用默认值）
GEMINI_MODEL=models/gemini-3-pro-preview
GEMINI_TEMPERATURE=0.8
DEEPSEEK_MODEL=deepseek-r1:7b

# 写作配置（可选）
MIN_CHAPTER_LENGTH=2000
TARGET_CHAPTER_LENGTH=3000
MAX_RETRY_LIMIT=3

# 数据库连接池（可选）
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
EOF
```

**重要**: 请将 `your_gemini_api_key_here` 和 `your_deepseek_api_key_here` 替换为你的实际 API Key。

#### 步骤 3: 启动服务

```bash
docker-compose up -d --build
```

该命令将启动以下容器：
- `novelgen-app`: FastAPI 后端服务 (Port: 8000)
- `novelgen-worker`: Celery 任务执行器
- `novelgen-db`: PostgreSQL 数据库 (Port: 5432)
- `novelgen-redis`: Redis 消息队列 (Port: 6379)

#### 步骤 4: 检查服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

#### 步骤 5: 初始化数据库

```bash
# 进入应用容器
docker-compose exec app python -m src.db.init_db

# 或使用迁移脚本（推荐）
docker-compose exec app python -m src.scripts.migrate_db upgrade
```

#### 步骤 6: 访问服务

- **Web UI**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **健康检查**: [http://localhost:8000/health](http://localhost:8000/health)

---

### 方式二：本地开发环境搭建

如果你需要修改代码或进行调试，建议搭建本地环境。

#### 步骤 1: 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 步骤 2: 启动基础设施

**选项 A: 使用 Docker 启动数据库和 Redis（推荐）**

```bash
# 仅启动数据库和 Redis
docker-compose up -d db redis
```

**选项 B: 本地安装 PostgreSQL 和 Redis**

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-16 postgresql-contrib redis-server

# macOS (使用 Homebrew)
brew install postgresql@16 redis

# 启动服务
# PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@16  # macOS

# Redis
sudo systemctl start redis  # Linux
brew services start redis  # macOS
```

**安装 pgvector 扩展**

```bash
# 连接到 PostgreSQL
psql -U postgres -d novelgen

# 在 psql 中执行
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

#### 步骤 3: 配置环境变量

创建 `.env` 文件：

```bash
# LLM API Keys
GOOGLE_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 数据库配置（本地）
POSTGRES_URL=postgresql://postgres:password@localhost:5432/novelgen

# Redis 配置（本地）
REDIS_URL=redis://localhost:6379/0

# 其他配置...
```

#### 步骤 4: 初始化数据库

```bash
# 创建数据库
createdb novelgen  # 或使用 psql

# 初始化表结构
python -m src.db.init_db

# 或使用迁移脚本
python -m src.scripts.migrate_db upgrade
```

#### 步骤 5: 启动服务

**终端 1: 启动 Celery Worker**

```bash
# Windows
celery -A src.worker.celery_app worker --loglevel=info --pool=solo

# Linux/Mac
celery -A src.worker.celery_app worker --loglevel=info
```

**终端 2: 启动 API 服务**

```bash
python -m src.api.run_server
# 或使用 uvicorn
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🗄 数据库初始化

### 自动初始化（推荐）

```bash
# Docker 环境
docker-compose exec app python -m src.db.init_db

# 本地环境
python -m src.db.init_db
```

### 手动初始化

如果需要删除所有表重新创建（**慎用！会丢失所有数据**）：

```bash
python -m src.db.init_db --drop
```

### 使用迁移脚本

```bash
# 升级数据库
python -m src.scripts.migrate_db upgrade

# 回滚（谨慎使用）
python -m src.scripts.migrate_db downgrade
```

### 验证数据库

```bash
# 检查数据库连接
python -c "from src.db.base import engine; print(engine.url)"

# 验证表结构
python -m src.scripts.verify_db
```

---

## 📚 数据初始化

### 1. 导入小说设定

#### 准备设定文档

创建一个文本文件，包含小说的基本设定。参考 `sample_inputs/novel_setup.txt`：

```text
# 小说大纲 (Plot Timeline)

### 第一阶段：微末崛起
主角从平凡开始，经历各种挑战...

## 主要人物 (Characters)

### 主角
- **定位**：男主角
- **核心能力**：...
- **性格**：...

## 世界观与势力 (World & Factions)

### 核心设定
...

## 文风要求 (Style Preference)
- **基调**：...
```

#### 导入设定

**创建新小说并导入设定：**

```bash
# 使用 CLI
python -m src.main init ./sample_inputs/novel_setup.txt \
    --title "我的小说" \
    --author "作者名" \
    --description "小说描述"

# Docker 环境
docker-compose exec app python -m src.main init ./sample_inputs/novel_setup.txt \
    --title "我的小说" \
    --author "作者名"
```

**更新现有小说：**

```bash
python -m src.main init ./sample_inputs/novel_setup.txt --novel-id 1
```

**使用本地解析器（不调用 LLM，速度更快但质量较低）：**

```bash
python -m src.main init ./sample_inputs/novel_setup.txt \
    --title "我的小说" \
    --no-llm
```

#### 审查设定（可选）

在导入前，可以让系统审查设定并提供建议：

```bash
python -m src.scripts.review_setup ./sample_inputs/novel_setup.txt
```

### 2. 导入资料库

资料库用于 RAG 检索，帮助系统理解世界观设定和文风。

#### 导入内置资料库

```bash
# 导入经典设定（修真、赛博朋克、克苏鲁等）
python -m src.scripts.seed_references

# Docker 环境
docker-compose exec app python -m src.scripts.seed_references
```

#### 导入自定义资料

创建 JSON 文件 `my_references.json`：

```json
[
  {
    "title": "自定义设定1",
    "source": "我的资料",
    "category": "world_setting",
    "tags": ["标签1", "标签2"],
    "content": "详细的设定内容..."
  },
  {
    "title": "自定义设定2",
    "source": "我的资料",
    "category": "style_reference",
    "tags": ["文风"],
    "content": "文风参考内容..."
  }
]
```

导入：

```bash
python -m src.scripts.import_references ./my_references.json
```

---

## ⚙️ 配置说明

### 环境变量配置

所有配置项都可通过 `.env` 文件或环境变量设置：

#### LLM 配置

```bash
# Gemini API (必需)
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=models/gemini-3-pro-preview
GEMINI_TEMPERATURE=0.8

# DeepSeek API (必需)
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-r1:7b
DEEPSEEK_ARCHITECT_TEMP=0.3
DEEPSEEK_REVIEWER_TEMP=0.1
```

#### 数据库配置

```bash
POSTGRES_URL=postgresql://user:password@host:5432/dbname
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
```

#### Redis 配置

```bash
REDIS_URL=redis://localhost:6379/0
```

#### Antigravity Rules 配置

```bash
# 循环熔断
MAX_RETRY_LIMIT=3

# 上下文管理
RECENT_CHAPTERS_CONTEXT=3
MAX_CONTEXT_CHAPTERS=10
```

#### 写作配置

```bash
MIN_CHAPTER_LENGTH=2000
TARGET_CHAPTER_LENGTH=3000
ENABLE_LOGIC_AUDIT=true
MIN_LOGIC_SCORE=0.7
```

### 配置验证

```bash
# 验证配置
python -c "from src.config import Config; result = Config.validate(); print('Valid:', result['valid']); print('Issues:', result.get('issues', [])); print('Warnings:', result.get('warnings', []))"

# 打印当前配置
python -c "from src.config import Config; Config.print_config()"
```

---

## 📖 使用指南

### 1. 命令行工具 (CLI)

#### 初始化小说

```bash
# 创建新小说
python -m src.main init ./my_setup.txt \
    --title "我的小说" \
    --author "作者名" \
    --description "小说简介"

# 更新现有小说
python -m src.main init ./my_setup.txt --novel-id 1
```

#### 生成章节

```bash
# 生成下一章（主分支）
python -m src.main run --novel-id 1

# 生成指定分支的章节
python -m src.main run --novel-id 1 --branch "if_hero_dies"
```

#### 导出小说

```bash
python -m src.scripts.export_novel --novel-id 1 --output ./output.txt
```

### 2. API 接口

#### 启动 API 服务

```bash
# 本地
python -m src.api.run_server

# 或使用 uvicorn
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

#### 查看 API 文档

访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 Swagger 文档。

#### 主要 API 端点

**触发生成任务：**

```bash
curl -X POST "http://localhost:8000/generation/" \
  -H "Content-Type: application/json" \
  -d '{
    "novel_id": 1,
    "branch_id": "main"
  }'
```

响应：
```json
{
  "message": "Generation task for novel 1 queued",
  "task_id": "abc123...",
  "status": "queued"
}
```

**查询任务状态：**

```bash
curl "http://localhost:8000/generation/status/{task_id}"
```

**实时流式订阅（SSE）：**

```bash
curl -N "http://localhost:8000/generation/stream/{task_id}"
```

**获取小说列表：**

```bash
curl "http://localhost:8000/novels/"
```

**获取章节内容：**

```bash
curl "http://localhost:8000/chapters/?novel_id=1&chapter_number=1"
```

#### Python 客户端示例

```python
import requests
import json

# 触发生成
response = requests.post(
    "http://localhost:8000/generation/",
    json={"novel_id": 1, "branch_id": "main"}
)
task_id = response.json()["task_id"]

# 查询状态
status = requests.get(f"http://localhost:8000/generation/status/{task_id}")
print(status.json())
```

### 3. Web 界面

访问 [http://localhost:8000](http://localhost:8000) 使用 Web 界面。

**功能包括：**
- 小说列表管理
- 章节预览和编辑
- 实时生成监控（SSE 流式输出）
- 资料库管理
- 配置查看和修改

---

## 📂 项目结构

```
NovelGen-Enterprise/
├── src/
│   ├── agents/              # 智能体实现
│   │   ├── base.py         # Agent 基类
│   │   ├── constants.py    # 常量定义
│   │   ├── architect.py    # 架构师 Agent（大纲规划）
│   │   ├── writer.py       # 写手 Agent（正文撰写）
│   │   ├── reviewer.py     # 审查员 Agent（逻辑审查）
│   │   ├── evolver.py      # 演化器 Agent（人物成长）
│   │   ├── style_analyzer.py  # 文风分析器
│   │   └── learner.py      # 学习器 Agent（设定解析）
│   ├── api/                 # FastAPI 应用
│   │   ├── app.py          # 应用入口
│   │   ├── routes/         # 路由模块
│   │   │   ├── novels.py
│   │   │   ├── chapters.py
│   │   │   ├── generation.py
│   │   │   └── ...
│   │   └── static/         # 静态文件（Web UI）
│   ├── db/                  # 数据库相关
│   │   ├── base.py         # 数据库连接
│   │   ├── models.py       # ORM 模型
│   │   ├── init_db.py      # 初始化脚本
│   │   ├── vector_store.py # 向量存储
│   │   └── reset_db.py    # 重置脚本
│   ├── schemas/            # 数据模式
│   │   ├── state.py        # 状态定义
│   │   └── style.py        # 文风定义
│   ├── services/           # 业务服务
│   │   ├── state_loader.py # 状态加载器
│   │   └── redis_stream.py # Redis 流服务
│   ├── scripts/            # 工具脚本
│   │   ├── import_novel.py      # 导入小说
│   │   ├── seed_references.py   # 导入资料库
│   │   ├── export_novel.py      # 导出小说
│   │   └── ...
│   ├── config.py           # 配置管理
│   ├── graph.py            # LangGraph 工作流
│   ├── llms.py             # LLM 封装
│   ├── utils.py            # 工具函数
│   ├── tasks.py            # Celery 任务
│   ├── worker.py           # Celery Worker
│   └── main.py             # CLI 入口
├── sample_inputs/          # 示例输入
│   └── novel_setup.txt     # 示例设定文档
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile              # Docker 镜像构建
├── requirements.txt        # Python 依赖
└── README.md               # 本文档
```

---

## ❓ 常见问题

### Q1: 如何获取 API Key？

**Gemini API Key:**
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录 Google 账号
3. 创建新的 API Key

**DeepSeek API Key:**
1. 访问 [DeepSeek 官网](https://www.deepseek.com/)
2. 注册账号并获取 API Key

### Q2: 数据库连接失败？

**检查项：**
1. PostgreSQL 是否正在运行
2. 连接字符串是否正确
3. 数据库是否已创建
4. 用户权限是否足够

**解决方案：**
```bash
# 检查 PostgreSQL 状态
# Linux
sudo systemctl status postgresql

# 测试连接
psql -U postgres -h localhost -d novelgen
```

### Q3: Celery Worker 无法启动？

**Windows 用户：**
必须使用 `--pool=solo` 参数：
```bash
celery -A src.worker.celery_app worker --loglevel=info --pool=solo
```

**Linux/Mac 用户：**
确保 Redis 正在运行：
```bash
redis-cli ping  # 应该返回 PONG
```

### Q4: 生成速度慢？

**优化建议：**
1. 使用更快的模型（如 Gemini Flash）
2. 减少上下文窗口大小（`RECENT_CHAPTERS_CONTEXT`）
3. 增加 Celery Worker 数量
4. 使用 GPU 加速（如果支持）

### Q5: 如何查看日志？

**Docker 环境：**
```bash
# 查看所有日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f worker
```

**本地环境：**
日志默认输出到控制台，也可以配置日志文件。

### Q6: 如何重置数据库？

**⚠️ 警告：会删除所有数据！**

```bash
# 删除所有表并重新创建
python -m src.db.init_db --drop

# 或使用重置脚本
python -m src.db.reset_db
```

---

## 🔧 开发指南

### 代码结构

- **Agent 基类**: 所有 Agent 继承自 `BaseAgent`，统一 LLM 初始化逻辑
- **常量管理**: 所有魔法字符串和数字集中在 `src/agents/constants.py`
- **配置管理**: 统一使用 `src/config.py` 管理配置
- **错误处理**: 使用 Python logging 模块记录日志

### 添加新 Agent

1. 继承 `BaseAgent`：
```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(model_name="gemini")
    
    async def process(self, *args, **kwargs):
        # 实现处理逻辑
        pass
```

2. 在 `graph.py` 中注册：
```python
self.my_agent = MyAgent()
self.workflow.add_node("my_node", self.my_node)
```

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest tests/test_agents.py
```

### 代码规范

- 遵循 PEP 8 规范
- 使用类型提示
- 添加文档字符串
- 编写单元测试

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

在提交代码前，请确保：
1. ✅ 运行了所有单元测试
2. ✅ 代码符合 PEP 8 规范
3. ✅ 新增功能包含相应的文档说明
4. ✅ 更新了 CHANGELOG.md

### 提交 Pull Request

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 状态机工作流
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [Celery](https://docs.celeryproject.org/) - 分布式任务队列
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL 向量扩展

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/aanong/NovelGen-Enterprise/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aanong/NovelGen-Enterprise/discussions)

---

**Happy Novel Writing! 📚✨**
