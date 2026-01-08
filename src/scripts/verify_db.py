from src.db.base import SessionLocal
from src.db.models import Chapter, Character

db = SessionLocal()
try:
    ch1 = db.query(Chapter).filter_by(chapter_number=1).first()
    print(f"Chapter 1 Saved: {ch1 is not None}")
    if ch1:
        print(f"Title: {ch1.title}")
        print(f"Content length: {len(ch1.content)}")
        print(f"Summary: {ch1.summary}")

    xu_nian = db.query(Character).filter_by(name='许念').first()
    if xu_nian:
        print(f"\nCharacter: {xu_nian.name}")
        print(f"Current Mood: {xu_nian.current_mood}")
        print("Evolution Log:")
        for log in xu_nian.evolution_log:
            print(f"  - {log}")
        print(f"Skills: {xu_nian.skills}")
        print(f"Assets: {xu_nian.assets}")
finally:
    db.close()
