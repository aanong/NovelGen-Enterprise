"""
Defaults Module
Default configuration values for NovelGen-Enterprise
"""

class Defaults:
    """
    默认配置值
    集中管理系统级别的默认参数
    """
    
    # ========== 章节相关 ==========
    MIN_CHAPTER_LENGTH = 2000       # 最小章节长度
    TARGET_CHAPTER_LENGTH = 3000    # 目标章节长度
    MAX_CHAPTER_LENGTH = 5000       # 最大章节长度
    
    # ========== 重试相关 ==========
    MAX_RETRY_LIMIT = 3             # 最大重试次数
    RETRY_DELAY_SECONDS = 1         # 重试延迟秒数
    
    # ========== 上下文相关 ==========
    RECENT_CHAPTERS_CONTEXT = 3     # 近期章节上下文数量
    MAX_CONTEXT_CHAPTERS = 10       # 最大上下文章节数
    MAX_CONTEXT_SUMMARIES = 3       # 提示词中使用的最大摘要数量（优化 token 使用）
    MAX_CHARACTERS_IN_PROMPT = 5   # 提示词中包含的最大角色数量（优化 token 使用）
    
    # ========== RAG 相关 ==========
    BIBLE_SEARCH_TOP_K = 3          # 世界观检索数量
    STYLE_SEARCH_TOP_K = 1          # 文风检索数量
    REFERENCE_SEARCH_TOP_K = 2      # 参考资料检索数量
    
    # ========== 逻辑审查 ==========
    MIN_LOGIC_SCORE = 0.7           # 最低逻辑评分
    MAX_LOGIC_SCORE = 1.0           # 最高逻辑评分
    
    # ========== 节奏控制 ==========
    RHYTHM_LOOKBACK_CHAPTERS = 5    # 节奏分析回看章节数
    HIGH_INTENSITY_THRESHOLD = 7    # 高强度阈值
    LOW_INTENSITY_THRESHOLD = 3     # 低强度阈值
    CONSECUTIVE_HIGH_LIMIT = 3      # 连续高强度章节限制
    CONSECUTIVE_LOW_LIMIT = 4       # 连续低强度章节限制
    
    # ========== 伏笔管理 ==========
    FORESHADOWING_LOOKAHEAD = 3     # 伏笔到期提前提醒章节数
    FORESHADOWING_OVERDUE_WARNING = True  # 是否开启过期警告
    
    # ========== 缓存相关 ==========
    CACHE_TTL_LLM_RESPONSE = 3600      # LLM 响应缓存 TTL（秒），默认 1 小时
    CACHE_TTL_EMBEDDING = 86400        # Embedding 缓存 TTL（秒），默认 24 小时
    CACHE_TTL_VECTOR_SEARCH = 300      # 向量检索缓存 TTL（秒），默认 5 分钟
    CACHE_TTL_PLAN_RESULT = 86400      # 规划结果缓存 TTL（秒），默认 24 小时
    
    # ========== 向量检索 ==========
    MAX_FALLBACK_ITEMS = 100           # Fallback 模式最大查询数量
    NOVEL_SPECIFIC_PRIORITY_BOOST = 1.2  # 小说特定项目的优先级提升倍数
    
    # ========== 重试相关 ==========
    MAX_STYLE_RETRIES = 2              # 风格问题最大重试次数
