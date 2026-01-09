import sys
import os
import json
from typing import List, Dict
from sqlalchemy.orm import Session
from src.db.base import SessionLocal
from src.db.models import ReferenceMaterial
from src.utils import get_embedding

# 示例数据
REFERENCES_DATA = [
    {
        "title": "修真境界划分",
        "source": "通用修真设定",
        "category": "world_setting",
        "tags": ["修真", "境界", "升级"],
        "content": """
        练气期：引气入体，洗髓伐毛，寿元百岁。
        筑基期：铸就道基，真气化液，寿元二百。
        金丹期：凝结金丹，法力无边，寿元五百。
        元婴期：碎丹成婴，神游太虚，寿元千载。
        化神期：感悟天地，掌控法则，寿元三千。
        炼虚期：破碎虚空，遨游星海，寿元万载。
        合体期：身融天地，法力无尽，寿元十万。
        大乘期：渡劫飞升，成就仙体，寿元百万。
        """
    },
    {
        "title": "赛博朋克核心元素",
        "source": "Cyberpunk Genre",
        "category": "world_setting",
        "tags": ["科幻", "赛博朋克", "反乌托邦"],
        "content": """
        高科技，低生活 (High Tech, Low Life)。
        霓虹灯下的贫民窟，巨型企业的垄断统治。
        义体改造：人类通过机械义肢、神经植入物增强自身能力，但也面临赛博精神病的风险。
        网络空间：黑客通过脑机接口潜入数据网络，进行信息窃取和破坏。
        """
    },
    {
        "title": "孤胆英雄原型",
        "source": "Character Archetypes",
        "category": "character_archetype",
        "tags": ["英雄", "孤独", "正义"],
        "content": """
        孤胆英雄通常是一个被社会边缘化或自我放逐的人物。
        他们拥有某种特殊的技能或过去，不信任体制，倾向于独自解决问题。
        核心动机往往是复仇、赎罪或守护某个弱小的存在。
        性格特征：沉默寡言、坚韧不拔、内心柔软但外表冷酷。
        """
    },
    {
        "title": "退婚流开局",
        "source": "网文经典桥段",
        "category": "plot_trope",
        "tags": ["退婚", "打脸", "逆袭"],
        "content": """
        主角开局遭遇未婚妻/夫上门退婚，通常伴随着羞辱和家族的压力。
        主角立下誓言（如“三十年河东，三十年河西”），从此发愤图强。
        这一桥段的核心在于制造强烈的压抑感和后续的爽感释放。
        """
    },
    {
        "title": "克苏鲁神话风格",
        "source": "H.P. Lovecraft",
        "category": "style",
        "tags": ["恐怖", "不可名状", "古神"],
        "content": """
        人类最古老而强烈的情感是恐惧，而最古老而强烈的恐惧是对未知的恐惧。
        描写重点在于氛围的渲染，使用大量的形容词如“不可名状”、“亵渎”、“扭曲”。
        强调人类在宇宙中的渺小和无知，接触真相往往意味着疯狂。
        """
    },
    {
        "title": "无限流设定",
        "source": "无限恐怖",
        "category": "world_setting",
        "tags": ["无限流", "主神空间", "任务"],
        "content": """
        主角被召唤到一个神秘的空间（主神空间），必须在不同的恐怖片或异世界中完成任务才能生存。
        完成任务可获得奖励点数，用于强化身体、兑换血统或武器。
        核心在于生存压力和团队合作，以及对人性的考验。
        """
    }
]

def seed_references():
    db = SessionLocal()
    try:
        print("📚 开始导入经典文献资料...")
        
        for item in REFERENCES_DATA:
            # 检查是否已存在
            existing = db.query(ReferenceMaterial).filter(
                ReferenceMaterial.title == item["title"]
            ).first()
            
            if existing:
                print(f"  ⚠️ 跳过已存在: {item['title']}")
                continue
            
            print(f"  Processing: {item['title']}...")
            
            # 生成 Embedding
            try:
                embedding = get_embedding(item["content"])
            except Exception as e:
                print(f"  ❌ Embedding 生成失败: {e}")
                continue
            
            # 创建记录
            ref = ReferenceMaterial(
                title=item["title"],
                source=item["source"],
                category=item["category"],
                tags=item["tags"],
                content=item["content"],
                embedding=embedding
            )
            db.add(ref)
            print(f"  ✅ 已添加: {item['title']}")
            
        db.commit()
        print("🎉 资料导入完成！")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_references()
