from .base import engine, Base
from .models import StyleRef, NovelBible, Character, CharacterRelationship, PlotOutline, Chapter, LogicAudit

def init_db():
    print("⏳ 正在初始化数据库表结构...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表结构初始化成功！")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")

if __name__ == "__main__":
    init_db()
