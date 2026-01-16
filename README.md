# NovelGen-Enterprise (NGE)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-LangGraph-purple)]()
[![Queue](https://img.shields.io/badge/Queue-Celery%20%7C%20Redis-red)]()

**NovelGen-Enterprise (NGE)** 是一款企业级、高可用的长篇小说生成系统。基于 **LangGraph** 的多智能体协作架构，采用 **Gemini** 双模型协同，解决长篇生成中的逻辑连贯性、人物一致性和风格统一性问题。

系统集成 **Celery + Redis** 分布式任务队列和 **PostgreSQL (pgvector)** 向量数据库，支持多用户、多项目、多分支的高并发生成。

---

## 目录

- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [完整使用流程](#完整使用流程)
- [API 接口文档](#api-接口文档)
- [剧情支线管理](#剧情支线管理)
- [人物演化系统](#人物演化系统)
- [伏笔管理系统](#伏笔管理系统)
- [资料库管理](#资料库管理)
- [项目结构](#项目结构)
- [Antigravity 规则系统](#antigravity-规则系统)
- [故障排除](#故障排除)
- [许可证](#许可证)

---

## 核心特性

### 智能写作引擎

| 功能 | 说明 |
|------|------|
| **双模型协同** | Gemini 负责逻辑审查与正文撰写 |
| **LangGraph 状态机** | 循环图结构：Plan → Write → Review → Evolve |
| **RAG 上下文增强** | pgvector 语义检索，精准提取世界观设定 |
| **Antigravity Rules** | 防止人物 OOC、逻辑硬伤、世界观崩坏 |

### 人物立体化系统

| 功能 | 说明 |
|------|------|
| **动态性格维度** | courage、rationality、empathy、openness、trust 五维度 |
| **价值观演化** | 正义、复仇、家族等价值观随剧情变化 |
| **能力成长曲线** | 支持线性/指数/阶梯/波动等成长模式 |
| **人物弧光** | 正向成长/负向堕落/扁平弧光/彻底转变 |
| **关键事件系统** | 创伤、顿悟、抉择、背叛等事件自动检测 |
| **技能掌握阶段** | NOVICE → COMPETENT → PROFICIENT → MASTER → TRANSCENDENT |
| **思想成熟度** | 追踪认知深度、情绪成熟度、决断力等 |

### 剧情管理系统

| 功能 | 说明 |
|------|------|
| **主支线交织** | 支持主线与多条支线的交织管理 |
| **剧情支线** | 独立管理支线人物、道具、引入时机 |
| **伏笔生命周期** | 结构化追踪伏笔埋设、推进、回收 |
| **节奏控制** | RhythmAnalyzer 防止连续高潮或拖沓 |
| **多分支剧情** | IF 线支持，自动维护分支状态快照 |

### 文学增强系统

| 功能 | 说明 |
|------|------|
| **典故注入** | AllusionAdvisor 主动推荐文学典故 |
| **写作技法** | 白描、蒙太奇、意识流等场景化建议 |
| **文风定制** | 每个角色可配置独特说话风格 |
| **世界观守护** | WorldConsistencyGuard 检测违规内容 |

### 企业级能力

| 功能 | 说明 |
|------|------|
| **分布式队列** | Celery + Redis 异步任务处理 |
| **SSE 流式输出** | 实时推送生成过程 |
| **RESTful API** | FastAPI + Swagger 文档 |
| **Docker 部署** | 一键容器化部署 |

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
│  │  NovelService │ PlotBranchService │ CharacterService      │  │
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
│ LoadContext│ ──────► │    Plan    │ ────────► │   Refine   │
│    Node    │         │    Node    │           │    Node    │
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

### 工作流节点说明

| 节点 | Agent | 功能 |
|------|-------|------|
| LoadContext | - | 加载角色状态、世界观、历史摘要 |
| Plan | ArchitectAgent | 规划章节内容、伏笔策略 |
| Refine | VectorStore | RAG 检索设定、典故、文风参考 |
| Write | WriterAgent | 生成章节正文 |
| Review | ReviewerAgent | 逻辑审查、OOC 检测 |
| Evolve | CharacterEvolver | 更新人物状态、保存章节 |

---

## 快速开始

### 前置要求

**Docker 部署（推荐）**
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存

**本地开发**
- Python 3.10+
- PostgreSQL 16+ (pgvector 扩展)
- Redis 7+

### 方式一：Docker 一键部署

```bash
git clone https://github.com/your-org/NovelGen-Enterprise.git
cd NovelGen-Enterprise
docker-compose up -d
```

### 方式二：本地开发环境

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥和数据库信息

# 4. 启动服务
# 终端1: FastAPI
uvicorn src.main:app --reload

# 终端2: Celery Worker
celery -A src.worker.celery_app worker --loglevel=info
```

---

## 环境配置

创建 `.env` 文件：

```env
# 必需配置
GOOGLE_API_KEY=your_gemini_api_key
POSTGRES_URL=postgresql://user:pass@localhost:5432/novelgen

# 可选配置
REDIS_URL=redis://localhost:6379/0
GEMINI_MODEL=models/gemini-2.0-flash
GEMINI_TEMPERATURE=0.8

# 写作配置
MIN_CHAPTER_LENGTH=2000
TARGET_CHAPTER_LENGTH=3000

# Antigravity 规则
MAX_RETRY_LIMIT=3
RECENT_CHAPTERS_CONTEXT=3
```

---

## 完整使用流程

### 步骤1：创建小说项目

```bash
curl -X POST "http://127.0.0.1:8000/api/novels/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "仙道无极",
    "author": "青云子",
    "description": "一个少年踏上修仙之路的故事"
  }'
```

### 步骤2：导入小说设定

```bash
python -m src.scripts.manage_references import my_data.json --novel-id 1
```

### 步骤3：生成章节大纲

```bash
python -m src.scripts.generate_outline --novel-id 1 --chapters 10
```

### 步骤4：运行章节生成

```bash
curl -X POST "http://127.0.0.1:8000/api/generate/trigger?novel_id=1"
```

### 步骤5：导出小说

```bash
python -m src.scripts.export_novel --novel-id 1 --format txt --output novel.txt
```

---

## API 接口文档

访问 `http://127.0.0.1:8000/docs` 查看完整 Swagger 文档。

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/novels/` | GET/POST | 小说管理 |
| `/api/novels/{id}/chapters/` | GET | 获取章节列表 |
| `/api/characters/` | GET/POST | 人物管理 |
| `/api/outlines/` | GET/POST | 大纲管理 |
| `/api/generate/trigger` | POST | 触发生成任务 |
| `/api/generate/stream/{task_id}` | GET | SSE 流式输出 |

---

## 剧情支线管理

NGE 支持完整的剧情支线管理，包括支线与人物、道具的关联。

### 创建剧情支线

```bash
curl -X POST "http://127.0.0.1:8000/api/novels/1/branches/full" \
  -H "Content-Type: application/json" \
  -d '{
    "branch_key": "revenge_arc",
    "name": "复仇之路",
    "description": "主角为师门复仇的支线",
    "branch_type": "side",
    "introduce_at_chapter": 5,
    "introduce_condition": "当主角发现师门灭门真相时",
    "priority": 8,
    "stages": [
      {"name": "发现真相", "chapter_range": [5, 10]},
      {"name": "追查仇人", "chapter_range": [11, 20]},
      {"name": "最终对决", "chapter_range": [21, 25]}
    ],
    "characters": [
      {"character_id": 1, "role_in_branch": "主导者", "involvement_level": "core"}
    ],
    "items": [
      {"item_id": 5, "role_in_branch": "关键证物", "importance": "critical"}
    ]
  }'
```

### 支线 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/novels/{id}/branches` | GET/POST | 支线管理 |
| `/api/novels/{id}/branches/active` | GET | 获取指定章节的活跃支线 |
| `/api/branches/{id}` | GET/PUT/DELETE | 支线详情操作 |
| `/api/branches/{id}/activate` | POST | 激活支线 |
| `/api/branches/{id}/complete` | POST | 完成支线 |
| `/api/branches/{id}/characters` | GET/POST | 支线人物关联 |
| `/api/branches/{id}/items` | GET/POST | 支线道具关联 |

---

## 人物演化系统

NGE 提供深度的人物演化系统，让角色随剧情自然成长。

### 演化维度

**性格维度** (0.0 - 1.0)
- `courage` - 勇气
- `rationality` - 理性
- `empathy` - 同理心
- `openness` - 开放性
- `trust` - 信任

**价值观** (0.0 - 1.0)
- 正义、复仇、家族、自由、权力、爱情等

**能力系统**
- 等级：1-10
- 熟练度：0.0-1.0
- 掌握阶段：NOVICE → MASTER → TRANSCENDENT
- 成长曲线：线性/指数/阶梯/波动

### 关键事件类型

| 类型 | 说明 |
|------|------|
| `trauma` | 创伤事件（亲人死亡、重大失败） |
| `epiphany` | 顿悟时刻（突破认知） |
| `decision` | 重大决定（改变命运） |
| `loss` | 失去（重要的人、物、信仰） |
| `gain` | 获得（力量、认可、真相） |
| `betrayal` | 背叛 |
| `sacrifice` | 牺牲 |
| `confrontation` | 直面恐惧 |

### 人物弧光类型

| 类型 | 说明 |
|------|------|
| `positive` | 正向成长（懦弱→勇敢） |
| `negative` | 负向堕落（善良→黑化） |
| `flat` | 扁平弧光（坚守信念） |
| `transformation` | 彻底转变（身份认知颠覆） |

---

## 伏笔管理系统

### 伏笔生命周期

```
planted (埋设) → advanced (推进) → resolved (回收)
                                  ↘ abandoned (放弃)
```

### 伏笔自动处理

1. **Summarizer** 从章节内容提取新伏笔
2. **Evolver** 更新伏笔状态
3. **Architect** 在规划时考虑伏笔回收时机

---

## 资料库管理

### 导入资料

```bash
# 导入全局资料库
python -m src.scripts.manage_references import data/global_references.json

# 为特定小说导入
python -m src.scripts.manage_references import data/refs.json --novel-id 1

# 覆盖更新
python -m src.scripts.manage_references import data/refs.json --force
```

### 资料格式

```json
[
  {
    "title": "修仙境界体系",
    "content": "练气期、筑基期、金丹期...",
    "source": "修仙通识",
    "category": "world_setting",
    "tags": ["境界", "修仙"]
  }
]
```

### 资料类别

| category | 说明 |
|----------|------|
| `world_setting` | 世界观设定 |
| `plot_trope` | 剧情套路 |
| `character_archetype` | 人物原型 |
| `style` | 文风参考 |

---

## 项目结构

```
src/
├── agents/                 # AI 智能体
│   ├── architect.py        # 大纲规划
│   ├── writer.py           # 正文撰写
│   ├── reviewer.py         # 逻辑审查
│   ├── evolver.py          # 人物演化
│   ├── summarizer.py       # 章节摘要
│   ├── allusion_advisor.py # 典故顾问
│   ├── rhythm_analyzer.py  # 节奏分析
│   └── world_guard.py      # 世界观守护
├── api/                    # FastAPI 路由
│   └── routes/
│       ├── novels.py
│       ├── chapters.py
│       ├── characters.py
│       ├── plot_branches.py
│       └── ...
├── db/                     # 数据库层
│   ├── models.py           # ORM 模型
│   ├── vector_store.py     # 向量存储
│   └── *_repository.py     # 仓储模式
├── nodes/                  # LangGraph 节点
│   ├── loader.py
│   ├── planner.py
│   ├── refiner.py
│   ├── writer.py
│   ├── reviewer.py
│   └── evolver.py
├── schemas/                # Pydantic 模型
│   ├── state.py            # NGEState 定义
│   └── literary.py         # 文学元素
├── services/               # 业务逻辑层
├── scripts/                # CLI 脚本
├── config.py               # 配置管理
├── graph.py                # LangGraph 工作流
└── worker.py               # Celery Worker
```

---

## Antigravity 规则系统

Antigravity Rules 是 NGE 的核心质量保障机制。

| 规则 | 说明 |
|------|------|
| **Rule 1** | 世界观一致性：所有内容必须符合 NovelBible 设定 |
| **Rule 2** | 人物灵魂锚定：角色有禁忌行为列表，绝对禁止违反 |
| **Rule 3** | 上下文滑窗：默认加载最近 3 章摘要，最多 10 章 |
| **Rule 4** | 输出清洗：自动清除 `<think>` 等标签 |
| **Rule 5** | 循环熔断：最多重试 3 次，超限自动降级修复 |
| **Rule 6** | 场景约束：动作场景短句、对话场景高对话占比 |

---

## 故障排除

### 常见问题

**Q: LLM 调用超时**
- 检查 API 配额
- 增加 timeout 配置

**Q: 向量检索无结果**
- 检查 embedding 是否生成
- 确认 pgvector 扩展已安装

**Q: 人物 OOC**
- 检查 `character_anchors` 配置
- 增加禁忌行为列表

**Q: 章节不连贯**
- 增加 `RECENT_CHAPTERS_CONTEXT` 配置

### 日志调试

```python
import logging
logging.getLogger("src.agents").setLevel(logging.DEBUG)
```

---

## 开发指南

### 代码风格

- 使用 `black` 格式化
- 使用 `isort` 排序导入
- 所有函数需有类型注解和中文文档字符串

### 运行测试

```bash
python -m src.scripts.test_all_flows
```

### 验证优化

```bash
python -m src.scripts.verify_optimization
```

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 PR

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 授权。

---

**NovelGen-Enterprise** - 让 AI 成为你的写作伙伴
