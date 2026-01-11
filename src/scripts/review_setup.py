"""
设定审查与完善脚本 (Setup Reviewer)
使用 Gemini 3 Pro 对小说设定进行逻辑审查、漏洞检测和自动补全。
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from ..config import Config
from ..db.vector_store import VectorStore
from ..utils import normalize_llm_content

load_dotenv()


class SetupReviewer:
    """设定审查专家 Agent"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=Config.model.SETUP_REVIEWER_MODEL,
            temperature=Config.model.SETUP_REVIEWER_TEMP,
            google_api_key=Config.model.GEMINI_API_KEY
        )
        self.vector_store = VectorStore()
    
    async def review_and_enhance(self, raw_setup: str) -> dict:
        """
        对原始设定进行全方位审查和增强
        """
        # 1. 检索相关参考资料
        print("📚 正在检索经典文献资料...")
        references = await self.vector_store.search_references(raw_setup, top_k=3)
        ref_context = ""
        if references:
            ref_context = "\n【参考资料库推荐】\n"
            for ref in references:
                ref_context += f"- **{ref['title']}** ({ref['category']}): {ref['content'][:200]}...\n"
        
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一位资深的玄幻小说世界观架构师和逻辑审查专家。\n"
                "你的任务是对用户提供的小说设定进行深度分析，找出以下问题：\n"
                "1. **逻辑漏洞**：修炼体系是否自洽？境界划分是否合理？\n"
                "2. **人物关系**：角色之间的关系网是否完整？是否有遗漏的重要关系？\n"
                "3. **地理体系**：世界的空间结构是否清晰？关键地点是否都有描述？\n"
                "4. **大纲完整性**：剧情节奏是否合理？是否有跳跃或断层？\n\n"
                "**特别要求**：\n"
                "- 在扩展人物、地点、势力时，必须参照《山海经》《易经》《诗经》《淮南子》《楚辞》《搜神记》进行命名。\n"
                "- 人物名：可用《诗经》中的意象（如'采薇''蒹葭''清扬'）或《易经》卦象（如'乾元''坤德''离明'）。\n"
                "- 地点名：参考《山海经》的山川名（如'不周山''归墟''扶桑''青丘'）、《淮南子》的天文地理（如'九州''四海''八极'）、《楚辞》的神话空间（如'阊阖''瑶台''云梦'）。\n"
                "- 异兽/神物：参考《搜神记》《山海经》中的神兽（如'烛龙''毕方''鲲鹏''九尾狐'）。\n"
                "- 势力名：结合古典意象，体现其特质（如'蓬莱仙阁''归藏书院''太玄道宗'）。\n\n"
                "{ref_context}\n"
                "请以专业编辑的角度，提供详细的审查报告和改进建议。"
            )),
            ("human", (
                "以下是小说的原始设定文档：\n\n"
                "```\n{raw_setup}\n```\n\n"
                "请按以下格式输出你的审查结果：\n\n"
                "## 一、逻辑漏洞检测与修复方案\n"
                "[详细列出发现的所有逻辑问题，并为每个问题提供具体的修复方案]\n\n"
                "## 二、修炼体系深度分析与重构\n"
                "[评估修炼体系，并提供一份清晰的对照表]\n\n"
                "## 三、人物扩展与关系网\n"
                "[补充关键角色，包括性格、动机和禁忌。主要配角不少于 20 个。]\n"
                "- **命名规范**：参考《诗经》《易经》《楚辞》命名，注明出处。\n\n"
                "## 四、世界地理与势力扩展\n"
                "[补充 10 个关键地点和 5 个核心势力。]\n\n"
                "## 五、完整章节大纲\n"
                "[根据重构后的逻辑生成一份详细的大纲目录。要求：分卷结构，至少包含 20 个核心剧情转折点章节名及梗概。不要生成上千章无关紧要的列表，重点放在主线逻辑。]\n\n"
                "## 六、最终完善版设定文档\n"
                "**直接输出修正后的完整设定文本，内容需包含：**\n"
                "- 完善后的世界观与核心规则\n"
                "- 人物小传（含新增角色）\n"
                "- 修炼体系对照表\n"
                "- 文风要求\n"
                "（这段文字将直接作为生成程序的输入，请务必保证信息量充足且格式清晰）"
            ))
        ])
        
        print("🔍 正在调用 Gemini 3 Pro 进行深度审查...")
        response = await self.llm.ainvoke(
            review_prompt.format(raw_setup=raw_setup, ref_context=ref_context)
        )
        
        content = normalize_llm_content(response.content)
        
        # 解析返回的结构化内容
        sections = {
            "logic_fixes": self._extract_section(content, "一、逻辑漏洞检测与修复方案"),
            "cultivation_system": self._extract_section(content, "二、修炼体系深度分析与重构"),
            "character_expansion": self._extract_section(content, "三、人物扩展与关系网"),
            "world_geography": self._extract_section(content, "四、世界地理与势力扩展"),
            "chapter_directory": self._extract_section(content, "五、完整章节大纲"),
            "final_setup": self._extract_section(content, "六、最终完善版设定文档")
        }
        
        return sections
    
    def _extract_section(self, content: str, section_title: str) -> str:
        """
        从 Markdown 格式中提取特定章节。
        改进逻辑：不再简单地在遇到下一个 '## ' 时停止，而是根据 section_title 的特征进行匹配。
        """
        import re
        
        # 匹配标题的正则，如 "## 七、最终完善版设定文档"
        # 允许标题前后有其他文字，只要包含关键词即可
        escaped_title = re.escape(section_title)
        pattern = rf"## .*?{escaped_title}.*?\n(.*?)(?=\n## |$)"
        
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # 清理可能的代码块包裹
            if extracted.startswith("```markdown"):
                extracted = extracted[11:].strip()
            if extracted.startswith("```"):
                extracted = extracted[3:].strip()
            if extracted.endswith("```"):
                extracted = extracted[:-3].strip()
            
            if extracted:
                return extracted

        # 回退逻辑：如果正则没匹配到，尝试精确匹配
        lines = content.split('\n')
        capturing = False
        result = []
        
        for line in lines:
            if section_title in line and line.startswith('## '):
                capturing = True
                continue
            if capturing:
                # 只有在遇到另一个同级别的引导标题时才停止
                # 引导标题通常带有一、二、三或数字编号
                if line.startswith('## ') and re.search(r'[一二三四五六七八九十\d]', line):
                    # 检查是否是真的下一个导航节，而不是内容中的子标题
                    if section_title not in line:
                        break
                result.append(line)
        
        extracted = '\n'.join(result).strip()
        
        # 清理代码块
        if extracted.startswith("```"):
            extracted = re.sub(r'^```(markdown)?\n', '', extracted)
            extracted = re.sub(r'\n```$', '', extracted)

        # 如果是最终设定且提取失败，最后尝试返回整个文档（作为保底）
        if not extracted and "最终完善版设定" in section_title:
            return content
        
        return extracted


