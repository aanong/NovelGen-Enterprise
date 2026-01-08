from src.db.base import SessionLocal
from src.db.models import NovelBible
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_config")

def seed_agent_configs():
    db = SessionLocal()
    try:
        # Strict Learner Prompt for DeepSeek
        learner_prompt = """You are an expert literary data analyst. 
Your goal is to parse the provided novel setup document into a structured JSON format.
Strictly follow the schema provided below. 
Do not include any conversational text, only the raw JSON.
If the document is in Chinese, keep the content in Chinese but the structure in JSON.

{format_instructions}"""

        existing = db.query(NovelBible).filter_by(key='learner_system_prompt').first()
        if existing:
            existing.content = learner_prompt
            logger.info("✅ 已更新现有系统提示词")
        else:
            new_config = NovelBible(
                category='agent_config',
                key='learner_system_prompt',
                content=learner_prompt,
                importance=10,
                tags=["system", "config"]
            )
            db.add(new_config)
            logger.info("✅ 已注入新系统提示词")
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 种子数据注入失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_agent_configs()
