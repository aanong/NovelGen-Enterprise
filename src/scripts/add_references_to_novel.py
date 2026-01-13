"""
为小说添加资料库的 CLI 工具
支持从 JSON 文件批量导入资料库到指定小说
"""
import argparse
import json
import os
import sys
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.base import SessionLocal
from src.db.models import Novel, ReferenceMaterial
from src.utils import get_embedding


def add_references_to_novel(novel_id: int, file_path: str, skip_existing: bool = True):
    """
    为指定小说添加资料库
    
    Args:
        novel_id: 小说ID
        file_path: JSON 文件路径
        skip_existing: 是否跳过已存在的资料（基于标题）
    """
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    db = SessionLocal()
    try:
        # 验证小说存在
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            print(f"❌ 小说 ID {novel_id} 不存在")
            return
        
        print(f"📚 为小说 '{novel.title}' (ID: {novel_id}) 添加资料库...")
        
        # 读取 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("❌ JSON 格式错误: 根元素必须是列表")
            return
        
        print(f"📊 发现 {len(data)} 条记录")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for item in data:
            title = item.get("title")
            content = item.get("content")
            
            if not title or not content:
                print(f"  ⚠️ 跳过无效记录: 缺少 title 或 content")
                fail_count += 1
                continue
            
            # 检查是否已存在（在同一小说中）
            existing = db.query(ReferenceMaterial).filter(
                ReferenceMaterial.novel_id == novel_id,
                ReferenceMaterial.title == title
            ).first()
            
            if existing:
                if skip_existing:
                    print(f"  ⚠️ 跳过已存在: {title}")
                    skip_count += 1
                    continue
                else:
                    print(f"  ⚠️ 更新已存在: {title}")
                    # 更新现有记录
                    existing.content = content
                    existing.source = item.get("source", existing.source)
                    existing.category = item.get("category", existing.category)
                    existing.tags = item.get("tags", existing.tags or [])
                    # 重新生成 embedding
                    try:
                        existing.embedding = get_embedding(content)
                    except Exception as e:
                        print(f"  ❌ Embedding 生成失败: {e}")
                        fail_count += 1
                        continue
                    success_count += 1
                    continue
            
            print(f"  Processing: {title}...")
            
            try:
                # 生成 Embedding
                embedding = get_embedding(content)
                
                # 创建资料库条目
                ref = ReferenceMaterial(
                    title=title,
                    content=content,
                    source=item.get("source"),
                    category=item.get("category"),
                    tags=item.get("tags", []),
                    novel_id=novel_id,
                    embedding=embedding
                )
                db.add(ref)
                success_count += 1
                print(f"  ✅ 已添加: {title}")
            except Exception as e:
                print(f"  ❌ 添加失败 '{title}': {e}")
                fail_count += 1
        
        db.commit()
        print(f"\n🎉 导入完成！")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ⚠️ 跳过: {skip_count}")
        print(f"  ❌ 失败: {fail_count}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        db.rollback()
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def list_novel_references(novel_id: int, category: str = None):
    """
    列出指定小说的资料库
    """
    db = SessionLocal()
    try:
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            print(f"❌ 小说 ID {novel_id} 不存在")
            return
        
        print(f"📚 小说 '{novel.title}' (ID: {novel_id}) 的资料库：\n")
        
        query = db.query(ReferenceMaterial).filter(ReferenceMaterial.novel_id == novel_id)
        if category:
            query = query.filter(ReferenceMaterial.category == category)
        
        references = query.order_by(ReferenceMaterial.created_at.desc()).all()
        
        if not references:
            print("  (无资料库)")
            return
        
        for ref in references:
            print(f"  [{ref.id}] {ref.title}")
            print(f"      分类: {ref.category or '未分类'}")
            print(f"      来源: {ref.source or 'N/A'}")
            print(f"      内容: {ref.content[:100]}...")
            print()
        
        print(f"总计: {len(references)} 条")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="为小说添加资料库")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 添加资料库命令
    add_parser = subparsers.add_parser("add", help="添加资料库到小说")
    add_parser.add_argument("novel_id", type=int, help="小说ID")
    add_parser.add_argument("file_path", help="JSON 文件路径")
    add_parser.add_argument("--update", action="store_true", help="更新已存在的资料（而不是跳过）")
    
    # 列出资料库命令
    list_parser = subparsers.add_parser("list", help="列出小说的资料库")
    list_parser.add_argument("novel_id", type=int, help="小说ID")
    list_parser.add_argument("--category", help="过滤分类")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_references_to_novel(args.novel_id, args.file_path, skip_existing=not args.update)
    elif args.command == "list":
        list_novel_references(args.novel_id, args.category)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
