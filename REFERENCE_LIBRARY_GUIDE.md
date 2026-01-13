# 资料库管理指南

本指南介绍如何为小说添加和管理资料库。

## 📚 概述

资料库（Reference Library）用于存储参考资料，帮助系统在生成小说时进行 RAG 检索。资料库可以：
- **全局资料库**：所有小说共享的通用资料（如经典设定、通用剧情套路）
- **小说专属资料库**：为特定小说添加的专属资料（如该小说的特殊设定、人物原型）

## 🚀 快速开始

### 1. 数据库迁移

首先需要运行迁移脚本，为 `reference_materials` 表添加 `novel_id` 字段：

```bash
python -m src.scripts.migrate_add_novel_id_to_references
```

### 2. 为小说添加资料库

#### 方式一：使用 CLI 工具（推荐）

创建 JSON 文件 `my_references.json`：

```json
[
  {
    "title": "修真世界基础设定",
    "content": "这是一个以修炼为主的世界，修炼者通过吸收天地灵气提升境界...",
    "source": "自定义",
    "category": "world_setting",
    "tags": ["修真", "境界", "灵气"]
  },
  {
    "title": "废材逆袭套路",
    "content": "主角原本是废材，通过奇遇或努力，最终逆袭成为强者...",
    "source": "经典套路",
    "category": "plot_trope",
    "tags": ["逆袭", "成长"]
  },
  {
    "title": "冷酷杀手原型",
    "content": "性格冷酷，擅长暗杀，对敌人毫不留情，但对信任的人会展现温柔一面...",
    "source": "人物原型库",
    "category": "character_archetype",
    "tags": ["杀手", "冷酷", "反差"]
  }
]
```

然后运行：

```bash
# 为小说 ID 1 添加资料库
python -m src.scripts.add_references_to_novel add 1 my_references.json

# 查看小说的资料库
python -m src.scripts.add_references_to_novel list 1

# 按分类查看
python -m src.scripts.add_references_to_novel list 1 --category plot_trope
```

#### 方式二：使用 API

```bash
# 添加单个资料库条目
curl -X POST "http://localhost:8000/api/novels/1/references" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "修真世界基础设定",
    "content": "这是一个以修炼为主的世界...",
    "category": "world_setting",
    "tags": ["修真", "境界"]
  }'

# 批量添加
curl -X POST "http://localhost:8000/api/novels/1/references/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "title": "设定1",
      "content": "内容1",
      "category": "world_setting"
    },
    {
      "title": "设定2",
      "content": "内容2",
      "category": "plot_trope"
    }
  ]'

# 查看小说的资料库
curl "http://localhost:8000/api/novels/1/references"

# 查看全局资料库
curl "http://localhost:8000/api/references/global"
```

## 📋 资料分类

支持以下分类：

- **world_setting**：世界观设定
- **plot_trope**：剧情套路
- **character_archetype**：人物原型
- **style**：文风参考

## 🔍 资料库检索优先级

在生成章节时，系统会按以下优先级检索资料库：

1. **小说专属资料库**（`novel_id` 匹配）
2. **全局资料库**（`novel_id` 为 `NULL`）

系统会优先使用小说专属资料库，如果不够，再补充全局资料库。

## 📝 API 端点

### 为小说添加资料库

```
POST /api/novels/{novel_id}/references
```

### 批量添加资料库

```
POST /api/novels/{novel_id}/references/batch
```

### 获取小说的资料库

```
GET /api/novels/{novel_id}/references?category={category}
```

### 获取全局资料库

```
GET /api/references/global?category={category}
```

### 获取单个资料库条目

```
GET /api/references/{reference_id}
```

### 更新资料库条目

```
PUT /api/references/{reference_id}
```

### 删除资料库条目

```
DELETE /api/references/{reference_id}
```

## 💡 使用建议

1. **全局资料库**：用于存储通用的、可复用的资料（如经典设定、通用套路）
2. **小说专属资料库**：用于存储该小说特有的设定、人物原型等
3. **分类明确**：正确设置 `category` 有助于系统更精准地检索
4. **内容质量**：资料内容应该清晰、准确，便于系统理解和使用

## 🔄 与现有系统的集成

资料库会在以下场景被自动使用：

1. **规划阶段**（`plan_node`）：检索相关剧情套路和人物原型
2. **上下文精炼阶段**（`refine_context_node`）：检索世界观设定和文风参考
3. **写作阶段**：通过 RAG 检索提供上下文参考

系统会自动优先使用小说专属资料库，确保生成内容更贴合该小说的设定。

## 📚 示例

### 示例 1：为修真小说添加专属设定

```json
[
  {
    "title": "本小说的修炼体系",
    "content": "本小说采用九大境界体系：练气、筑基、金丹、元婴、化神、炼虚、合体、大乘、渡劫。每个境界分为初期、中期、后期、巅峰四个小阶段。",
    "category": "world_setting",
    "tags": ["修炼体系", "境界"]
  }
]
```

### 示例 2：添加人物原型

```json
[
  {
    "title": "主角性格设定",
    "content": "主角性格坚毅，不轻易放弃，对朋友重情重义，对敌人冷酷无情。在关键时刻会爆发出强大的潜力。",
    "category": "character_archetype",
    "tags": ["主角", "性格"]
  }
]
```

### 示例 3：添加剧情套路

```json
[
  {
    "title": "拍卖会套路",
    "content": "主角参加拍卖会，遇到心仪的物品但资金不足，通过展示其他宝物或特殊能力获得关注，最终以特殊方式获得物品。",
    "category": "plot_trope",
    "tags": ["拍卖会", "获得宝物"]
  }
]
```

## 🛠️ 故障排查

### 问题：迁移失败

**解决方案**：
- 确保数据库连接正常
- 检查是否有其他进程占用数据库
- 查看错误日志获取详细信息

### 问题：资料库未被使用

**解决方案**：
- 检查资料库的 `category` 是否正确
- 确认资料库内容与查询相关
- 查看 RAG 检索日志

### 问题：重复添加

**解决方案**：
- 使用 `--update` 参数更新已存在的资料
- 或先删除旧资料再添加新资料

## 📖 相关文档

- [README.md](README.md) - 项目主文档
- [STORY_GENERATION_OPTIMIZATION.md](STORY_GENERATION_OPTIMIZATION.md) - 优化文档
