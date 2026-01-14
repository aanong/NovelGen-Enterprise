---
name: noval
description: NovelGen-Enterprise (NGE) 项目开发规范与技术指南
---

# NovelGen-Enterprise 开发规范

## 一、项目概述

NovelGen-Enterprise (NGE) 是一款企业级、高可用的长篇小说生成系统。系统采用 **LangGraph** 构建多智能体协作工作流，通过 **DeepSeek (逻辑中枢)** 与 **Gemini (文学工匠)** 双模型架构协同工作，解决长篇生成中的逻辑连贯性、人物一致性和风格统一性问题。

### 核心技术栈

- **语言**: Python 3.10+
- **AI 框架**: LangChain, LangGraph
- **LLM 模型**: Gemini (写作), DeepSeek (逻辑/规划)
- **Web 框架**: FastAPI
- **任务队列**: Celery + Redis
- **数据库**: PostgreSQL + pgvector (向量存储)
- **ORM**: SQLAlchemy + Alembic (迁移)
- **配置管理**: python-dotenv

---

## 二、项目架构

### 目录结构

```
src/
├── agents/           # Agent 实现（AI 智能体）
│   ├── base.py       # Agent 基类
│   ├── architect.py  # 架构师 Agent（大纲拆解、剧情规划）
│   ├── writer.py     # 写作 Agent（正文撰写、文风模仿）
│   ├── reviewer.py   # 审查 Agent（逻辑审查、OOC 检查）
│   ├── evolver.py    # 演化 Agent（人物状态演化）
│   ├── summarizer.py # 摘要 Agent（章节摘要生成）
│   ├── style_analyzer.py # 文风分析 Agent
│   └── constants.py  # Agent 常量定义
├── api/              # FastAPI 路由
│   ├── app.py        # FastAPI 应用入口
│   ├── deps.py       # 依赖注入
│   ├── schemas.py    # Pydantic 请求/响应模型
│   └── routes/       # 路由模块
├── db/               # 数据库层
│   ├── base.py       # SQLAlchemy Base
│   ├── models.py     # ORM 模型定义
│   ├── vector_store.py # 向量存储操作
│   └── *_repository.py # 仓储模式实现
├── nodes/            # LangGraph 节点实现
│   ├── loader.py     # 上下文加载节点
│   ├── planner.py    # 规划节点
│   ├── refiner.py    # 上下文精炼节点（RAG）
│   ├── writer.py     # 写作节点
│   ├── reviewer.py   # 审查节点
│   └── evolver.py    # 演化节点
├── schemas/          # 数据模型
│   ├── state.py      # NGEState 状态定义
│   └── style.py      # 文风特征定义
├── services/         # 业务逻辑层
├── scripts/          # 脚本工具
├── config.py         # 配置管理
├── graph.py          # LangGraph 工作流定义
├── worker.py         # Celery Worker
├── tasks.py          # Celery 任务定义
└── utils.py          # 工具函数库
```

### 工作流架构

```
load_context → plan → refine_context → write → review → evolve
     ↓           ↓          ↓            ↓        ↓        ↓
  加载状态   规划章节   RAG检索     撰写正文  逻辑审查  人物演化
                                                ↓
                                    ┌─────────────────────┐
                                    │ CONTINUE → evolve   │
                                    │ REVISE → write      │
                                    │ REPAIR → repair     │
                                    └─────────────────────┘
```

---

## 三、Antigravity Rules 规则系统

Antigravity Rules 是 NGE 的核心质量保障机制，用于防止人物 OOC、逻辑硬伤和世界观崩坏。

### Rule 1: 世界观一致性

- 所有生成内容必须符合 `NovelBible` 中定义的世界观设定
- 核心设定（功法、等级、地理等）不可违背

### Rule 2: 人物灵魂锚定

- **Rule 2.1**: 每个角色都有禁忌行为列表，绝对禁止生成
- **Rule 2.2**: 角色行为必须符合其性格锚定（personality_traits）
- 禁忌行为存储在 `antigravity_context.character_anchors`

```python
# 默认禁忌行为
DEFAULT_CHARACTER_FORBIDDEN = [
    "突然性格大变",
    "违背核心动机",
    "降智行为"
]
```

### Rule 3: 上下文滑窗准则

- **Rule 3.1**: 默认加载最近 3 章摘要作为上下文
- **Rule 3.2**: 最多加载 10 章上下文
- **Rule 3.3**: 剧情防崩与连贯检查

### Rule 4: 输出清洗

- **Rule 4.1**: 清除 `<think>` 标签（DeepSeek-R1 特有）

```python
def strip_think_tags(content: str) -> str:
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
```

### Rule 5: 循环熔断机制

- **Rule 5.1**: 最大重试次数限制（默认 3 次）
- **Rule 5.2**: 超过限制自动降级处理

### Rule 6: 场景化强制约束

- **Rule 6.1**: 不同场景类型有不同的写作约束
- **Rule 6.2**: 验证前缀机制

