# NovelGen-Enterprise (NGE) 🚀

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Model](https://img.shields.io/badge/LLM-Gemini--2.0%20%7C%20DeepSeek--R1-orange)](https://deepseek.com/)

**NovelGen-Enterprise (NGE)** 是一款专为大规模、高逻辑性长篇小说设计的企业级多智能体生成引擎。

它采用了创新的 **"Antigravity Rules" (反重力规则)**，通过 **本地 DeepSeek (逻辑中枢)** 与 **云端 Gemini (文学工匠)** 的协同，彻底解决了 AI 创作长篇小说时常见的“逻辑坠毁”、“人物走形”和“上下文断裂”问题。

---

## ✨ 核心亮点

- **🧠 逻辑与文学分离**: 所有的剧情拆解、逻辑审计由推理能力极强的 **DeepSeek-R1** 负责；所有的文风模仿、细节描写由具备超长上下文的 **Gemini-2.0** 负责。
- **📉 动态上下文精炼 (Context Refiner)**: 系统不再一股脑填塞所有设定，而是通过 RAG 技术，仅提取当前章节最相关的 5% 设定，极大提升了生成的专注度。
- **⚖️ 自动化逻辑审计**: 每一章都会经过 `Reviewer Agent` 的毒舌扫描，检查是否有逻辑硬伤或 OOC。
- **🔄 持久化记忆链接**: 角色好感度、心境变化和最近三章的摘要被实时存入数据库，确保剧情万章不乱。

---

## 🛠 快速开始

### 1. 环境依赖
*   **Python**: 3.10+ (推荐 3.12)
*   **Database**: PostgreSQL 16+ (推荐开启 `pgvector` 扩展)
*   **Local LLM**: [Ollama](https://ollama.com/) (需运行 `ollama run deepseek-r1:7b`)

### 2. 配置秘钥
复制并编辑 `.env` 文件：
```bash
cp .env.example .env
```
确保包含以下配置项：
*   `GOOGLE_API_KEY`: 申请 [Google AI Studio](https://aistudio.google.com/)。
*   `POSTGRES_URL`: 你的数据库连接字符串。

### 3. 数据导入
将你的小说设定写在文本文件中：
```bash
python -m src.scripts.import_novel ./sample_inputs/novel_setup.txt
```

### 4. 开启无限创作
系统会自动识别当前进度并生成下一章：
```bash
python -m src.main
```

---

## 📖 进阶技巧：如何写得更好？

### 💡 怎么写下一章？
你无需任何额外操作。系统每次运行 `main.py` 都会检查 `chapters` 表。如果第 1 章已完成，它会自动读取大纲并加载最近的 `MemoryContext` 来撰写第 2 章。

### ✍️ 怎么完善（修改）已写的章节？
1.  **手动引导**：修改 `plot_outlines` 表中对应章节的 `key_conflict`。
2.  **强制重写**：删除对应章节的数据库记录，系统会视其为“待生成”章节重新调用 Writer 生成。
3.  **微调文风**：在 `novel_bible` 表的 `style_description` 中增加具体的关键词（如：多用古文，少用白话）。

---

## 🏗 开源路线图 (Roadmap)
- [ ] **RAG 向量搜索完全集成**: 实现世界观设定的语义检索。 (In Progress)
- [ ] **可视化交互界面**: 基于 Next.js 的小说创作 Dashboard。
- [ ] **多线剧情分支**: 支持 Architect 生成多个结局路径。

---
*本项目遵循 Antigravity Rules 治理准则，确保每一行文字都具有灵魂。*
