from src.db.base import SessionLocal
from src.db.models import Chapter, Character, Novel, CharacterBranchStatus
from sqlalchemy import func

def verify_db():
    db = SessionLocal()
    try:
        print("=== NovelGen-Enterprise Database Verification ===\n")

        # 1. List Novels
        novels = db.query(Novel).all()
        print(f"📚 Found {len(novels)} Novels:")
        for novel in novels:
            print(f"  - [ID: {novel.id}] {novel.title} (Author: {novel.author})")
            
            # 2. List Branches for this novel
            branches = db.query(Chapter.branch_id).filter_by(novel_id=novel.id).distinct().all()
            branch_names = [b[0] for b in branches]
            print(f"    🌿 Branches: {branch_names}")
            
            for branch in branch_names:
                # 3. List Chapters in this branch
                chapter_count = db.query(Chapter).filter_by(novel_id=novel.id, branch_id=branch).count()
                latest_chapter = db.query(Chapter).filter_by(novel_id=novel.id, branch_id=branch).order_by(Chapter.chapter_number.desc()).first()
                
                print(f"      > Branch '{branch}': {chapter_count} chapters")
                if latest_chapter:
                    print(f"        Latest: Ch.{latest_chapter.chapter_number} - {latest_chapter.title}")
                    print(f"        Summary: {latest_chapter.summary[:50]}..." if latest_chapter.summary else "        Summary: None")

        print("\n=== Character Status Check ===")
        characters = db.query(Character).all()
        for char in characters:
            print(f"👤 {char.name} (Novel ID: {char.novel_id})")
            print(f"   Current Mood: {char.current_mood}")
            
            # Check snapshots
            snapshots = db.query(CharacterBranchStatus).filter_by(character_id=char.id).order_by(CharacterBranchStatus.chapter_number.desc()).all()
            if snapshots:
                print(f"   📸 Snapshots ({len(snapshots)}):")
                for snap in snapshots[:3]: # Show last 3
                    print(f"     - [Branch: {snap.branch_id}] Ch.{snap.chapter_number}: Mood={snap.current_mood}")
            else:
                print("   📸 No snapshots found.")
            print("")

    finally:
        db.close()

if __name__ == "__main__":
    verify_db()
