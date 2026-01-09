import argparse
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Chapter, Novel
from src.config import settings

def export_novel(novel_id: int, output_file: str, branch_id: str = "main"):
    """
    导出指定小说和分支的章节为 Markdown 文件。
    """
    print(f"正在连接数据库: {settings.POSTGRES_URL}")
    engine = create_engine(settings.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 查询小说信息
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            print(f"错误: 未找到 ID 为 {novel_id} 的小说。")
            return

        # 查询指定小说的章节
        chapters = db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.branch_id == branch_id
        ).order_by(Chapter.chapter_number).all()

        if not chapters:
            print(f"在小说 '{novel.title}' 中未找到分支 '{branch_id}' 的任何章节。")
            return

        print(f"找到 {len(chapters)} 个章节，正在导出小说 '{novel.title}'...")

        # 如果未指定输出文件，则根据小说标题生成默认文件名
        if output_file is None:
            output_file = f"{novel.title.replace(' ', '_')}_export.md"

        with open(output_file, "w", encoding="utf-8") as f:
            # 写入小说标题
            f.write(f"# {novel.title}\n\n")
            f.write(f"**Author:** {novel.author or 'N/A'}\n")
            f.write(f"**Branch:** {branch_id}\n\n")
            
            for chapter in chapters:
                title = chapter.title or f"Chapter {chapter.chapter_number}"
                content = chapter.content or "*(No Content)*"
                
                f.write(f"## 第 {chapter.chapter_number} 章: {title}\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")

        print(f"导出成功！文件已保存至: {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"导出过程中发生错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导出小说章节为 Markdown 文件")
    parser.add_argument("--novel-id", "-n", type=int, required=True, help="要导出的小说的 ID")
    parser.add_argument("--output", "-o", help="输出文件路径 (默认: [小说标题]_export.md)")
    parser.add_argument("--branch", "-b", default="main", help="要导出的分支 ID (默认: main)")
    
    args = parser.parse_args()
    
    export_novel(novel_id=args.novel_id, output_file=args.output, branch_id=args.branch)
