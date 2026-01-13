import asyncio
import argparse
import sys
import os

from .graph import NGEGraph
from .db.base import SessionLocal
from .db.models import Novel
from .scripts.import_novel import import_novel_data
from .services.state_loader import load_initial_state

async def run_generation_task(novel_id: int, branch_id: str = "main"):
    """为指定小说运行生成任务 (CLI 直接运行模式)"""
    initial_state = await load_initial_state(novel_id, branch_id)
    if not initial_state:
        print(f"❌ 无法为小说 ID {novel_id} 加载初始状态，任务中止。")
        return

    print(f"🚀 启动 NovelGen-Enterprise (NGE) 引擎，目标: 小说 ID {novel_id}...")
    graph = NGEGraph()
    
    final_state = await graph.app.ainvoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ 章节生成任务完成！")
    print(f"小说 ID: {final_state.get('current_novel_id')}")
    print(f"当前进度：第 {final_state.get('current_plot_index', 0)} 章节点已处理")
    print("生成样章片段（前200字）：")
    draft = final_state.get('current_draft', "")
    print(draft[:200] if draft else "无内容生成。")
    print("="*50)

async def main():
    parser = argparse.ArgumentParser(description="NovelGen-Enterprise (NGE) CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Init Command ---
    parser_init = subparsers.add_parser("init", help="从文档初始化或更新小说数据")
    parser_init.add_argument("file_path", help="小说设定文档的路径")
    parser_init.add_argument("--novel-id", type=int, help="要更新的现有小说的 ID")
    parser_init.add_argument("--title", help="创建新小说的标题 (如果未提供 novel-id)")
    parser_init.add_argument("--author", help="新小说的作者")
    parser_init.add_argument("--description", help="新小说的描述")
    parser_init.add_argument("--no-llm", action="store_true", help="使用本地回退解析器而非 LLM")

    # --- Run Command ---
    parser_run = subparsers.add_parser("run", help="运行章节生成任务")
    parser_run.add_argument("--novel-id", type=int, required=True, help="要生成章节的小说的 ID")
    parser_run.add_argument("--branch", default="main", help="要生成的分支 (默认: main)")

    args = parser.parse_args()

    if args.command == "init":
        db = SessionLocal()
        novel_id_to_use = args.novel_id
        try:
            if not novel_id_to_use:
                if not args.title:
                    print("❌ 错误: 创建新小说必须提供 --title。")
                    return
                new_novel = Novel(title=args.title, author=args.author, description=args.description)
                db.add(new_novel)
                db.commit()
                novel_id_to_use = new_novel.id
                print(f"✨ 成功创建新小说 '{args.title}' (ID: {novel_id_to_use})")
            else:
                # 验证小说是否存在
                if not db.query(Novel).filter(Novel.id == novel_id_to_use).first():
                    print(f"❌ 错误: 未找到 ID 为 {novel_id_to_use} 的小说。")
                    return
        finally:
            db.close()
        
        await import_novel_data(args.file_path, novel_id_to_use, use_llm=not args.no_llm)

    elif args.command == "run":
        await run_generation_task(novel_id=args.novel_id, branch_id=args.branch)

if __name__ == "__main__":
    asyncio.run(main())