async def main(input_file: str, output_dir: str = "./reviewed_setups"):
    """主流程"""
    print(f"📂 读取设定文件: {input_file}")
    
    if not os.path.exists(input_file):
        print("❌ 文件不存在")
        return
    
    with open(input_file, "r", encoding="utf-8") as f:
        raw_setup = f.read()
    
    reviewer = SetupReviewer()
    
    try:
        result = await reviewer.review_and_enhance(raw_setup)
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存审查报告
        report_path = os.path.join(output_dir, "review_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 小说设定深度审查报告\n\n")
            f.write("## 一、逻辑漏洞检测与修复方案\n")
            f.write(result["logic_fixes"] + "\n\n")
            f.write("## 二、修炼体系深度分析与重构\n")
            f.write(result["cultivation_system"] + "\n\n")
            f.write("## 三、人物扩展与关系网\n")
            f.write(result["character_expansion"] + "\n\n")
            f.write("## 四、世界地理与势力扩展\n")
            f.write(result["world_geography"] + "\n\n")
            f.write("## 五、完整章节大纲\n")
            f.write(result["chapter_directory"] + "\n\n")
        
        print(f"✅ 审查报告已保存至: {report_path}")
        
        # 保存完善后的设定
        enhanced_path = os.path.join(output_dir, "enhanced_setup.txt")
        with open(enhanced_path, "w", encoding="utf-8") as f:
            f.write(result["final_setup"])
        
        print(f"✅ 完善后的设定已保存至: {enhanced_path}")
        print("\n" + "="*60)
        print("🎉 审查完成！你可以：")
        print(f"1. 查看审查报告: {report_path}")
        print(f"2. 使用完善后的设定导入系统:")
        print(f"   python -m src.scripts.import_novel {enhanced_path}")
        
    except Exception as e:
        print(f"❌ 审查过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="审查并完善小说设定")
    parser.add_argument("file", help="设定文件路径")
    parser.add_argument("--output", default="./reviewed_setups", help="输出目录")
    args = parser.parse_args()
    
    asyncio.run(main(args.file, args.output))
