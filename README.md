# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Model](https://img.shields.io/badge/LLM-Gemini--2.0%20%7C%20DeepSeek--R1-orange)](https://deepseek.com/)

**NovelGen-Enterprise (NGE)** 是一款专为大规模、高逻辑性长篇小说设计的企业级多智能体生成引擎。

它采用了创新的 **"Antigravity Rules" (反重力规则)**，通过 **本地 DeepSeek (逻辑中枢)** 与 **云端 Gemini (文学工匠)** 的协同，彻底解决了 AI 创作长篇小说时常见的"逻辑坠毁"、"人物走形"和"上下文断裂"问题。

---

## ✨ 核心亮点

- **🧠 逻辑与文学分离**: 所有的剧情拆解、逻辑审计由推理能力极强的 **DeepSeek-R1** 负责；所有的文风模仿、细节描写由具备超长上下文的 **Gemini-2.0** 负责。
- **📉 动态上下文精炼 (Context Refiner)**: 系统不再一股脑填塞所有设定，而是通过 RAG 技术，仅提取当前章节最相关的 5% 设定，极大提升了生成的专注度。
- **⚖️ 自动化逻辑审计**: 每一章都会经过 `Reviewer Agent` 的毒舌扫描，检查是否有逻辑硬伤或 OOC。
- **🔄 持久化记忆链接**: 角色好感度、心境变化和最近三章的摘要被实时存入数据库，确保剧情万章不乱。
- **🔍 AI 设定审查**: 内置 `review_setup.py` 脚本，可在导入前对设定进行深度逻辑审查和自动完善。

---

## 🛠 快速开始

### 1. 环境依赖
*   **Python**: 3.10+ (推荐 3.12)
*   **Database**: PostgreSQL 16+ (可选 `pgvector` 扩展)
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

### 4. 初始化数据库
```bash
python -m src.db.init_db
```

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

### 步骤 3: 开启创作
系统会自动识别当前进度并生成下一章：
```bash
python -m src.main
```

每次运行都会：
1. 从数据库加载最新进度
2. 调用 `Architect` 规划本章剧情
3. 使用 `Writer` 生成正文
4. 通过 `Reviewer` 进行逻辑审查
5. 保存到数据库并更新人物状态

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

---

## 📁 项目结构
```
NovelGen-Enterprise/
├── src/
│   ├── agents/          # 智能体 (Architect, Writer, Reviewer, Learner)
│   ├── db/              # 数据库层 (Models, SessionLocal)
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
- [x] **RAG 向量搜索**: 实现世界观设定的语义检索
- [ ] **可视化界面**: 基于 Next.js 的创作 Dashboard
- [ ] **多线剧情分支**: 支持生成多个结局路径

---

## 🤝 贡献指南
欢迎提交 Issue 和 Pull Request！

---

## 📄 License
MIT License

---

*本项目遵循 Antigravity Rules 治理准则，确保每一行文字都具有灵魂。*
