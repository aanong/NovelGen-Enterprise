#!/usr/bin/env python3
"""
NovelGen-Enterprise 优化验证脚本
快速检查所有优化是否正常工作
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试新模块是否可以正常导入"""
    print("🔍 测试 1: 检查新模块导入...")
    
    try:
        from src.config import Config
        print("  ✅ Config 模块导入成功")
    except ImportError as e:
        print(f"  ❌ Config 模块导入失败: {e}")
        return False
    
    try:
        from src.utils import strip_think_tags, extract_json_from_text
        print("  ✅ Utils 模块导入成功")
    except ImportError as e:
        print(f"  ❌ Utils 模块导入失败: {e}")
        return False
    
    try:
        from src.monitoring import monitor, PerformanceMonitor
        print("  ✅ Monitoring 模块导入成功")
    except ImportError as e:
        print(f"  ❌ Monitoring 模块导入失败: {e}")
        return False
    
    return True


def test_config():
    """测试配置系统"""
    print("\n🔍 测试 2: 检查配置系统...")
    
    try:
        from src.config import Config
        
        # 验证配置
        validation = Config.validate()
        
        if validation["valid"]:
            print("  ✅ 配置验证通过")
        else:
            print(f"  ⚠️ 配置存在问题:")
            for issue in validation["issues"]:
                print(f"    - {issue}")
        
        # 打印配置
        Config.print_config()
        
        return True
    except Exception as e:
        print(f"  ❌ 配置测试失败: {e}")
        return False


def test_utils():
    """测试工具函数"""
    print("\n🔍 测试 3: 检查工具函数...")
    
    try:
        from src.utils import (
            strip_think_tags,
            extract_json_from_text,
            validate_character_consistency,
            analyze_sentence_length
        )
        
        # 测试 strip_think_tags
        test_text = "<think>思考内容</think>正文内容"
        result = strip_think_tags(test_text)
        assert result == "正文内容", "strip_think_tags 失败"
        print("  ✅ strip_think_tags 工作正常")
        
        # 测试 extract_json_from_text
        test_json = '这是一些文本 {"key": "value"} 更多文本'
        result = extract_json_from_text(test_json)
        assert result == {"key": "value"}, "extract_json_from_text 失败"
        print("  ✅ extract_json_from_text 工作正常")
        
        # 测试 validate_character_consistency
        result = validate_character_consistency(
            "测试角色",
            "角色突然降智了",
            ["降智", "性格突变"]
        )
        assert not result["valid"], "validate_character_consistency 失败"
        print("  ✅ validate_character_consistency 工作正常")
        
        # 测试 analyze_sentence_length
        test_text = "短句。这是一个中等长度的句子。这是一个非常非常非常非常非常非常非常非常非常长的句子。"
        result = analyze_sentence_length(test_text)
        assert "short" in result and "medium" in result and "long" in result
        print("  ✅ analyze_sentence_length 工作正常")
        
        return True
    except Exception as e:
        print(f"  ❌ 工具函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_schema():
    """测试状态 Schema"""
    print("\n🔍 测试 4: 检查状态 Schema...")
    
    try:
        from src.schemas.state import NGEState, AntigravityContext, NovelBible, character_state, MemoryContext
        
        # 创建测试状态
        state = NGEState(
            novel_bible=NovelBible(
                world_view="测试世界观",
                core_settings={}
            ),
            characters={},
            plot_progress=[],
            memory_context=MemoryContext()
        )
        
        # 检查新字段
        assert hasattr(state, 'antigravity_context'), "缺少 antigravity_context"
        assert hasattr(state, 'max_retry_limit'), "缺少 max_retry_limit"
        assert hasattr(state, 'state_version'), "缺少 state_version"
        
        print("  ✅ NGEState 包含所有新字段")
        
        # 检查 AntigravityContext
        assert hasattr(state.antigravity_context, 'character_anchors'), "缺少 character_anchors"
        assert hasattr(state.antigravity_context, 'scene_constraints'), "缺少 scene_constraints"
        assert hasattr(state.antigravity_context, 'violated_rules'), "缺少 violated_rules"
        
        print("  ✅ AntigravityContext 结构正确")
        
        # 测试设置人物禁忌
        state.antigravity_context.character_anchors["测试角色"] = ["禁忌1", "禁忌2"]
        assert len(state.antigravity_context.character_anchors["测试角色"]) == 2
        
        print("  ✅ 人物禁忌设置功能正常")
        
        return True
    except Exception as e:
        print(f"  ❌ 状态 Schema 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_models():
    """测试数据库模型"""
    print("\n🔍 测试 5: 检查数据库模型...")
    
    try:
        from src.db.models import (
            NovelBible, Character, CharacterRelationship,
            PlotOutline, Chapter, LogicAudit
        )
        
        # 检查索引定义
        assert hasattr(NovelBible, '__table_args__'), "NovelBible 缺少 __table_args__"
        print("  ✅ NovelBible 包含索引定义")
        
        # 检查关系
        assert hasattr(Character, 'relationships_as_a'), "Character 缺少关系定义"
        assert hasattr(Character, 'relationships_as_b'), "Character 缺少关系定义"
        print("  ✅ Character 关系定义正确")
        
        assert hasattr(Chapter, 'audits'), "Chapter 缺少 audits 关系"
        print("  ✅ Chapter 关系定义正确")
        
        return True
    except Exception as e:
        print(f"  ❌ 数据库模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_monitoring():
    """测试性能监控"""
    print("\n🔍 测试 6: 检查性能监控...")
    
    try:
        from src.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor(log_file=".test_performance.json")
        
        # 测试会话记录
        session_id = monitor.start_session(1)
        monitor.log_agent_call(session_id, "TestAgent", 1.5, 100, True)
        monitor.end_session(session_id, True, 0)
        
        # 获取摘要
        summary = monitor.get_summary()
        assert summary["total_chapters"] == 1
        assert summary["successful_chapters"] == 1
        
        print("  ✅ 性能监控功能正常")
        
        # 清理测试文件
        import os
        if os.path.exists(".test_performance.json"):
            os.remove(".test_performance.json")
        
        return True
    except Exception as e:
        print(f"  ❌ 性能监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("🚀 NovelGen-Enterprise 优化验证")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("配置系统", test_config),
        ("工具函数", test_utils),
        ("状态Schema", test_state_schema),
        ("数据库模型", test_database_models),
        ("性能监控", test_monitoring),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统优化成功！")
        print("\n下一步:")
        print("1. 执行数据库迁移: python -m src.scripts.migrate_db upgrade")
        print("2. 运行主程序测试: python -m src.main")
        print("3. 查看性能报告: python -m src.monitoring")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
