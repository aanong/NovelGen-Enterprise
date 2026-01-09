# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Model](https://img.shields.io/badge/LLM-Gemini-Pro%20%7C%20DeepSeek-V3-orange)](https://deepseek.com/)

**NovelGen-Enterprise (NGE)** 是一款专为大规模、高逻辑性长篇小说设计的企业级多智能体生成引擎。它支持**同时管理和创作多部小说**，并为每个项目提供独立的数据隔离。

它采用了创新的 **"Antigravity Rules" (反重力规则)**，通过 **本地 DeepSeek (逻辑中枢)** 与 **云端 Gemini (文学工匠)** 的协同，彻底解决了 AI 创作长篇小说时常见的"逻辑坠毁"、"人物走形"和"上下文断裂"问题。

---

## ✨ 核心亮点

- **📚 多小说项目管理**: 可同时创建、管理和生成多部小说，每个项目的数据（角色、大纲、章节）完全隔离。
- **🧠 逻辑与文学分离**: 所有的剧情拆解、逻辑审计由推理能力极强的 **DeepSeek** 负责；所有的文风模仿、细节描写由具备超长上下文的 **Gemini** 负责。
- **📉 动态上下文精炼 (Context Refiner)**: 集成 **pgvector** 向量数据库，实现基于语义的 RAG 检索，精准提取与当前剧情最相关的世界观和文风片段。
- **⚖️ 自动化逻辑审计**: 每一章都会经过 `Reviewer Agent` 的扫描，检查是否有逻辑硬伤或 OOC。
- **🔄 角色状态实时演化**: 系统会根据剧情自动更新角色的状态、物品和关系，确保人物随故事成长。

---

## 🛠 快速开始

### 1. 环境配置
无论是使用 Docker 还是本地安装，请先完成环境配置。

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key 和数据库连接信息
# 如果使用 Docker, 数据库 URL 应为: postgresql://postgres:password@db:5432/novelgen
```

### 2. 启动方式

<details>
<summary><b>🐳 方式一：Docker 极速启动 (推荐)</b></summary>

1.  **启动服务**:
    ```bash
    docker-compose up -d --build
    ```
2.  **进入容器**:
    ```bash
    docker-compose exec app bash
    ```
    *后续所有 CLI 命令均在容器内执行。*

</details>

<details>
<summary><b>💻 方式二：本地手动安装</b></summary>

1.  **环境依赖**:
    *   Python 3.10+
    *   PostgreSQL 16+ (需安装 `pgvector` 扩展)
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **初始化数据库**:
    首次运行时，需要创建数据库表结构。
    ```bash
    # 自动生成迁移脚本 (仅在模型变更后需要)
    python -m alembic revision --autogenerate -m "Initial migration"
    
    # 应用迁移
    python -m alembic upgrade head
    ```

</details>

---

## 📖 完整工作流程 (CLI)

现在，你可以通过 `python -m src.main` 配合 `init` 和 `run` 子命令来管理你的小说项目。

### 步骤 1: 创建第一部小说并导入设定

使用 `init` 命令创建一部新小说，并从设定文档中导入初始数据。

```bash
python -m src.main init ./sample_inputs/novel_setup.txt \
  --title "无限神域" \
  --author "AI作家" \
  --description "一部关于虚拟现实与宇宙探索的史诗。"
```
系统会输出 `✨ 成功创建新小说 '无限神域' (ID: 1)`。**请记住这个 Novel ID**。

### 步骤 2: 为小说生成章节

使用 `run` 命令和 `--novel-id` 来为指定的小说生成下一章。

```bash
python -m src.main run --novel-id 1
```
系统会自动加载小说 `1` 的当前进度，并生成新的章节。

### 步骤 3: 创建并管理第二部小说

你可以随时初始化另一部完全独立的小说。

```bash
python -m src.main init ./sample_inputs/another_novel.txt \
  --title "都市奇缘"
```
假设这部小说被创建的 ID 是 `2`。现在你可以为它生成章节：

```bash
python -m src.main run --novel-id 2
```

### 步骤 4: 更新现有小说的设定

如果你想为一个已存在的小说追加或更新设定，同样使用 `init` 命令并提供 `--novel-id`。

```bash
python -m src.main init ./sample_inputs/updated_setup.txt --novel-id 1
```

### 步骤 5: 导出小说为 Markdown

使用 `export_novel.py` 脚本，并指定 `--novel-id` 来导出作品。

```bash
python -m src.scripts.export_novel --novel-id 1 --output "无限神域.md"
```

---

##  GUI 方式 (推荐)

我们提供了一个基于 Web 的控制台，用于监控进度、阅读章节和触发生成。

1.  **启动 FastAPI 服务器**:
    ```bash
    # 在 Docker 容器内或本地环境中运行
    python -m src.api.run_server
    ```
2.  **访问 Web 界面**:
    打开浏览器访问: [http://localhost:8000](http://localhost:8000)

**GUI 功能**:
- 📚 **小说管理**: 创建新小说，查看和切换不同的小说项目。
- 📊 **实时看板**: 查看选定小说的章节数、角色数和大纲进度。
- 🚀 **一键生成**: 为当前选定的小说触发下一章生成任务。
- 📖 **在线阅读**: 浏览已生成的章节内容。

---

## 💡 进阶技巧

### 如何指定生成分支？
`run` 命令和 `export` 脚本都支持 `--branch` 参数，用于多线叙事。

```bash
# 为小说1的 "if-story" 分支生成章节
python -m src.main run --novel-id 1 --branch "if-story"

# 导出该分支
python -m src.scripts.export_novel --novel-id 1 --branch "if-story"
```

### 如何重写某个章节？
1.  **API/数据库操作**: 通过 API 或直接在数据库中删除 `chapters` 表中对应的章节记录。
2.  **重新生成**: 再次运行 `run` 命令，系统会发现该章节缺失并重新生成。

---

## 📁 项目结构
```
.
├── src/
│   ├── agents/         # 核心智能体 (Architect, Writer, Reviewer, Learner)
│   ├── api/            # FastAPI 后端与前端静态文件
│   ├── db/             # 数据库模型 (SQLAlchemy) 与初始化
│   ├── graph/          # LangGraph 状态机定义
│   ├── schemas/        # Pydantic 数据模型 (State, Style等)
│   ├── scripts/        # 命令行工具 (导入/导出/大纲生成)
│   └── main.py         # CLI 入口点
├── alembic/            # 数据库迁移脚本
├── sample_inputs/      # 示例小说设定文件
├── .env.example        # 环境变量模板
├── docker-compose.yml  # Docker 配置
└── README.md           # 项目说明
```

---

## 🏗 开源路线图
- [x] **设定审查系统**: 使用 Gemini 3 Pro 进行逻辑审查
- [x] **RAG 向量搜索**: 实现世界观设定的语义检索 (pgvector)
- [x] **角色状态演化**: 实时更新技能、物品消耗及人际关系
- [x] **多线剧情分支**: 支持生成多个结局路径
- [x] **智能大纲工具**: 支持大纲自动生成与交互式调整
- [x] **可视化界面**: 基于 FastAPI + Vue 的创作 Dashboard

---

## 🤝 贡献指南
欢迎提交 Issue 和 Pull Request！

---

## 📄 License
MIT License

---

*本项目遵循 Antigravity Rules 治理准则，确保每一行文字都具有灵魂。*
