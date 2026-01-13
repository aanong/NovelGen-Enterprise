from sqlalchemy import text
from src.db.base import engine

def fix_schema():
    print("Fixing database schema...")
    with engine.connect() as conn:
        # Use autocommit for schema changes
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            print("Adding novel_id to reference_materials...")
            conn.execute(text("ALTER TABLE reference_materials ADD COLUMN IF NOT EXISTS novel_id INTEGER REFERENCES novels(id) ON DELETE CASCADE;"))
            print("Successfully added novel_id.")
        except Exception as e:
            print(f"Error adding novel_id: {e}")
        
        try:
             print("Adding tags to reference_materials...")
             conn.execute(text("ALTER TABLE reference_materials ADD COLUMN IF NOT EXISTS tags JSON;"))
             print("Successfully added tags.")
        except Exception as e:
            print(f"Error adding tags: {e}")

if __name__ == "__main__":
    fix_schema()
