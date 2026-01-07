# NovelGen-Enterprise 优化指南

## 🎯 本次优化内容总览

本次优化全面提升了系统的稳定性、可维护性和性能，主要包括以下方面：

---

## ✨ 核心优化

### 1. **Antigravity Rules 强化实施**

#### 新增功能
- **AntigravityContext**: 在 `NGEState` 中新增反重力规则执行上下文
  - `character_anchors`: 人物禁忌行为锚定（Rule 2.1）
  - `scene_constraints`: 场景化强制约束（Rule 6.1）
  - `violated_rules`: 违规记录追踪

#### 使用示例
```python
# 在导入设定时设置人物禁忌
state.antigravity_context.character_anchors["林枫"] = [
    "突然变成话痨",
    "无脑冲动",
    "违背复仇动机"
]

# 设置场景约束
state.antigravity_context.scene_constraints = {
    "scene_type": "Action",
    "max_sentence_length": 20
}
```

---

### 2. **集中式配置管理**

新增 `src/config.py`，统一管理所有配置项：

```python
from src.config import Config

# 使用配置
print(Config.antigravity.MAX_RETRY_LIMIT)  # 3
print(Config.model.GEMINI_MODEL)  # gemini-2.0-flash-exp
```

#### 环境变量支持
在 `.env` 中可配置：
```bash
# Antigravity Rules
MAX_RETRY_LIMIT=3
RECENT_CHAPTERS_CONTEXT=3

# Models
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.8
DEEPSEEK_MODEL=deepseek-r1:7b

# Writing
MIN_CHAPTER_LENGTH=2000
TARGET_CHAPTER_LENGTH=3000
```

---

### 3. **工具函数库**

新增 `src/utils.py`，提供常用工具函数：

```python
from src.utils import (
    strip_think_tags,           # Rule 4.1: 清除 <think> 标签
    extract_json_from_text,     # 容错 JSON 提取
    validate_character_consistency,  # Rule 2.1: 人物一致性验证
    analyze_sentence_length,    # 句式分析
    check_scene_constraints     # Rule 6.1: 场景约束检查
)

# 示例：验证人物行为
result = validate_character_consistency(
    character_name="林枫",
    action="林枫突然变得话痨，开始滔滔不绝...",
    forbidden_actions=["突然变成话痨"]
)
# result = {"valid": False, "violations": ["林枫 违反禁忌: 突然变成话痨"]}
```

---

### 4. **数据库优化**

#### 新增索引
- `novel_bible`: 复合索引 `(category, importance)`
- `character_relationships`: 复合索引 `(char_a_id, char_b_id)`
- `plot_outlines`: 唯一索引 `(novel_id, chapter_number)`
- `chapters`: 唯一索引 `(novel_id, chapter_number)`

#### 新增关系
- `Character` ↔ `CharacterRelationship` (双向关系)
- `Chapter` ↔ `LogicAudit` (一对多)

#### 级联删除
删除角色时自动删除相关关系，删除章节时自动删除审核记录。

#### 迁移命令
```bash
# 升级数据库
python -m src.scripts.migrate_db upgrade

# 回滚（谨慎使用）
python -m src.scripts.migrate_db downgrade
```

---

### 5. **性能监控**

新增 `src/monitoring.py`，追踪系统性能：

```python
from src.monitoring import monitor, monitor_performance

# 在 Agent 方法上使用装饰器
@monitor_performance("WriterAgent")
async def write_chapter(self, state, instruction):
    # ... 你的代码
    pass

# 查看性能报告
monitor.print_summary()
```

输出示例：
```
📊 NovelGen-Enterprise 性能报告
==================================================
总章节数: 10
成功章节数: 9
成功率: 90.0%
平均生成时间: 45.32s
平均重试次数: 0.80

📈 Agent 性能统计:
  WriterAgent:
    调用次数: 12
    总耗时: 320.45s
    平均耗时: 26.70s
    Token 消耗: 45000
    失败次数: 2
```

---

## 🔧 使用新功能

### 场景化写作

在 `plan_node` 中设置场景类型：

```python
# 在 graph.py 的 plan_node 中
state.antigravity_context.scene_constraints = {
    "scene_type": "Action",  # 或 "Emotional", "Dialogue"
}
```

Writer Agent 会自动应用对应的约束规则。

---

### 人物禁忌行为设置

在导入设定后，为关键角色设置禁忌：

```python
# 在 import_novel.py 或 main.py 中
state.antigravity_context.character_anchors = {
    "主角": ["降智", "性格突变", "违背核心动机"],
    "反派": ["突然洗白", "无脑送人头"]
}
```

---

### 调整熔断阈值

```bash
# 在 .env 中
MAX_RETRY_LIMIT=5  # 允许最多重试 5 次
```

或在代码中动态调整：
```python
state.max_retry_limit = 5
```

---

## 📊 性能优化建议

### 1. **数据库查询优化**
- 使用新增的复合索引加速查询
- 避免在循环中执行数据库操作

### 2. **上下文窗口管理**
- 默认只加载最近 3 章摘要（可通过 `RECENT_CHAPTERS_CONTEXT` 配置）
- 超过 10 章的细节会被视为"可忽略背景"（Rule 3.2）

### 3. **并发处理**（未来优化）
- 可以考虑使用 `asyncio.gather` 并行调用多个 Agent
- 注意数据库连接池配置（`DB_POOL_SIZE`）

---

## 🐛 常见问题

### Q1: 如何查看违规记录？
```python
# 在生成完成后
print(state.antigravity_context.violated_rules)
# 输出: ['Rule 5.2 Triggered: 第3章在第3次重试后强制通过']
```

### Q2: 如何禁用某个场景约束？
```python
state.antigravity_context.scene_constraints = {}
```

### Q3: 数据库迁移失败怎么办？
```bash
# 检查数据库连接
python -c "from src.db.base import engine; print(engine.url)"

# 手动创建表
python -m src.db.init_db
```

---

## 🚀 下一步优化方向

1. **RAG 向量检索**: 实现世界观设定的语义检索
2. **多线程生成**: 支持同时生成多个章节
3. **Web Dashboard**: 可视化监控和配置界面
4. **自动化测试**: 添加单元测试和集成测试
5. **LLM 缓存**: 减少重复调用的 API 费用

---

## 📝 变更日志

### v1.1.0 (2026-01-07)
- ✅ 新增 AntigravityContext 支持
- ✅ 新增集中式配置管理
- ✅ 新增工具函数库
- ✅ 优化数据库模型（索引、关系、级联）
- ✅ 新增性能监控工具
- ✅ 优化 Writer/Architect Agent 实施反重力规则
- ✅ 新增数据库迁移脚本

---

## 🤝 贡献指南

如果你有更好的优化建议，欢迎：
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

*本文档由 Antigravity AI 自动生成并优化 🚀*
