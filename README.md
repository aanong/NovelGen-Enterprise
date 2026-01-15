# NovelGen-Enterprise (NGE)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-LangGraph-purple)]()
[![Queue](https://img.shields.io/badge/Queue-Celery%20%7C%20Redis-red)]()

**NovelGen-Enterprise (NGE)** 是一款企业级、高可用的长篇小说生成系统。它不仅仅是一个简单的 LLM 包装器，而是一个基于 **LangGraph** 的复杂多智能体协作系统，旨在解决长篇生成中的逻辑连贯性、人物一致性和风格统一性问题。

系统采用 **DeepSeek (逻辑中枢)** 与 **Gemini (文学工匠)** 的双模型架构，结合 **Celery + Redis** 分布式任务队列和 **PostgreSQL (pgvector)** 向量数据库，支持多用户、多项目、多分支的高并发生成。

---

## 目录

- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
  - [前置要求](#前置要求)
  - [方式一：Docker 一键部署](#方式一docker-一键部署推荐)
  - [方式二：本地开发环境](#方式二本地开发环境搭建)
- [环境配置](#环境配置)
- [数据库初始化](#数据库初始化)
- [完整使用流程](#完整使用流程)
  - [步骤1：创建小说项目](#步骤1创建小说项目)
  - [步骤2：导入小说设定](#步骤2导入小说设定)
  - [步骤3：生成章节大纲](#步骤3生成章节大纲)
  - [步骤4：运行章节生成](#步骤4运行章节生成)
  - [步骤5：导出小说](#步骤5导出小说)
- [API 接口文档](#api-接口文档)
- [CLI 命令参考](#cli-命令参考)
- [资料库管理](#资料库管理)
- [多分支剧情](#多分支剧情)
- [项目结构](#项目结构)
- [Antigravity 规则系统](#antigravity-规则系统)
- [深度功能详解](#深度功能详解)
  - [一、文笔优化系统](#一文笔优化系统)
  - [二、文学元素系统](#二文学元素系统)
  - [三、价值观系统](#三价值观系统)
  - [四、世界观一致性守护](#四世界观一致性守护)
  - [五、角色成长系统](#五角色成长系统)
- [故障排除](#故障排除)
- [开发指南](#开发指南)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 核心特性

### 深度智能架构

- **双模型协同**: DeepSeek 负责大纲拆解、逻辑审查和剧情推演；Gemini 负责正文撰写、文风模仿和长文本扩写
- **LangGraph 状态机**: 采用循环图结构，实现 Plan → Write → Review → Revise 的自我修正循环
- **RAG 上下文增强**: 基于 pgvector 的语义检索，精准提取与当前场景相关的世界观设定和历史伏笔
- **Antigravity Rules**: 内置反重力规则系统，防止人物 OOC、逻辑硬伤和世界观崩坏

### 高级文学功能

- **伏笔生命周期管理**: 结构化追踪伏笔的埋设、推进和回收
- **人物心理深度**: 支持人物内心冲突、潜意识恐惧、防御机制等心理描写
- **节奏控制系统**: RhythmAnalyzer 分析剧情节奏，防止连续高潮或拖沓
- **典故注入系统**: AllusionAdvisor 主动推荐文学典故和叙事手法，支持典故使用验证
- **语言风格定制**: 每个角色可配置独特的说话风格和口头禅

### 深度优化功能（v2.0 新增）

- **写作技法指导**: WritingTechniqueAdvisor 提供场景化写作技法建议（白描、蒙太奇、意识流等）
- **视角控制系统**: 支持第一人称、第三人称限制视角、全知视角的精确控制
- **描写平衡管理**: 自动调节环境/动作/心理/对话描写的比例
- **氛围渲染控制**: 针对紧张、恐怖、温馨等不同氛围提供关键词和禁忌词指导
- **文学元素库**: 预置典故、诗词、成语、叙事母题等丰富的文学素材
- **价值观冲突系统**: 支持角色两难抉择建模，自动检测行为违规
- **世界观一致性守护**: WorldConsistencyGuard 检测并修正违背设定的内容
- **角色成长曲线**: 支持线性/指数/阶梯等多种成长模式，追踪技能驾驭曲线
- **思想成熟度系统**: 追踪角色的认知深度、情绪成熟度、决断力等思想维度

### 企业级工程能力

- **分布式任务队列**: Celery + Redis 支持任务持久化和异步处理
- **实时流式输出**: SSE 协议实时推送生成过程
- **多线剧情分支**: 支持平行宇宙（IF 线）生成，自动维护分支状态快照
- **依赖注入架构**: 工厂模式支持灵活配置和测试

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Web UI    │  │  REST API   │  │     CLI     │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Server                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                          │  │
│  │  NovelService │ ChapterService │ CharacterService │ ...   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Redis       │  │  Celery Worker  │
│   (pgvector)    │  │   (Broker)      │  │                 │
└─────────────────┘  └─────────────────┘  └────────┬────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
                     │  LangGraph      │  │   RAG Engine    │  │   VectorStore   │
                     │  Workflow       │  │   (Retrieval)   │  │   (pgvector)    │
                     └────────┬────────┘  └─────────────────┘  └─────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    ▼                         ▼                         ▼
┌────────────┐         ┌────────────┐           ┌────────────┐
│ LoadContext│ ──────► │   Plan     │ ────────► │  Refine    │
│    Node    │         │   Node     │           │   Node     │
└────────────┘         └────────────┘           └─────┬──────┘
                                                      │
                                                      ▼
┌────────────┐         ┌────────────┐           ┌────────────┐
│   Evolve   │ ◄────── │   Review   │ ◄──────── │   Write    │
│    Node    │         │    Node    │           │    Node    │
└────────────┘         └─────┬──────┘           └────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              [PASS: Evolve]    [FAIL: Revise/Repair]
```

### 工作流说明

1. **LoadContext**: 从数据库加载角色状态、世界观、历史摘要
2. **Plan**: ArchitectAgent 规划本章内容，RhythmAnalyzer 分析节奏
3. **Refine**: RAG 检索相关设定，AllusionAdvisor 推荐典故，WritingTechniqueAdvisor 提供技法建议
4. **Write**: WriterAgent 生成章节正文（应用视角控制、描写平衡、氛围渲染）
5. **Review**: ReviewerAgent 逻辑审查和 OOC 检测，WorldConsistencyGuard 检查世界观一致性
6. **Evolve**: CharacterEvolver 更新人物状态（含价值观变化、思想成长、技能进化），保存章节

---

## 快速开始

### 前置要求

#### Docker 部署（推荐）

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存

#### 本地开发环境

- Python 3.10+
- PostgreSQL 16+（需安装 pgvector 扩展）
- Redis 7+
- Git

### 方式一：Docker 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/NovelGen-Enterprise.git
cd NovelGen-Enterprise

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API 密钥

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f app
docker-compose logs -f worker
```

服务启动后：
- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **Web 界面**: http://localhost:8000

### 方式二：本地开发环境搭建

```bash
# 1. 克隆项目
git clone https://github.com/your-org/NovelGen-Enterprise.git
cd NovelGen-Enterprise

# 2. 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 5. 启动 PostgreSQL 和 Redis（确保已安装）
# PostgreSQL 需要安装 pgvector 扩展

# 6. 初始化数据库
python -m src.db.init_db

# 7. 启动 API 服务（终端 1）
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# 8. 启动 Celery Worker（终端 2）
celery -A src.worker.celery_app worker --loglevel=info
```

---

## 环境配置

创建 `.env` 文件并配置以下环境变量：

```bash
# ============ 必需配置 ============

# Google Gemini API 密钥（必需）
GOOGLE_API_KEY=your_gemini_api_key_here

# PostgreSQL 数据库连接（必需）
POSTGRES_URL=postgresql://postgres:password@localhost:5432/novelgen

# ============ 可选配置 ============

# DeepSeek 配置（如使用 Ollama 本地部署可保持默认）
DEEPSEEK_API_BASE=http://localhost:11434/v1
DEEPSEEK_API_KEY=ollama
DEEPSEEK_MODEL=deepseek-r1:7b

# Gemini 模型配置
GEMINI_MODEL=models/gemini-2.0-flash
GEMINI_TEMPERATURE=0.8

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 写作配置
MIN_CHAPTER_LENGTH=2000
TARGET_CHAPTER_LENGTH=3000

# Antigravity 规则配置
MAX_RETRY_LIMIT=3
RECENT_CHAPTERS_CONTEXT=3
MAX_CONTEXT_CHAPTERS=10

# 功能开关
ENABLE_STYLE_ANALYSIS=true
ENABLE_LOGIC_AUDIT=true
MIN_LOGIC_SCORE=0.7

# 数据库连接池
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### 配置验证

```bash
# 验证配置是否正确
python -c "from src.config import Config; Config.print_config(); print(Config.validate())"
```

---

## 数据库初始化

### 自动初始化

```bash
# 初始化数据库表结构
python -m src.db.init_db
```

### 手动初始化（PostgreSQL）

```sql
-- 1. 创建数据库
CREATE DATABASE novelgen;

-- 2. 连接到数据库
\c novelgen

-- 3. 安装 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
```

### 数据库迁移

```bash
# 使用 Alembic 进行迁移
alembic upgrade head

# 生成新的迁移文件
alembic revision --autogenerate -m "描述"
```

### 重置数据库

```bash
# 警告：此操作将删除所有数据
python -m src.db.reset_db
```

---

## 完整使用流程

以下是从零开始创建和生成小说的完整流程：

### 步骤1：创建小说项目

#### 方式 A：使用 CLI

```bash
python -m src.main init sample_inputs/novel_setup.txt --title "我的小说" --author "作者名"
```

#### 方式 B：使用 API

```bash
curl -X POST "http://localhost:8000/api/novels/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的小说",
    "author": "作者名",
    "description": "这是一部奇幻小说"
  }'
```

**响应示例：**
```json
{
  "id": 1,
  "title": "我的小说",
  "author": "作者名",
  "description": "这是一部奇幻小说",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 步骤2：导入小说设定

准备设定文档（Markdown 格式），包含：
- 世界观设定
- 人物设定
- 剧情大纲
- 文风参考

#### 设定文档示例

```markdown
# 《星际征途》设定文档

## 世界观

### 宇宙背景
公元3000年，人类已殖民银河系...

### 势力分布
- 地球联邦：人类主导的政治实体
- 天狼星帝国：军事强权

## 人物设定

### 主角：林远
- 性格：冷静、睿智、重情义
- 背景：前联邦特种兵，因任务失败退役
- 技能：近战格斗、星舰驾驶
- 核心动机：寻找失踪的妹妹

### 女主：苏晴
- 性格：热情、善良、有正义感
- 背景：联邦医疗官
- 与主角关系：救命恩人，后发展为恋人

## 剧情大纲

第一章：命运的邂逅
- 场景：废弃空间站
- 核心冲突：主角遭遇海盗袭击
- 伏笔：发现妹妹的线索

第二章：新的旅程
- 场景：联邦首都
- 核心冲突：被卷入政治阴谋
```

#### 导入设定

```bash
# 使用 LLM 解析设定文档
python -m src.scripts.import_novel sample_inputs/novel_setup.txt --novel-id 1

# 不使用 LLM（快速模式）
python -m src.scripts.import_novel sample_inputs/novel_setup.txt --novel-id 1 --no-llm
```

### 步骤3：生成章节大纲

```bash
# 生成 10 章的大纲
python -m src.scripts.generate_outline sample_inputs/synopsis.txt --chapters 10 --novel-id 1

# 调整现有大纲（从第 5 章开始）
python -m src.scripts.generate_outline --refine --novel-id 1 --start-chapter 5 \
  --instruction "增加更多战斗场景"
```

### 步骤4：运行章节生成

#### 方式 A：CLI 直接运行（同步）

```bash
# 生成下一章
python -m src.main run --novel-id 1

# 指定分支
python -m src.main run --novel-id 1 --branch main
```

#### 方式 B：API 异步任务

```bash
# 启动生成任务
curl -X POST "http://localhost:8000/api/generate/chapter" \
  -H "Content-Type: application/json" \
  -d '{
    "novel_id": 1,
    "branch_id": "main"
  }'
```

**响应示例：**
```json
{
  "task_id": "abc123-def456",
  "status": "pending",
  "message": "任务已提交"
}
```

#### 查询任务状态

```bash
curl "http://localhost:8000/api/generate/status/abc123-def456"
```

#### SSE 实时流（推荐）

```javascript
// 前端 JavaScript 示例
const eventSource = new EventSource('/api/generate/stream/abc123-def456');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('进度:', data.progress);
  console.log('内容:', data.content);
};

eventSource.onerror = () => {
  eventSource.close();
};
```

### 步骤5：导出小说

```bash
# 导出为 Markdown
python -m src.scripts.export_novel --novel-id 1 --output my_novel.md

# 导出指定分支
python -m src.scripts.export_novel --novel-id 1 --branch if_line_1 --output if_novel.md
```

---

## API 接口文档

启动服务后访问 http://localhost:8000/docs 查看完整的 Swagger 文档。

### 核心接口

| 方法 | 路径 | 描述 |
|------|------|------|
| **小说管理** |||
| GET | `/api/novels/` | 获取小说列表 |
| POST | `/api/novels/` | 创建新小说 |
| GET | `/api/novels/{id}` | 获取小说详情 |
| PUT | `/api/novels/{id}` | 更新小说信息 |
| DELETE | `/api/novels/{id}` | 删除小说 |
| **章节管理** |||
| GET | `/api/chapters/novel/{novel_id}` | 获取小说章节列表 |
| GET | `/api/chapters/{id}` | 获取章节详情 |
| PUT | `/api/chapters/{id}` | 更新章节内容 |
| **角色管理** |||
| GET | `/api/characters/novel/{novel_id}` | 获取小说角色列表 |
| POST | `/api/characters/` | 创建新角色 |
| PUT | `/api/characters/{id}` | 更新角色信息 |
| **大纲管理** |||
| GET | `/api/outlines/novel/{novel_id}` | 获取大纲列表 |
| POST | `/api/outlines/` | 创建大纲 |
| PUT | `/api/outlines/{id}` | 更新大纲 |
| **生成任务** |||
| POST | `/api/generate/chapter` | 启动章节生成任务 |
| GET | `/api/generate/status/{task_id}` | 查询任务状态 |
| GET | `/api/generate/stream/{task_id}` | SSE 实时流 |
| **资料库** |||
| GET | `/api/references/` | 获取参考资料 |
| POST | `/api/references/import` | 导入资料 |
| **分支管理** |||
| GET | `/api/novels/{id}/branches` | 获取分支列表 |
| POST | `/api/novels/{id}/branches` | 创建新分支 |

### 请求示例

#### 创建角色

```bash
curl -X POST "http://localhost:8000/api/characters/" \
  -H "Content-Type: application/json" \
  -d '{
    "novel_id": 1,
    "name": "林远",
    "role": "protagonist",
    "personality_traits": {
      "personality": "冷静、睿智",
      "background": "前联邦特种兵"
    },
    "skills": ["近战格斗", "星舰驾驶"],
    "forbidden_actions": ["背叛同伴", "无故杀戮平民"]
  }'
```

#### 更新大纲

```bash
curl -X PUT "http://localhost:8000/api/outlines/1" \
  -H "Content-Type: application/json" \
  -d '{
    "scene_description": "废弃空间站，昏暗的灯光闪烁",
    "key_conflict": "主角遭遇海盗伏击，必须保护受伤的医疗官",
    "foreshadowing": ["发现神秘芯片", "海盗首领认出主角身份"]
  }'
```

---

## CLI 命令参考

### 主命令

```bash
# 初始化小说
python -m src.main init <设定文件> --title <标题> [--author <作者>] [--no-llm]

# 运行生成
python -m src.main run --novel-id <ID> [--branch <分支>]
```

### 脚本命令

```bash
# 导入小说设定
python -m src.scripts.import_novel <文件路径> --novel-id <ID> [--no-llm]

# 生成大纲
python -m src.scripts.generate_outline <梗概文件> --chapters <数量> --novel-id <ID>

# 调整大纲
python -m src.scripts.generate_outline --refine --novel-id <ID> --start-chapter <起始章> --instruction "调整说明"

# 导出小说
python -m src.scripts.export_novel --novel-id <ID> [--output <文件>] [--branch <分支>]

# 管理资料库
python -m src.scripts.manage_references import <JSON文件> [--novel-id <ID>] [--force]
python -m src.scripts.manage_references list [--novel-id <ID>] [--category <类别>]

# 数据库验证
python -m src.scripts.verify_db

# 测试所有流程
python -m src.scripts.test_all_flows

# 验证优化
python -m src.scripts.verify_optimization
```

---

## 资料库管理

NGE 支持两级资料库：

1. **全局资料库**: 适用于所有小说的通用设定（如经典网文套路、常见职业设定）
2. **小说专属资料库**: 仅适用于特定小说的独有设定

### 导入资料

```bash
# 导入全局资料
python -m src.scripts.manage_references import data/global_references.json

# 导入小说专属资料
python -m src.scripts.manage_references import data/novel_1_refs.json --novel-id 1

# 强制覆盖
python -m src.scripts.manage_references import data/refs.json --force
```

### 资料 JSON 格式

```json
[
  {
    "title": "修真境界体系",
    "content": "炼气、筑基、金丹、元婴、化神、渡劫、大乘",
    "source": "经典修真设定",
    "category": "cultivation_system",
    "tags": ["修真", "境界", "体系"]
  },
  {
    "title": "角色原型：复仇者",
    "content": "因家族灭门而踏上复仇之路的角色...",
    "source": "叙事原型库",
    "category": "character_archetype",
    "tags": ["原型", "复仇", "动机"]
  }
]
```

更多详情请参考 [REFERENCE_LIBRARY_GUIDE.md](REFERENCE_LIBRARY_GUIDE.md)

---

## 多分支剧情

NGE 支持创建平行宇宙（IF 线），实现同一故事的不同发展方向。

### 创建分支

```bash
curl -X POST "http://localhost:8000/api/novels/1/branches" \
  -H "Content-Type: application/json" \
  -d '{
    "branch_id": "if_heroine_dies",
    "parent_branch": "main",
    "fork_chapter": 5,
    "description": "女主在第五章牺牲的 IF 线"
  }'
```

### 在分支上生成

```bash
# CLI
python -m src.main run --novel-id 1 --branch if_heroine_dies

# API
curl -X POST "http://localhost:8000/api/generate/chapter" \
  -H "Content-Type: application/json" \
  -d '{"novel_id": 1, "branch_id": "if_heroine_dies"}'
```

### 分支状态隔离

每个分支独立维护：
- 角色状态快照（心情、技能、资产）
- 章节内容
- 伏笔进度
- 人物关系

---

## 项目结构

```
NovelGen-Enterprise/
├── src/
│   ├── agents/                 # AI Agent 实现
│   │   ├── __init__.py        # 模块导出
│   │   ├── base.py            # Agent 基类
│   │   ├── architect.py       # 大纲规划 Agent
│   │   ├── writer.py          # 写作 Agent
│   │   ├── reviewer.py        # 审核 Agent
│   │   ├── evolver.py         # 人物演化 Agent
│   │   ├── rhythm_analyzer.py # 节奏分析 Agent
│   │   ├── style_analyzer.py  # 文风分析 Agent
│   │   ├── allusion_advisor.py # 典故推荐 Agent（含验证功能）
│   │   ├── writing_technique_advisor.py # 写作技法顾问 Agent [新增]
│   │   ├── world_guard.py     # 世界观一致性守护 Agent [新增]
│   │   ├── learner.py         # 学习 Agent
│   │   ├── summarizer.py      # 摘要 Agent
│   │   └── constants.py       # 常量定义
│   │
│   ├── api/                   # FastAPI 接口
│   │   ├── app.py            # 应用入口
│   │   ├── deps.py           # 依赖注入
│   │   ├── schemas.py        # API 数据模型
│   │   └── routes/           # 路由定义
│   │       ├── novels.py
│   │       ├── chapters.py
│   │       ├── characters.py
│   │       ├── plot_branches.py # 分支管理
│   │       └── ...
│   │
│   ├── db/                    # 数据库层
│   │   ├── base.py           # 数据库连接
│   │   ├── models.py         # ORM 模型
│   │   ├── vector_store.py   # 向量存储
│   │   └── *_repository.py   # 仓储类
│   │
│   ├── nodes/                 # LangGraph 节点
│   │   ├── __init__.py       # 模块导出
│   │   ├── base.py           # 节点基类
│   │   ├── loader.py         # 上下文加载
│   │   ├── planner.py        # 章节规划
│   │   ├── refiner.py        # 上下文增强
│   │   ├── writer.py         # 章节写作
│   │   ├── reviewer.py       # 内容审核
│   │   └── evolver.py        # 状态演化
│   │
│   ├── schemas/               # 数据模型
│   │   ├── __init__.py       # 模块导出
│   │   ├── state.py          # NGEState 全局状态（含价值观/成长系统）
│   │   ├── style.py          # 文风模型（含视角/描写/氛围控制）[增强]
│   │   └── literary.py       # 文学元素模型（典故/诗词/母题）[新增]
│   │
│   ├── scripts/               # 独立脚本
│   │   ├── import_novel.py   # 导入设定
│   │   ├── export_novel.py   # 导出小说
│   │   ├── generate_outline.py # 生成大纲
│   │   └── manage_references.py # 资料库管理
│   │
│   ├── services/              # 业务逻辑层
│   │   ├── novel_service.py
│   │   ├── chapter_service.py
│   │   ├── plot_branch_service.py # 分支服务
│   │   └── ...
│   │
│   ├── config.py              # 配置管理
│   ├── graph.py               # LangGraph 工作流
│   ├── main.py                # CLI 入口
│   └── worker.py              # Celery Worker
│
├── data/                      # 数据文件
│   └── global_references.json # 全局资料库
│
├── sample_inputs/             # 示例输入
│   └── novel_setup.txt        # 示例设定文档
│
├── docker-compose.yml         # Docker 编排
├── Dockerfile                 # Docker 镜像
├── requirements.txt           # Python 依赖
├── REFERENCE_LIBRARY_GUIDE.md # 资料库使用指南
├── CHANGELOG.md               # 更新日志
└── README.md                  # 本文档
```

---

## Antigravity 规则系统

NGE 内置"反重力规则"系统，确保生成内容的质量和一致性：

| 规则 | 描述 | 实现方式 |
|------|------|----------|
| Rule 1.1 | 世界观不可修改 | RAG 检索世界观设定，强制遵循 |
| Rule 2.1 | 人物灵魂锚定 | 每个角色配置禁忌行为列表 |
| Rule 2.2 | 禁止降智行为 | ReviewerAgent 检测 OOC |
| Rule 3.1 | 上下文滑窗 | 自动回溯最近 N 章摘要 |
| Rule 3.3 | 禁止逻辑硬伤 | 逻辑审查评分机制 |
| Rule 4.1 | 清除 AI 痕迹 | 自动过滤 `<think>` 标签 |
| Rule 5.1 | 循环熔断 | 最大重试次数限制 |
| Rule 5.2 | 分级修复 | 超过重试次数后 Gemini 介入 |
| Rule 6.1 | 场景约束 | 根据场景类型调整写作风格 |

### 配置示例

```python
# src/config.py
class AntigravityConfig:
    MAX_RETRY_LIMIT = 3           # Rule 5.1
    RECENT_CHAPTERS_CONTEXT = 3   # Rule 3.1
    SCENE_CONSTRAINTS = {         # Rule 6.1
        "Action": {"max_sentence_length": 20},
        "Dialogue": {"min_dialogue_ratio": 0.6}
    }
```

---

## 深度功能详解

### 一、文笔优化系统

#### 写作技法顾问 (WritingTechniqueAdvisor)

根据场景类型自动推荐写作技法，提供专业的写作指导：

```python
from src.agents import WritingTechniqueAdvisor

advisor = WritingTechniqueAdvisor()
advice = await advisor.advise(state)

# 返回结构化建议
# - recommended_techniques: 推荐技法列表
# - atmosphere_guide: 氛围渲染指导
# - description_guides: 描写比例建议
# - key_warnings: 关键警告
```

**内置技法库：**

| 技法 | 适用场景 | 描述 |
|------|----------|------|
| 白描 | 动作场景、紧张时刻 | 简练笔墨，抓住特征 |
| 蒙太奇 | 时间跳跃、回忆穿插 | 镜头组接，画面切换 |
| 意识流 | 心理描写、情感爆发 | 意识流动，打破时空 |
| 留白 | 悬念制造、情感含蓄 | 不说透，留想象空间 |
| 五感描写 | 环境渲染、沉浸体验 | 视听触嗅味全方位 |

#### 视角控制 (PerspectiveControl)

```python
from src.schemas import PerspectiveType, PerspectiveControl

# 配置叙事视角
perspective = PerspectiveControl(
    primary_perspective=PerspectiveType.THIRD_LIMITED,  # 第三人称限制视角
    pov_character="林远",  # 视角人物
    allow_pov_switch=False,  # 禁止章节内切换
    perspective_constraints=["不能看到视角人物背后的事物"]
)
```

#### 场景写作模板 (SCENE_TEMPLATES)

系统预置四种场景模板，自动调整写作风格：

- **Action**: 短句为主、动词密集、节奏紧凑
- **Emotional**: 心理描写深入、内心独白、意象渲染
- **Dialogue**: 对话节奏、潜台词、非语言描写
- **Description**: 五感描写、空间层次、时间流动

---

### 二、文学元素系统

#### 预置文学素材库

系统内置丰富的文学素材，可直接检索使用：

```python
from src.agents import AllusionAdvisor
from src.schemas import EmotionalCategory

advisor = AllusionAdvisor()

# 按情感搜索典故
allusions = advisor.search_preset_allusions(
    emotion=EmotionalCategory.REVENGE,
    limit=5
)

# 按意象搜索诗词
poetry = advisor.search_preset_poetry(
    imagery="月",
    mood=EmotionalCategory.LONGING
)

# 获取叙事母题
motif = advisor.get_motif_by_name("英雄之旅")
```

**预置典故示例：**

| 典故 | 核心含义 | 适用情感 |
|------|----------|----------|
| 卧薪尝胆 | 忍辱负重，发愤图强 | 复仇、雄心 |
| 塞翁失马 | 祸福相依 | 希望、怀旧 |
| 精卫填海 | 意志坚定，永不放弃 | 雄心、悲凉 |

#### 典故使用验证

自动检验典故是否被正确使用：

```python
# 验证章节中的典故使用
validations = await advisor.validate_allusion_usage(
    content=chapter_content,
    expected_allusions=["卧薪尝胆", "精卫填海"],
    scene_context="主角遭遇重大失败后蛰伏修炼"
)

# 返回验证结果
# - is_correct: 是否正确使用
# - naturalness_score: 自然度评分
# - fit_score: 契合度评分
# - suggestions: 改进建议
```

---

### 三、价值观系统

#### 价值信念模型 (ValueBelief)

```python
from src.schemas import ValueBelief, ValueSystem

# 定义角色的核心价值观
justice = ValueBelief(
    value_name="正义",
    strength=0.9,
    origin="童年经历",
    can_be_shaken=True,
    shake_conditions=["亲人被正义所伤"],
    related_actions={
        "must_do": "保护无辜",
        "must_not_do": "袖手旁观",
        "will_sacrifice": "个人利益"
    },
    opposing_values=["私利"]
)

# 创建完整价值观系统
value_system = ValueSystem(
    beliefs=[justice],
    moral_absolutes=["不伤害无辜", "不背叛同伴"]
)
```

#### 价值冲突建模

系统自动检测两难抉择情境：

```python
# 检测价值冲突
conflict = value_system.detect_potential_conflict(
    situation="主角发现亲人犯下了不可饶恕的罪行"
)

# 返回冲突详情
# - values_in_conflict: ["正义", "亲情"]
# - intensity: 0.9
# - possible_choices: [...]
```

#### 行为违规检查

```python
# 检查行为是否违反价值观
violations = value_system.check_action_violation(
    action="主角为了复仇杀害无辜平民"
)
# 返回: ["道德底线：不伤害无辜"]
```

---

### 四、世界观一致性守护

#### WorldConsistencyGuard

自动检测生成内容是否违背世界观设定：

```python
from src.agents import WorldConsistencyGuard

guard = WorldConsistencyGuard()
result = await guard.check_consistency(state, chapter_content)

# 返回检查结果
# - is_consistent: 是否一致
# - violations: 违规列表
# - overall_score: 一致性评分
# - needs_revision: 是否需要修订
```

**检查维度：**

| 维度 | 检查内容 |
|------|----------|
| 能力体系 | 角色使用的能力是否超出应有水平 |
| 地理设定 | 地点描述是否与设定一致 |
| 时间线 | 事件顺序是否合理 |
| 科技/魔法 | 使用的技术/魔法是否符合世界观 |
| 社会规则 | 人物行为是否符合社会背景 |

**严重程度：**

- `critical`: 严重违规，必须修改
- `major`: 较大违规，建议修改
- `minor`: 轻微违规，可接受但最好调整

---

### 五、角色成长系统

#### 成长曲线类型

支持多种成长模式：

| 类型 | 特点 | 适用角色 |
|------|------|----------|
| LINEAR | 线性平稳成长 | 普通角色 |
| EXPONENTIAL | 后期爆发型 | 大器晚成型 |
| LOGARITHMIC | 早期快速成长 | 天才型 |
| STEP | 阶梯突破型 | 需要顿悟的角色 |
| WAVE | 起伏波动型 | 命途多舛型 |

#### 技能掌握阶段

```python
from src.schemas import MasteryStage, AbilityLevel

skill = AbilityLevel(
    level=5,
    proficiency=0.8,
    mastery_stage=MasteryStage.PROFICIENT,  # 熟练
    growth_curve=GrowthCurveType.STEP,  # 阶梯成长
    bottleneck={"type": "insight", "description": "需要实战顿悟"}
)
```

**掌握阶段：**

1. `UNAWARE` - 未知（不知道自己不会）
2. `NOVICE` - 初学（知道自己不会）
3. `COMPETENT` - 胜任（有意识地会）
4. `PROFICIENT` - 熟练（无意识地会）
5. `MASTER` - 大师（可以教授他人）
6. `TRANSCENDENT` - 超凡（开创新境）

#### 思想成熟度

追踪角色的认知发展：

```python
from src.schemas import MindsetDimension

mindset = MindsetDimension(
    openness=0.6,           # 思维开放度
    depth=0.5,              # 思维深度
    emotional_maturity=0.4, # 情绪成熟度
    empathy=0.7,            # 共情能力
    decisiveness=0.5,       # 决断力
    resilience=0.6,         # 抗压能力
    insight=0.5,            # 领悟力
)

# 获取整体成熟度
maturity = mindset.get_overall_maturity()  # 0.0-1.0
```

#### 成长里程碑追踪

```python
from src.schemas import CharacterGrowthSystem

growth = CharacterGrowthSystem(
    current_growth_theme="学会信任",
    growth_blockers=["童年创伤未愈"],
    growth_accelerators=["遇到良师益友"]
)

# 记录重大成长节点
growth.record_milestone(
    milestone_type="insight",
    chapter=15,
    description="在生死关头终于领悟剑意",
    is_major=True
)
```

---

## 故障排除

### 常见问题

#### 1. 数据库连接失败

```
Error: could not connect to server
```

**解决方案：**
```bash
# 检查 PostgreSQL 是否运行
docker-compose ps db

# 检查连接字符串
echo $POSTGRES_URL

# 测试连接
psql $POSTGRES_URL -c "SELECT 1"
```

#### 2. pgvector 扩展未安装

```
Error: type "vector" does not exist
```

**解决方案：**
```sql
-- 连接到数据库后执行
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 3. Gemini API 密钥无效

```
Error: 403 Forbidden
```

**解决方案：**
1. 确认 `GOOGLE_API_KEY` 正确设置
2. 检查 API 密钥是否已启用 Gemini API
3. 确认账号有足够的配额

#### 4. Celery Worker 无法启动

```
Error: No module named 'src'
```

**解决方案：**
```bash
# 确保在项目根目录运行
cd /path/to/NovelGen-Enterprise

# 使用正确的命令
celery -A src.worker.celery_app worker --loglevel=info
```

#### 5. 生成内容过短

**解决方案：**
```bash
# 调整配置
export MIN_CHAPTER_LENGTH=3000
export TARGET_CHAPTER_LENGTH=5000
```

### 日志查看

```bash
# Docker 环境
docker-compose logs -f app
docker-compose logs -f worker

# 本地环境
tail -f logs/app.log
```

---

## 开发指南

### 代码风格

```bash
# 格式化代码
black src/

# 排序导入
isort src/

# 类型检查
mypy src/
```

### 添加新 Agent

1. 在 `src/agents/` 创建新文件
2. 继承 `BaseAgent` 基类
3. 实现 `process()` 方法
4. 在 `src/core/factories.py` 中注册

```python
# src/agents/my_agent.py
from .base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, temperature: float = 0.7):
        super().__init__(
            model_name="gemini",
            temperature=temperature
        )
    
    async def process(self, state, **kwargs):
        # 实现逻辑
        pass
```

### 添加新 Node

1. 在 `src/nodes/` 创建新文件
2. 继承 `BaseNode` 或 `AgentNode`
3. 实现 `__call__()` 方法
4. 在 `src/graph.py` 中添加节点

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agents.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 验证系统

```bash
# 验证数据库
python -m src.scripts.verify_db

# 验证优化
python -m src.scripts.verify_optimization

# 测试完整流程
python -m src.scripts.test_all_flows
```

---

## 贡献指南

我们欢迎任何形式的贡献！

### 提交流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 提交规范

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试
- `chore`: 杂项

### 报告问题

请使用 GitHub Issues 报告问题，包含：
- 问题描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息

---

## 许可证

本项目根据 [MIT 许可证](LICENSE) 授权。

---

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 状态图工作流
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL 向量扩展

---

**NovelGen-Enterprise** - 让 AI 成为你的写作伙伴
