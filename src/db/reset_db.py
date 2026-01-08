from src.db.base import engine, Base
from src.db.models import StyleRef, NovelBible, Character, CharacterRelationship, PlotOutline, Chapter, LogicAudit
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_reset")

def reset_db():
    logger.info("🗑️ Dropping all tables...")
    try:
        # Use a transaction to drop tables
        with engine.connect() as conn:
            # We need to drop with CASCADE because of foreign keys
            tables = ["logic_audits", "chapters", "plot_outlines", "character_relationships", "characters", "novel_bible", "style_ref"]
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            conn.commit()
        logger.info("✅ All tables dropped successfully.")
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {e}")

    logger.info("🏗️ Creating all tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    reset_db()