```python
SCENE_CONSTRAINTS = {
    "Action": {
        "max_sentence_length": 20,
        "preferred_style": "短促动词为主",
        "forbidden_patterns": ["超过20字的长句"]
    },
    "Emotional": {
        "forbidden_patterns": ["连续动词堆叠"],
        "preferred_style": "心理描写为主"
    },
    "Dialogue": {
        "min_dialogue_ratio": 0.6,
        "preferred_style": "符合人物语气"
    }
}
```

---

## 四、核心模块开发规范

### 1. Agent 开发规范

所有 Agent 必须继承 `BaseAgent` 并实现 `process` 方法：

```python
from src.agents.base import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",  # 或 "deepseek"
            temperature=temperature or Config.model.GEMINI_TEMPERATURE,
            mock_responses=[...]  # 测试用响应
        )
    
    async def process(self, state: NGEState, *args, **kwargs) -> Any:
        """必须实现的处理方法"""
        # 1. 构建提示词
        # 2. 调用 LLM
        # 3. 处理响应（包括 strip_think_tags）
        # 4. 返回结果
        pass
```

**模型选择原则**:
- `gemini`: 用于写作、摘要生成等需要创意的任务
- `deepseek`: 用于逻辑推理、规划、审查等需要严谨思维的任务

### 2. Node 开发规范

LangGraph 节点应该是独立的、可测试的单元：

```python
class CustomNode:
    def __init__(self, agent: BaseAgent):
        self.agent = agent
    
    async def __call__(self, state: NGEState) -> NGEState:
        """节点必须接收 NGEState 并返回更新后的 NGEState"""
        # 1. 从 state 提取所需数据
        # 2. 调用 agent 处理
        # 3. 更新 state 并返回
        result = await self.agent.process(state, ...)
        return state.model_copy(update={"field": result})
```

### 3. Repository 开发规范

采用仓储模式封装数据库操作：

```python
class CustomRepository:
    def __init__(self, session: Session):
        self.session = session
    
    async def get_by_id(self, id: int) -> Optional[Model]:
        """查询方法"""
        pass
    
    async def create(self, data: CreateSchema) -> Model:
        """创建方法"""
        pass
    
    async def update(self, id: int, data: UpdateSchema) -> Model:
        """更新方法"""
        pass
```

### 4. Service 开发规范

Service 层封装业务逻辑，不直接依赖数据库 Session：

```python
class CustomService:
    @staticmethod
    async def perform_action(param: str) -> Dict[str, Any]:
        """业务逻辑方法"""
        pass
```

---

## 五、状态管理规范

### NGEState 核心字段

```python
class NGEState(BaseModel):
    # 核心数据
    novel_bible: NovelBible          # 世界观设定
    characters: Dict[str, CharacterState]  # 人物状态
    world_items: List[WorldItemSchema]     # 关键物品
    plot_progress: List[PlotPoint]         # 剧情进度
    
    # 运行时状态
    current_plot_index: int          # 当前剧情点索引
    current_branch: str              # 当前分支 ID
    current_novel_id: int            # 当前小说 ID
    
    # 记忆上下文
    memory_context: MemoryContext    # 摘要和伏笔
    refined_context: List[str]       # RAG 检索结果
    
    # Antigravity 规则上下文
    antigravity_context: AntigravityContext
    
    # 运行控制
    next_action: str                 # 下一步动作
    current_draft: str               # 当前草稿
    review_feedback: str             # 审查反馈
    retry_count: int                 # 重试次数
```

### 状态更新原则

1. **不可变更新**: 使用 `state.model_copy(update={...})` 而非直接修改
2. **最小更新**: 只更新必要的字段
3. **版本追踪**: 重要变更需更新 `state_version`

---

## 六、数据库模型规范

### 核心表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `novels` | 小说元数据 | id, title, status |
| `chapters` | 章节内容 | novel_id, branch_id, chapter_number, content |
| `characters` | 人物信息 | novel_id, name, personality_traits, skills |
| `plot_outlines` | 剧情大纲 | novel_id, branch_id, chapter_number |
| `novel_bible` | 世界观设定 | novel_id, category, key, content, embedding |
| `reference_materials` | 资料库 | novel_id, title, content, category, embedding |
| `world_items` | 关键物品 | novel_id, name, rarity, powers, owner_id |
| `character_relationships` | 人物关系 | char_a_id, char_b_id, relation_type, intimacy |

### 索引设计原则

1. 所有外键字段必须建立索引
2. 复合查询使用复合索引
3. 向量字段使用 pgvector 索引

```python
__table_args__ = (
    Index('idx_novel_category', 'novel_id', 'category'),
    Index('idx_novel_key', 'novel_id', 'key', unique=True),
)
```

---

## 七、API 开发规范

### 路由命名规范

- 资源使用复数形式: `/api/novels/`, `/api/chapters/`
- 嵌套资源: `/api/novels/{novel_id}/chapters/`
- 动作使用动词: `/api/generate/trigger`

### 响应格式

