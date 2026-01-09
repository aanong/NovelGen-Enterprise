# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Model](https://img.shields.io/badge/LLM-Gemini--2.0%20%7C%20DeepSeek--R1-orange)](https://deepseek.com/)

**NovelGen-Enterprise (NGE)** 是一款专为大规模、高逻辑性长篇小说设计的企业级多智能体生成引擎。

它采用了创新的 **"Antigravity Rules" (反重力规则)**，通过 **本地 DeepSeek (逻辑中枢)** 与 **云端 Gemini (文学工匠)** 的协同，彻底解决了 AI 创作长篇小说时常见的"逻辑坠毁"、"人物走形"和"上下文断裂"问题。

---

## ✨ 核心亮点

- **🧠 逻辑与文学分离**: 所有的剧情拆解、逻辑审计由推理能力极强的 **DeepSeek-R1** 负责；所有的文风模仿、细节描写由具备超长上下文的 **Gemini-2.0** 负责。
- **📉 动态上下文精炼 (Context Refiner)**: 集成 **pgvector** 向量数据库，实现基于语义的 RAG 检索。系统不再一股脑填塞所有设定，而是精准提取与当前剧情最相关的世界观和文风片段。
- **⚖️ 自动化逻辑审计**: 每一章都会经过 `Reviewer Agent` 的毒舌扫描，检查是否有逻辑硬伤或 OOC。
- **🔄 角色状态实时演化**: 真正的动态世界！系统会根据剧情自动更新角色的**技能列表**、**物品背包**（获得/消耗）以及**人际关系**（亲密度/结盟/敌对），确保人物随故事成长。
- **🔍 AI 设定审查**: 内置 `review_setup.py` 脚本，可在导入前对设定进行深度逻辑审查和自动完善。

---

## 🛠 快速开始

### 方式一：Docker 极速启动 (推荐)
这是最快、最稳定的方式，无需手动安装数据库。

1. **安装 Docker**: 确保已安装 Docker Desktop。
2. **配置环境**:
   ```bash
   cp .env.example .env
   # 编辑 .env 填入 API Key
   # 数据库 URL 请使用: postgresql://postgres:password@db:5432/novelgen
   ```
3. **启动服务**:
   ```bash
   docker-compose up -d
   ```
4. **进入容器**:
   ```bash
   docker-compose exec app bash
   ```
   *后续所有命令均在容器内执行。*

### 方式二：本地手动安装
<details>
<summary>点击展开详细步骤</summary>

