"""
Prompts Module
Prompt templates for NovelGen-Enterprise
"""

class PromptTemplates:
    """
    提示词模板片段
    用于构建 LLM 提示词的可复用组件
    """
    
    # 反重力规则警告
    ANTIGRAVITY_WARNING = """
【反重力规则警告】
- Rule 1.1: 严禁修改世界观设定，只能根据设定进行演绎
- Rule 2.1: 严禁人物性格突变或降智
- Rule 2.2: 严禁自发导致人物性格突变或降智
- Rule 3.3: 严禁逻辑硬伤
- Rule 4.1: 清除 AI 思考痕迹
- Rule 5.1: 循环熔断保护
- Rule 6.1: 场景化强制约束
"""
    
    # 人物锚定提示
    CHARACTER_ANCHOR_TEMPLATE = """
【人物灵魂锚定 - {character_name}】
- 禁止行为：{forbidden_actions}
- 当前状态：{current_mood}
- 技能：{skills}
- 资产：{assets}
"""
    
    # 场景约束提示
    SCENE_CONSTRAINT_TEMPLATE = """
【场景强制约束 - {scene_type}】
- 风格要求：{preferred_style}
- 禁忌模式：{forbidden_patterns}
"""
    
    # 伏笔管理提示
    FORESHADOWING_TEMPLATE = """
【伏笔管理要求】
1. 推进策略：明确指出本章应推进哪些已有的存量伏笔
2. 回收策略：如果剧情时机成熟，明确指出应在本章回收/揭晓的伏笔
3. 埋线策略：根据主线需要，本章是否需要埋下新的伏笔或悬念
"""
    
    # 节奏控制提示
    RHYTHM_TEMPLATE = """
【节奏控制要求】
- 节奏强度：{intensity}/10 ({intensity_desc})
- 节奏类型：{rhythm_type}
- 情绪基调：{emotional_tone}
- 避免模式：{avoid_patterns}
"""
    
    # 语言风格提示
    SPEECH_STYLE_TEMPLATE = """
【{character_name}的语言风格】
- 说话风格：{speech_pattern}
- 口头禅：{verbal_tics}
- 语气特点：{tone_modifiers}
"""
