import argparse
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Chapter
from src.config import settings

def export_novel(output_file: str, branch_id: str = "main"):
    """
    导出指定分支的小说章节为 Markdown 文件。
    """
    print(f"正在连接数据库: {settings.POSTGRES_URL}")
    engine = create_engine(settings.POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 查询指定分支的所有章节，按章节号排序
        chapters = db.query(Chapter).filter(
            Chapter.branch_id == branch_id
        ).order_by(Chapter.chapter_number).all()

        if not chapters:
            print(f"未找到分支 '{branch_id}' 的任何章节。")
            return

        print(f"找到 {len(chapters)} 个章节，正在导出...")

        with open(output_file, "w", encoding="utf-8") as f:
            # 写入标题
            f.write(f"# Novel Export (Branch: {branch_id})\n\n")
            
            for chapter in chapters:
                title = chapter.title or f"Chapter {chapter.chapter_number}"
                content = chapter.content or "*(No Content)*"
                
                # 写入章节标题
                f.write(f"## 第 {chapter.chapter_number} 章 {title}\n\n")
                
                # 写入章节内容
                f.write(f"{content}\n\n")
                
                # 写入分隔符
                f.write("---\n\n")

        print(f"导出成功！文件已保存至: {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"导出过程中发生错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导出小说章节为 Markdown 文件")
    parser.add_argument("--output", "-o", default="novel_export.md", help="输出文件路径 (默认: novel_export.md)")
    parser.add_argument("--branch", "-b", default="main", help="要导出的分支 ID (默认: main)")
    
    args = parser.parse_args()
    
    export_novel(args.output, args.branch)