```python
# 成功响应
{
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "detail": "错误信息"
}
```

### SSE 流式响应

生成任务支持 SSE 流式输出：

```python
@router.get("/stream/{task_id}")
async def stream_generation(task_id: str):
    return EventSourceResponse(
        GenerationService.stream_generation_events(task_id)
    )
```

---

## 八、配置管理规范

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `GOOGLE_API_KEY` | Gemini API 密钥 | 是 |
| `POSTGRES_URL` | PostgreSQL 连接字符串 | 是 |
| `REDIS_URL` | Redis 连接字符串 | 否 |
| `DEEPSEEK_API_BASE` | DeepSeek API 地址 | 否 |
| `GEMINI_MODEL` | Gemini 模型名称 | 否 |

### 配置访问

通过 `Config` 类统一访问配置：

```python
from src.config import Config

# 访问模型配置
model_name = Config.model.GEMINI_MODEL

# 访问写作配置
min_length = Config.writing.MIN_CHAPTER_LENGTH

# 访问 Antigravity 配置
max_retry = Config.antigravity.MAX_RETRY_LIMIT
```

---

## 九、代码风格规范

### Python 代码规范

1. **格式化**: 使用 `black` 进行代码格式化
2. **导入排序**: 使用 `isort` 进行导入排序
3. **类型注解**: 所有函数必须有类型注解
4. **文档字符串**: 所有公共函数/类必须有中文文档字符串

```python
async def process_chapter(
    state: NGEState,
    chapter_id: int,
    options: Optional[Dict[str, Any]] = None
) -> ChapterResult:
    """
    处理章节生成
    
    Args:
        state: 当前全局状态
        chapter_id: 章节 ID
        options: 可选的处理选项
        
    Returns:
        ChapterResult: 章节生成结果
        
    Raises:
        ValueError: 当 chapter_id 无效时
    """
    pass
```

### 命名规范

- **类名**: PascalCase (如 `WriterAgent`)
- **函数名**: snake_case (如 `process_chapter`)
- **常量**: UPPER_SNAKE_CASE (如 `MAX_RETRY_LIMIT`)
- **私有成员**: 前缀下划线 (如 `_build_prompt`)

### 异步编程规范

1. 所有 I/O 操作必须使用异步
2. 使用 `asyncio.gather` 并行执行独立任务
3. 避免在异步函数中使用阻塞调用

```python
# 正确: 并行执行
results = await asyncio.gather(
    self.fetch_bible(query),
    self.fetch_style(query),
    self.fetch_references(query)
)

# 错误: 顺序执行
bible = await self.fetch_bible(query)
style = await self.fetch_style(query)
refs = await self.fetch_references(query)
```

---

## 十、测试规范

### Mock 模型使用

开发和测试时可使用 Mock 模型：

```python
# 设置环境变量
GEMINI_MODEL=mock

# 或在代码中
agent = WriterAgent(use_mock=True, mock_responses=[...])
```

### 测试文件命名

- 单元测试: `test_<module>.py`
- 集成测试: `test_integration_<feature>.py`

---

## 十一、常用工具函数

### LLM 响应处理

```python
from src.utils import (
    strip_think_tags,        # 清除 <think> 标签
    extract_json_from_text,  # 从文本提取 JSON
    normalize_llm_content,   # 标准化 LLM 输出
)
```

### 文本分析

```python
from src.utils import (
    analyze_sentence_length,     # 句式长度分析
    check_scene_constraints,     # 场景约束检查
    validate_character_consistency,  # 人物一致性验证
)
```

### Embedding 生成

```python
from src.utils import get_embedding

# 生成文本向量
embedding = get_embedding("这是一段文本")
```

---

## 十二、Git 提交规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具

**示例**:
```
feat(agents): 添加 SummarizerAgent 实现结构化摘要

- 使用 LLM 生成包含核心事件、人物变化的结构化摘要
- 替代简单的文本截取方式
- 符合 Antigravity Rule 3.3 剧情连贯性要求
```

---

## 十三、性能优化指南

### RAG 检索优化

1. 使用复合查询减少检索次数
2. 限制 top_k 数量（默认 5）
3. 使用缓存减少重复检索

### LLM 调用优化

1. 合理设置 temperature 参数
2. 限制输入 token 数量
3. 使用流式输出提升用户体验

### 数据库优化

1. 使用连接池（默认 pool_size=5）
2. 添加适当的索引
3. 使用 batch 操作减少往返

---

## 十四、故障排查

### 常见问题

1. **LLM 调用超时**: 检查 API 配额，增加 timeout
2. **向量检索无结果**: 检查 embedding 是否生成，索引是否存在
3. **人物 OOC**: 检查 character_anchors 配置
4. **章节不连贯**: 增加 RECENT_CHAPTERS_CONTEXT 配置

### 日志查看

```python
import logging
logging.getLogger("src.agents").setLevel(logging.DEBUG)
```

---

*文档版本: 1.0.0*
*最后更新: 2026-01-14*
