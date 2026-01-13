"""
Unified Reference Management CLI
Handles importing references from JSON files (global or novel-specific), seeding defaults, and database migrations.
"""
import argparse
import json
import os
import sys
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.base import SessionLocal
from src.services.reference_service import ReferenceService
from src.db.models import ReferenceMaterial

def import_references(
    file_path: str, 
    novel_id: Optional[int] = None, 
    skip_existing: bool = True
):
    """
    Import references from a JSON file.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        return

    if not isinstance(data, list):
        print("❌ Invalid JSON format: Root must be a list")
        return

    print(f"📂 Processing {file_path} ({len(data)} items)")
    if novel_id:
        print(f"📘 Target Novel ID: {novel_id}")
    else:
        print(f"🌍 Importing as Global References")

    db: Session = SessionLocal()
    success = 0
    skipped = 0
    failed = 0

    try:
        for item in data:
            try:
                # Prepare data
                ref_data = item.copy()
                
                title = ref_data.get("title")
                if not title:
                    failed += 1
                    continue

                # Check existence manually to implement skip_existing
                query = db.query(ReferenceMaterial).filter(ReferenceMaterial.title == title)
                if novel_id:
                    query = query.filter(ReferenceMaterial.novel_id == novel_id)
                else:
                    query = query.filter(ReferenceMaterial.novel_id.is_(None))
                
                existing = query.first()

                if existing:
                    if skip_existing:
                        print(f"  ⚠️ Skipped (Exists): {title}")
                        skipped += 1
                        continue
                    else:
                        print(f"  ⚠️ Updating: {title}")
                        for k, v in ref_data.items():
                            if hasattr(existing, k):
                                setattr(existing, k, v)
                        # Re-embed if content changed
                        if 'content' in ref_data:
                             from src.utils import get_embedding
                             existing.embedding = get_embedding(ref_data['content'])
                        success += 1
                else:
                    # Add new
                    print(f"  ✨ Adding: {title}")
                    ReferenceService.add_reference(db, novel_id if novel_id else None, ref_data)
                    success += 1
            
            except Exception as e:
                print(f"  ❌ Error processing {item.get('title', 'Unknown')}: {e}")
                failed += 1

        db.commit()
        print(f"\n✅ Import Complete: {success} added/updated, {skipped} skipped, {failed} failed.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        db.close()

def run_migration():
    """Execute database migration to add novel_id to references."""
    db = SessionLocal()
    try:
        print("🔄 Starting migration: Adding novel_id to reference_materials table...")
        
        # Check if column exists
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'reference_materials' 
        AND column_name = 'novel_id'
        """
        result = db.execute(text(check_sql))
        if result.fetchone():
            print("✅ novel_id column already exists, skipping.")
            return
        
        # Add novel_id column
        print("  Adding novel_id column...")
        db.execute(text("""
            ALTER TABLE reference_materials 
            ADD COLUMN novel_id INTEGER REFERENCES novels(id) ON DELETE CASCADE
        """))
        
        # Add index
        print("  Adding index...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reference_materials_novel_id 
            ON reference_materials(novel_id)
        """))
        
        # Add composite index
        print("  Adding composite index...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_novel_category 
            ON reference_materials(novel_id, category)
        """))
        
        db.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Manage Reference Materials")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Import Command
    import_parser = subparsers.add_parser("import", help="Import references from JSON")
    import_parser.add_argument("file_path", help="Path to JSON file")
    import_parser.add_argument("--novel-id", type=int, help="Target Novel ID (optional, defaults to Global)")
    import_parser.add_argument("--force", action="store_true", help="Overwrite existing references")

    # Migrate Command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migration for references")

    # Seed Command
    seed_parser = subparsers.add_parser("seed", help="Seed default references")
    
    args = parser.parse_args()

    if args.command == "import":
        import_references(args.file_path, args.novel_id, skip_existing=not args.force)
    elif args.command == "migrate":
        run_migration()
    elif args.command == "seed":
        print("To be implemented: pointing to a default seed file.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
