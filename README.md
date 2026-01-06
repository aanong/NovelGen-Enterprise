# NovelGen-Enterprise (NGE)

基于 LangGraph 的企业级多智能体长篇小说生成系统 (Enterprise Novel Generation System)。
本项目专为追求高质量、逻辑严密的长篇小说创作而设计，利用 **Deepseek-V3/R1** 进行底层逻辑规划，**Gemini-1.5/3 Pro** 进行文学性正文创作。

## 🌟 核心特性
- **双模型深度协作 (Dual-Model Synergy)**: 
  - `Architect` & `Critic` (Deepseek): 确保大纲严谨、逻辑闭环、无 OOC (Out of Character)。
  - `Writer` (Gemini): 依托长上下文窗口，实现细腻的场景描写与风格化叙述。
- **智能上下文精炼 (ContextRefiner)**: 
  - 自动从海量设定中提取当前章节最相关的规则与伏笔，显著降低 Token 消耗并提升生成精准度。
- **多维角色演化 (Character Evolution)**: 
  - 动态跟踪人物心境、受损状态及人际关系矩阵，确保角色在长篇故事中具有持续的成长感。
- **全流程逻辑审计 (LogicAudit)**: 
  - 每一章节生成后都会进行多维度逻辑扫描，所有评审意见均持久化至数据库供复盘优化。
- **一键文档初始化 (One-Click Onboarding)**: 
  - 提供 `LearnerAgent`，支持通过纯文本设定文档自动初始化项目。

## 📂 项目结构
```bash
src/
├── agents/         # 智能体中心 (Architect, Writer, Reviewer, Learner, Analyzer)
├── db/             # 数据库层 (SQLAlchemy 模型, pgvector RAG 支持)
├── schemas/        # 数据协议定义 (Pydantic Models)
├── scripts/        # 实用脚本 (数据导入、Seed 填充)
├── graph.py        # LangGraph 核心状态机逻辑
└── main.py         # 引擎运行入口
```

## 🚀 完整使用教程 (Complete Tutorial)

### 1. 环境搭建
首先，确保你的系统中安装了 **Python 3.10+** 和 **PostgreSQL** (推荐安装 `pgvector` 插件以获得最佳 RAG 体验)。

```bash
# 1. 克隆项目
git clone https://github.com/aanong/NovelGen-Enterprise.git
cd NovelGen-Enterprise

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入：
# GOOGLE_API_KEY (用于 Gemini)
# DEEPSEEK_API_KEY (用于 Deepseek)
# POSTGRES_URL (格式: postgresql://user:pass@localhost:5432/dbname)
```

### 2. 数据库初始化
在第一次运行前，需要建立数据库表结构：

```bash
python -m src.db.init_db
```

### 3. 初始化小说项目 (从中文文档导入)
这是 NGE 的核心优势：你只需要准备一个包含小说设定、人物、大纲的中文 `.txt` 文件，系统将自动进行结构化。

**示例设定文件 (`my_novel.txt`):**
```text
## 小说大纲
第一章：觉醒。萧炎在纳兰嫣然的讥笑中开启了神秘戒指。
第二章：药老现身。灵魂态的药老决定传授焚诀。

## 人物设定
萧炎：定位主角，坚毅，拥有报仇欲望。
纳兰嫣然：云岚宗少宗主，高傲自大。

## 世界观
力量等级：斗之气、斗者、斗师...
核心道具：骨灵冷火。
```

**运行导入脚本:**
```bash
python -m src.scripts.import_novel ./sample_inputs/novel_setup.txt
```

### 4. 启动生成引擎
导入完成后，执行主程序开始生成正文。系统将自动读取数据库进度，按章节顺序进行 “规划 -> 上下文精炼 -> 撰写 -> 逻辑审计 -> 人物演变” 的往复循环。

```bash
python -m src.main
```

## 🛠 开发与调试
- **查看历史日志**: 所有的生成记录和 LogicAudit 建议都存储在数据库的 `chapters` 和 `logic_audits` 表中。
- **自定义文风**: 可以在 `src/agents/writer.py` 或初始化文档中通过 Few-shot Examples 调整 Gemini 的文学风格。

## 📌 注意事项
- 确保 Postgres 服务已启动并创建了对应的数据库。
- 长篇写作推荐使用 Gemini-1.5-Pro 以获得更连贯的上下文记忆。
