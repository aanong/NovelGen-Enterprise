# Anti-Gravity Rules: Enterprise Novel Generation System

## 1. 项目核心定义 (Project Context)
- **项目名称**: NovelGen-Enterprise (NGE)
- **核心目标**: 构建一个基于 LangGraph 的多智能体系统，能够模仿特定文风，生成情节连贯、人物立体、风格多变的长篇小说。
- **技术栈**:
  - **LLM**: Gemini-1.5-Pro/Gemini-3-Pro (主生成/长上下文), Deepseek-V3/R1 (逻辑推理/大纲构建/审查).
  - **Orchestration**: LangGraph (必须使用StateGraph), LangChain.
  - **Backend**: FastAPI (REST API), SQLAlchemy (ORM).
  - **Frontend**: Vue.js 3 (Dashboard), TailwindCSS.
  - **Database**: PostgreSQL (pgvector 插件用于RAG，JSONB 用于存储复杂状态).
  - **Infrastructure**: Docker & Docker Compose.
  - **Language**: Python 3.10+.

## 2. 架构设计原则 (Architecture Rules)

### 2.1 双模型协作策略 (Dual-Model Strategy)
- **Deepseek (Logic/Structure)**: 必须用于“大纲生成”、“剧情逻辑审查”、“人物性格一致性检查”、“章节拆解”节点。利用其推理能力防止剧情崩坏。
- **Gemini (Creative/Context)**: 必须用于“正文撰写”、“文风模仿学习”、“长文本扩写”节点。利用其超长上下文窗口保持整书的连贯性。

### 2.2 LangGraph 状态机设计 (State Management)
- **禁止**使用简单的线性 Chain。必须构建循环图 (Cyclic Graph)。
- **State Schema (全局状态)** 必须包含：
  - `novel_bible`: 世界观、核心设定、文风特征向量。
  - `character_state`: 动态的人物属性表（随章节更新，记录成长）。
  - `plot_progress`: 当前剧情进度指针（已完成/待完成）。
  - `memory_context`: 最近 N 章的摘要 + 全局关键伏笔。
  - `current_branch`: 当前剧情分支 ID (支持多线叙事)。

### 2.3 数据库设计 (PostgreSQL)
- **Strict Schema**:
  - `style_ref`: 存储原著片段的 Embedding (用于RAG检索文风)。
  - `characters`: 存储人物档案，包含 `personality_traits`, `relationships`, `evolution_log` (JSONB)。
  - `chapters`: 存储生成内容，包含 `branch_id` (分支标识) 和 `previous_chapter_id` (链表结构，用于回溯上下文)。
  - `plot_outlines`: 存储分章大纲，支持多分支 (`branch_id`)。

## 3. 核心功能实现规范 (Implementation Guidelines)

### 3.1 文风学习与细化 (Style Learning & Refinement)
- **Rule**: 不接受通用的 "Write like [Author]" 提示词。
- **Action**:
  1. 建立 `StyleAnalyzer` Agent，分析输入文本的：句式长度分布、常用修辞、对话/旁白比例、情绪色调。
  2. 在生成正文前，检索与当前场景相似的“参考文本”作为 Few-Shot Examples 注入 Prompt。
  3. **动态风格**: 根据场景类型（战斗/言情/悬疑）和视角人物，动态切换 System Prompt 中的 Tone 设定。

### 3.2 人物立体与成长 (Character Depth)
- **Rule**: 人物不能是静态的。
- **Action**:
  1. 每次生成章节前，必须读取 `character_state`。
  2. 章节生成后，触发 `CharacterEvolver` 节点，分析该章节发生的事件是否改变了人物的心境或关系，并更新数据库。
  3. 对话生成必须基于人物的 `MBTI` 或 `BigFive` 属性以及当前的 `Mood` 状态。

