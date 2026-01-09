"""
资料库数据导入工具
支持从 JSON 文件批量导入参考资料到向量数据库。

使用方法:
    python -m src.scripts.import_references <file_path>

JSON 文件格式示例:
[
    {
        "title": "资料标题",
        "content": "资料详细内容...",
        "source": "来源（可选）",
        "category": "分类（可选，如 world_setting, plot_trope, character_archetype, style）",
        "tags": ["标签1", "标签2"]
    },
    ...
]
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
from src.db.models import ReferenceMaterial
from src.utils import get_embedding

def import_references(file_path: str):
    """从文件导入参考资料"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print("❌ JSON 格式错误: 根元素必须是列表")
            return
            
        print(f"📂 正在处理文件: {file_path}")
        print(f"📊 发现 {len(data)} 条记录")
        
        db = SessionLocal()
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
                
            # 检查是否存在
            existing = db.query(ReferenceMaterial).filter(
                ReferenceMaterial.title == title
            ).first()
            
            if existing:
                print(f"  ⚠️ 跳过已存在: {title}")
                skip_count += 1
                continue
            
            print(f"  Processing: {title}...")
            
            try:
                # 生成 Embedding
                embedding = get_embedding(content)
                
                ref = ReferenceMaterial(
                    title=title,
                    content=content,
                    source=item.get("source", "User Import"),
                    category=item.get("category", "uncategorized"),
                    tags=item.get("tags", []),
                    embedding=embedding
                )
                db.add(ref)
                success_count += 1
                
                # 每 10 条提交一次，避免内存过大
                if success_count % 10 == 0:
                    db.commit()
                    
            except Exception as e:
                print(f"  ❌ 处理失败 ({title}): {e}")
                fail_count += 1
        
        db.commit()
        print("\n" + "="*40)
        print(f"🎉 导入完成!")
        print(f"✅ 成功: {success_count}")
        print(f"⚠️ 跳过: {skip_count}")
        print(f"❌ 失败: {fail_count}")
        
    except json.JSONDecodeError:
        print("❌ JSON 解析失败: 请检查文件格式")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="资料库批量导入工具")
    parser.add_argument("file", help="包含资料数据的 JSON 文件路径")
    args = parser.parse_args()
    
    import_references(args.file)
