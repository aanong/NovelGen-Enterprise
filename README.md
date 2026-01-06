# NovelGen-Enterprise (NGE)

基于 LangGraph 的企业级多智能体长篇小说生成系统 (Enterprise Novel Generation System)。
利用 **Deepseek-V3/R1** 进行严密逻辑推理与大纲架构，利用 **Gemini-1.5/3 Pro** 进行高质量长文本创作。

## 核心特性
- **双模型协作 (Dual-Model Strategy)**: 
  - `Architect` & `Critic` (Deepseek): 负责大纲细化、逻辑审计、防崩坏检查。
  - `Writer` (Gemini): 负责基于 RAG 的文风模仿、场景描写与正文生成。
- **动态状态机 (Stateful Graph)**: 采用 LangGraph 构建循环图，而非线性链，支持“写-审-改”闭环。
- **深度记忆 (Deep Context)**:
  - `NovelBible`: 存储世界观、战力体系、地理设定。
  - `CharacterRelationship`: 动态演化的人物关系矩阵。
  - `ContextRefiner`: 智能检索本章最相关的伏笔与规则，压缩上下文 Token。
- **企业级可观测性**: 全程记录 `LogicAudit` 审计日志。

## 项目结构
```bash
src/
├── agents/         # 智能体实现 (Architect, Writer, Reviewer, StyleAnalyzer)
├── db/             # 数据库层 (SQLAlchemy Models, pgvector)
├── schemas/        # Pydantic 数据结构定义
├── graph.py        # LangGraph 状态机定义 (Core Logic)
└── main.py         # 程序入口
```

## 快速开始 (Getting Started)

### 1. 环境准备
确保已安装 Python 3.10+ 和 PostgreSQL (需启用 `pgvector` 插件)。

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入 API Keys
# GOOGLE_API_KEY=...
# DEEPSEEK_API_KEY=...
# POSTGRES_URL=postgresql://user:pass@localhost/novelgen
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 初始化数据库
我们提供了自动初始化脚本，用于创建 `characters`, `novel_bible`, `chapters` 等核心表。

```bash
python -m src.db.init_db
```

### 4. 运行生成引擎
启动主程序，开始根据预设状态生成小说。

```bash
python -m src.main
```

## 工作流程 (Workflow)

1. **Load Context**: 从数据库加载最新的人物状态、世界观设定。
2. **Plan (Architect)**: Deepseek 基于当前剧情进度，生成本章的“微型大纲” (场面调度、核心冲突)。
3. **Refine Context**: 系统自动从 `NovelBible` 中检索与本章设定最相关的规则（如魔法属性、特定道具），注入上下文。
4. **Write (Writer)**: Gemini 根据大纲和精炼后的上下文，撰写正文初稿。
5. **Review (Critic)**: Deepseek 审查初稿逻辑，若不通过则打回重写 (Revise Loop)。
6. **Evolve**: 章节通过后，更新人物心理状态、关系矩阵，并持久化章节内容。