### 1. 环境依赖
*   **Python**: 3.10+ (推荐 3.12)
*   **Database**: PostgreSQL 16+ (必须安装 `pgvector` 扩展以支持向量检索)
*   **Local LLM**: [Ollama](https://ollama.com/) (需运行 `ollama run deepseek-r1:7b`)

### 2. 安装依赖
```bash
git clone https://github.com/aanong/NovelGen-Enterprise.git
cd NovelGen-Enterprise
pip install -r requirements.txt
```

### 3. 配置秘钥
复制并编辑 `.env` 文件：
```bash
cp .env.example .env
```
确保包含以下配置项：
*   `GOOGLE_API_KEY`: 申请 [Google AI Studio](https://aistudio.google.com/)
*   `POSTGRES_URL`: 你的数据库连接字符串

</details>

### 4. 初始化数据库
```bash
python -m src.db.init_db
```

---

## ⚡ 性能与成本优化指南

为了在企业级应用中平衡效果与成本，建议遵循以下最佳实践：

### 1. 增量大纲生成 (降低成本)
不要一次性生成 100 章大纲。建议采用 **"5+N" 策略**：
- 先生成前 5 章：`python -m src.scripts.generate_outline ... --chapters 5`
- 试写满意后，使用 `--refine` 模式续写后续章节。
- **收益**: 避免因大纲方向错误导致的 Token 浪费，节省约 80% 的试错成本。

### 2. 设定审查缓存 (提升效率)
`review_setup.py` 运行较慢。如果设定文件未修改，请直接使用上次生成的 `enhanced_setup.txt`，无需重复审查。

### 3. 数据库连接池 (提升并发)
项目已配置 SQLAlchemy 连接池。在生产环境中，建议在 `.env` 中调整 `DB_POOL_SIZE` 以匹配并发写作者数量。

---

## 📖 完整工作流程

### 步骤 1: 审查设定（推荐）
在导入设定前，先用 AI 进行逻辑审查：
```bash
python -m src.scripts.review_setup ./sample_inputs/novel_setup.txt
```

这会生成：
- `./reviewed_setups/review_report.md` - 详细的审查报告
- `./reviewed_setups/enhanced_setup.txt` - 完善后的设定

审查内容包括：
- ✅ 修炼体系逻辑检查
- ✅ 人物关系网补充
- ✅ 世界地理完善
- ✅ 大纲节奏优化

### 步骤 2: 导入设定
使用完善后的设定：
```bash
python -m src.scripts.import_novel ./reviewed_setups/enhanced_setup.txt
```

或使用原始设定：
```bash
python -m src.scripts.import_novel ./sample_inputs/novel_setup.txt
```

### 步骤 3: 生成/调整大纲
在开始写作前，先生成全书大纲：
```bash
python -m src.scripts.generate_outline ./sample_inputs/novel_setup.txt --chapters 20
```

### 步骤 4: 开启创作 (CLI 方式)
系统会自动识别当前进度并生成下一章：
```bash
python -m src.main --run
```

### 步骤 5: 开启创作 (GUI 方式 - 推荐)
我们提供了一个基于 Web 的控制台，用于监控进度、阅读章节和触发生成。

启动服务：
```bash
python src/run_server.py
```

然后打开浏览器访问: [http://localhost:8000](http://localhost:8000)

功能包括：
- 📊 **实时看板**: 查看章节数、角色数和大纲进度。
- 📖 **在线阅读**: 浏览已生成的章节内容。
- 🚀 **一键生成**: 点击按钮触发下一章生成任务。
- 👥 **角色监控**: 查看角色当前的心情和状态。

---

## 💡 进阶技巧

### 如何写下一章？
无需任何操作，再次运行 `python -m src.main` 即可。系统会：
- 自动检测 `chapters` 表的最大章节号
- 加载前 3 章的摘要作为上下文
- 继续生成下一章

### 如何完善已写的章节？
1. **修改大纲重写**：
   - 在数据库 `plot_outlines` 表中修改对应章节的 `scene_description`
   - 删除 `chapters` 表中的该章记录
   - 重新运行 `main.py`

2. **调整文风**：
   - 修改 `novel_bible` 表的 `style_description`
   - 或在 `src/agents/writer.py` 中调整 System Prompt

### 如何避免逻辑崩坏？
系统内置了 **Antigravity Rules (反重力规则)**：
- **Rule 5.1**: Writer-Reviewer 循环不超过 3 次
- **Rule 5.2**: 第 3 次审核失败后强制通过并标记
- **Rule 4.1**: 自动过滤 DeepSeek-R1 的 `<think>` 标签

### 如何导出小说？
你可以将已生成的章节导出为 Markdown 文件，方便阅读和编辑：
```bash
python -m src.scripts.export_novel --output my_novel.md
```
支持指定分支导出（默认为 `main`）：
```bash
python -m src.scripts.export_novel --branch main --output main_story.md
```

---

## 📁 项目结构
```
NovelGen-Enterprise/
├── src/
│   ├── agents/          # 智能体 (Architect, Writer, Reviewer, Learner)
│   ├── db/              # 数据库层 (Models, SessionLocal, VectorStore)
│   ├── schemas/         # 数据协议 (Pydantic Models)
│   ├── scripts/         # 工具脚本
│   │   ├── import_novel.py    # 导入设定
│   │   └── review_setup.py    # 审查设定 (NEW!)
│   ├── graph.py         # LangGraph 状态机
│   └── main.py          # 主入口
├── sample_inputs/       # 示例设定
├── reviewed_setups/     # 审查输出目录
└── README.md
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