### 3.3 剧情防崩与连贯 (Plot Coherence)
- **Rule**: 严禁脱离大纲 (Out-of-Outline) 的幻觉。
- **Action**:
  1. **Outline Expansion**: 用户输入简单大纲 -> Deepseek 扩充为“细纲”（精确到场面调度）-> 存入 DB。
  2. **Pre-Check**: 写每一章前，Agent 必须回答：“这一章如何服务于主线？上一章的结尾是什么？”
  3. **Post-Check (Critic)**: 生成后，Deepseek 必须作为 Critic 检查：“是否有逻辑漏洞？人物是否OOC (Out of Character)？” 若失败，回滚重写。

### 3.4 全书大纲预生成 (Full Outline Pre-generation)
- **Rule**: 在开始正文写作前，必须生成全书（或当前卷）的分章大纲并存入数据库。
- **Action**:
  1. 用户提供核心梗概 (Core Synopsis) 和预计章节数。
  2. Architect Agent 将梗概拆解为具体的 `PlotOutline` 序列，包含每章的 `scene_description` 和 `key_conflict`。
  3. 存入 `plot_outlines` 表，作为后续写作的导航地图。
  4. 支持 **Refine Mode**: 允许用户指定起始章节，对后续大纲进行增量调整。

### 3.5 多线剧情分支 (Multi-Branch Storyline)
- **Rule**: 系统必须支持平行宇宙（IF 线）的生成。
- **Action**:
  1. 数据库 `chapters` 和 `plot_outlines` 表通过 `branch_id` 区分不同分支。
  2. 上下文加载时，通过 `previous_chapter_id` 链表回溯，确保只加载当前分支的历史。
  3. 提供 API 接口切换当前分支，实现不同走向的续写。

### 3.6 可视化交互 (Visual Interaction)
- **Rule**: 提供直观的界面用于监控和干预。
- **Action**:
  1. **Dashboard**: 展示章节列表、角色状态卡片、大纲进度条。
  2. **Control**: 提供“生成下一章”、“暂停”、“重试”按钮。
  3. **Reader**: 内置 Markdown 渲染器，实时预览生成效果。

## 4. 代码规范 (Coding Standards)

- **Type Hinting**: 所有函数必须包含 Python 类型注解。
- **Modular Agents**: 每个 Agent (Node) 必须封装为独立的 Class 或 Callable，便于在 Graph 中编排。
- **Error Handling**: LLM 调用必须包含重试机制 (Exponential Backoff) 和 fallback 策略。
- **Environment**: 使用 `.env` 管理 API Keys (`GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `POSTGRES_URL`).
- **Containerization**: 必须维护 `Dockerfile` 和 `docker-compose.yml`，确保环境一致性。

## 5. 提示词工程策略 (Prompt Engineering Strategy)

- **Role-Playing**: 必须为每个 Agent 设定具体的角色（如：“你是一个严谨的网文主编”、“你是一个擅长细腻描写的言情作家”）。
- **CoT (Chain of Thought)**: 在复杂逻辑任务（大纲细化）中，强制模型输出 `<thinking>` 标签。
- **Structured Output**: 尽可能要求模型返回 JSON 格式，以便程序解析（使用 Pydantic Parser）。

---

## 6. 开发路线图 (Step-by-Step Execution for AI)

如果你（AI）要开始写代码，请遵循以下顺序：
1. **Setup**: 初始化 PostgreSQL 表结构 (`alembic`) 和 LangChain 基础配置。 (✅ Completed)
2. **Module 1 (Learner)**: 实现文本分析 Agent，提取文风特征存入 PGVector。 (✅ Completed)
3. **Module 2 (Architect)**: 实现大纲扩充与拆解 Agent (Deepseek)。 (✅ Completed)
4. **Module 3 (Writer)**: 实现基于 LangGraph 的写作循环 (Plan -> Write -> Review -> Revise)。 (✅ Completed)
5. **Module 4 (Memory)**: 实现人物状态更新与上下文检索机制。 (✅ Completed)
6. **Module 5 (API & UI)**: 实现 FastAPI 后端与 Vue 前端，提供可视化操作界面。 (✅ Completed)
7. **Module 6 (Optimization)**: 引入 Docker 部署，优化大纲生成策略 (Refine Mode)。 (✅ Completed)
