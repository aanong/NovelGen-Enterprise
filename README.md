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
- **🌿 多线剧情分支 (Multi-Branch)**: 支持平行宇宙（IF 线）生成。系统自动维护不同分支的人物状态快照，确保在切换分支时，人物的心情、技能和关系能够正确回溯。
- **📉 动态上下文精炼 (Context Refiner)**: 集成 **pgvector** 向量数据库，实现基于语义的 RAG 检索，精准提取与当前剧情最相关的世界观和文风片段。
- **⚖️ 自动化逻辑审计**: 每一章都会经过 `Reviewer Agent` 的扫描，检查是否有逻辑硬伤或 OOC。
- **🔄 角色状态实时演化**: 系统会根据剧情自动更新角色的状态、物品和关系，并保存每个分支的历史快照。

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
    # 运行迁移脚本，自动创建表和更新 Schema
    python -m src.scripts.migrate_db upgrade
    ```

</details>

---

## 📖 详细教程与工作流程

现在，你可以通过 `python -m src.main` 配合 `init` 和 `run` 子命令来管理你的小说项目。

### 场景一：从零开始创作一部新小说

**步骤 1: 初始化项目**
使用 `init` 命令创建一部新小说，并从设定文档中导入初始数据。

```bash
python -m src.main init ./sample_inputs/novel_setup.txt \
  --title "无限神域" \
  --author "AI作家" \
  --description "一部关于虚拟现实与宇宙探索的史诗。"
```
系统会输出 `✨ 成功创建新小说 '无限神域' (ID: 1)`。**请记住这个 Novel ID**。

**步骤 2: 生成主线章节**
使用 `run` 命令和 `--novel-id` 来为指定的小说生成下一章。默认分支为 `main`。

```bash
python -m src.main run --novel-id 1
```
系统会自动加载小说 `1` 的当前进度，并生成新的章节。

### 场景二：创建平行世界 (IF 线)

假设在第 10 章，主角面临一个重大选择：是“拯救世界”还是“毁灭世界”。主线选择了“拯救”，但你想看看“毁灭”会发生什么。

**步骤 1: 切换分支并生成**
你可以直接指定一个新的 `--branch` 名称。系统会自动从当前进度的最近公共祖先（或上一章）开始分叉。

```bash
# 假设当前进度是第 10 章
# 我们想从第 11 章开始进入 "dark_timeline" 分支
python -m src.main run --novel-id 1 --branch "dark_timeline"
```

**系统内部逻辑**:
1.  系统检测到 `dark_timeline` 是新分支。
2.  它会查找上一章（第 10 章）的状态快照。
3.  加载第 10 章的人物状态（心情、装备、关系）。
4.  基于此状态生成第 11 章，并将结果标记为 `branch_id='dark_timeline'`。
5.  生成结束后，保存第 11 章的人物状态快照到 `dark_timeline` 分支。

**步骤 2: 继续该分支**
后续继续运行该命令，系统会自动沿着 `dark_timeline` 继续生成第 12 章、第 13 章...

```bash
python -m src.main run --novel-id 1 --branch "dark_timeline"
```

### 场景三：多小说管理

你可以随时初始化另一部完全独立的小说。

```bash
python -m src.main init ./sample_inputs/another_novel.txt \
  --title "都市奇缘"
```
假设这部小说被创建的 ID 是 `2`。现在你可以为它生成章节：

```bash
python -m src.main run --novel-id 2
```

### 场景四：导出与发布

使用 `export_novel.py` 脚本，并指定 `--novel-id` 和 `--branch` 来导出作品。

```bash
# 导出主线
python -m src.scripts.export_novel --novel-id 1 --output "无限神域_主线.md"

# 导出黑化线
python -m src.scripts.export_novel --novel-id 1 --branch "dark_timeline" --output "无限神域_黑化篇.md"
```

---

## 🖥️ GUI 可视化控制台

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
- 🌿 **分支视图**: (即将推出) 可视化查看剧情树和不同分支的走向。
- 📊 **实时看板**: 查看选定小说的章节数、角色数和大纲进度。
- 🚀 **一键生成**: 为当前选定的小说触发下一章生成任务。
- 📖 **在线阅读**: 浏览已生成的章节内容。

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
│   ├── scripts/        # 命令行工具 (导入/导出/大纲生成/数据库迁移)
│   └── main.py         # CLI 入口点
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
- [x] **多线剧情分支**: 支持生成多个结局路径，并自动管理人物状态快照
- [x] **智能大纲工具**: 支持大纲自动生成与交互式调整
- [x] **可视化界面**: 基于 FastAPI + Vue 的创作 Dashboard
