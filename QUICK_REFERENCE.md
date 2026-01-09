# 🚀 NovelGen-Enterprise 优化快速参考

## 📋 优化内容一览

### ✅ 已完成的 10 项优化

| # | 优化项 | 文件 | 优先级 |
|---|--------|------|--------|
| 1 | 状态管理增强 | `src/schemas/state.py` | ⭐⭐⭐ |
| 2 | Writer Agent 规则实施 | `src/agents/writer.py` | ⭐⭐⭐ |
| 3 | Graph 循环熔断优化 | `src/graph.py` | ⭐⭐⭐ |
| 4 | 数据库模型优化 | `src/db/models.py` | ⭐⭐⭐ |
| 5 | 集中式配置管理 | `src/config.py` (新) | ⭐⭐ |
| 6 | 工具函数库 | `src/utils.py` (新) | ⭐⭐ |
| 7 | Architect Agent 重构 | `src/agents/architect.py` | ⭐⭐ |
| 8 | 数据库迁移脚本 | `src/scripts/migrate_db.py` (新) | ⭐⭐ |
| 9 | 性能监控工具 | `src/monitoring.py` (新) | ⭐⭐ |
| 10 | 文档完善 | `OPTIMIZATION_GUIDE.md` (新) | ⭐ |

---

## 🎯 Antigravity Rules 实施状态

| 规则 | 描述 | 实施状态 | 相关代码 |
|------|------|----------|----------|
| Rule 1.1 | Gemini 为王（设定解释权） | ✅ 完成 | `architect.py` Prompt |
| Rule 2.1 | 人物灵魂锚定 | ✅ 完成 | `state.py`, `writer.py` |
| Rule 2.2 | 动态弧度限制 | ✅ 完成 | `architect.py` Prompt |
| Rule 3.1 | 无记忆不写作 | ✅ 已有 | `writer.py` 上下文注入 |
| Rule 3.2 | 遗忘防御 | ✅ 已有 | `config.py` MAX_CONTEXT |
| Rule 4.1 | 思考标签隔离 | ✅ 完成 | `utils.py` strip_think_tags |
| Rule 5.1 | 三轮必断 | ✅ 完成 | `graph.py` max_retry_limit |
| Rule 5.2 | 降级方案 | ✅ 完成 | `graph.py` 熔断记录 |
| Rule 6.1 | 场景化约束 | ✅ 完成 | `writer.py` 场景规则 |

---

## 🛠️ 快速使用指南

### 1. 设置人物禁忌（Rule 2.1）
```python
state.antigravity_context.character_anchors["主角"] = [
    "突然降智",
    "性格突变",
    "违背核心动机"
]
```

### 2. 设置场景约束（Rule 6.1）
```python
state.antigravity_context.scene_constraints = {
    "scene_type": "Action",  # 或 "Emotional", "Dialogue"
}
```

### 3. 调整熔断阈值（Rule 5.1）
```bash
# .env 文件
MAX_RETRY_LIMIT=5
```

### 4. 使用工具函数
```python
from src.utils import strip_think_tags, validate_character_consistency

# 清理 <think> 标签
clean_text = strip_think_tags(raw_output)

# 验证人物一致性
result = validate_character_consistency(
    character_name="主角",
    action="主角的行为描述",
    forbidden_actions=["禁忌1", "禁忌2"]
)
```

### 5. 查看性能报告
```python
from src.monitoring import monitor
monitor.print_summary()
```

---

## 📊 配置参数速查

### Antigravity Rules 参数
```bash
MAX_RETRY_LIMIT=3              # 最大重试次数
RECENT_CHAPTERS_CONTEXT=3      # 上下文章节数
MAX_CONTEXT_CHAPTERS=10        # 最大上下文范围
```

### 模型参数
```bash
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.8
DEEPSEEK_MODEL=deepseek-r1:7b
DEEPSEEK_ARCHITECT_TEMP=0.3
DEEPSEEK_REVIEWER_TEMP=0.1
```

### 写作参数
```bash
MIN_CHAPTER_LENGTH=2000        # 最小章节字数
TARGET_CHAPTER_LENGTH=3000     # 目标章节字数
ENABLE_LOGIC_AUDIT=true        # 启用逻辑审查
MIN_LOGIC_SCORE=0.7            # 最低逻辑分数
```

---

## 🔧 常用命令

### 数据库操作
```bash
# 初始化数据库
python -m src.db.init_db

# 升级数据库（应用优化）
python -m src.scripts.migrate_db upgrade

# 回滚数据库
python -m src.scripts.migrate_db downgrade
```

### 设定管理
```bash
# 审查设定
python -m src.scripts.review_setup ./sample_inputs/novel_setup.txt

# 导入设定
python -m src.scripts.import_novel ./reviewed_setups/enhanced_setup.txt
```

### 生成章节
```bash
# 生成下一章 (需指定 Novel ID)
python -m src.main run --novel-id 1
```

### 验证优化
```bash
# 运行验证脚本
python verify_optimization.py
```

### 性能监控
```bash
# 查看性能报告
python -m src.monitoring
```

---

## 🚨 部署检查清单

部署前请确认：

- [ ] ✅ 所有测试通过（运行 `verify_optimization.py`）
- [ ] ✅ 数据库已迁移（`migrate_db upgrade`）
- [ ] ✅ `.env` 配置已更新
- [ ] ✅ 已阅读 `OPTIMIZATION_GUIDE.md`
- [ ] ✅ 已测试生成一章
- [ ] ✅ 已查看性能报告

---

## 📚 文档索引

- **优化总结**: `OPTIMIZATION_REPORT.md`
- **使用指南**: `OPTIMIZATION_GUIDE.md`
- **项目说明**: `README.md`
- **本参考卡**: `QUICK_REFERENCE.md`

---

## 💡 最佳实践

### 1. 人物设定
- 为主要角色设置 3-5 个禁忌行为
- 在导入设定后立即配置 `character_anchors`

### 2. 场景控制
- 战斗场景使用 `scene_type: "Action"`
- 情感戏使用 `scene_type: "Emotional"`
- 对话戏使用 `scene_type: "Dialogue"`

### 3. 性能优化
- 定期查看性能报告
- 关注 Token 消耗最高的 Agent
- 调整 `temperature` 参数平衡质量和速度

### 4. 错误处理
- 检查 `violated_rules` 了解熔断原因
- 查看 `logic_audits` 表了解审核历史
- 使用性能监控定位慢速环节

---

## 🔗 快速链接

- [Gemini API](https://aistudio.google.com/)
- [Ollama 文档](https://ollama.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

---

**版本**: v1.1.0  
**更新时间**: 2026-01-07  
**维护者**: Antigravity AI

*快速参考，随时查阅 📖*
