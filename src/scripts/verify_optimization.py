"""
Optimization Verification Script
Checks the structural integrity of the refactored codebase.
"""
import sys
import os
import inspect
from typing import Type

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def check_agent_inheritance():
    print("\n🔍 Checking Agent Inheritance...")
    try:
        from src.agents.base import BaseAgent
        from src.agents.writer import WriterAgent
        from src.agents.reviewer import ReviewerAgent
        from src.agents.evolver import CharacterEvolver
        from src.agents.architect import ArchitectAgent
        
        agents = [WriterAgent, ReviewerAgent, CharacterEvolver, ArchitectAgent]
        all_passed = True
        
        for agent_cls in agents:
            if issubclass(agent_cls, BaseAgent):
                print(f"  ✅ {agent_cls.__name__} inherits from BaseAgent")
            else:
                print(f"  ❌ {agent_cls.__name__} does NOT inherit from BaseAgent")
                all_passed = False
                
        return all_passed
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def check_vector_store():
    print("\n🔍 Checking VectorStore API...")
    try:
        from src.db.vector_store import VectorStore
        
        if hasattr(VectorStore, 'search'):
            print("  ✅ VectorStore has 'search' method")
        else:
            print("  ❌ VectorStore missing 'search' method")
            return False
            
        # Check signature or basic usage if possible (static analysis)
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def check_service_layer():
    print("\n🔍 Checking Service Layer...")
    services = [
        "src.services.generation_service",
        "src.services.novel_service",
        "src.services.reference_service",
        "src.services.chapter_service",
        "src.services.outline_service",
        "src.services.character_service",
        "src.services.relationship_service",
        "src.services.world_service"
    ]
    
    all_passed = True
    for svc in services:
        try:
            __import__(svc, fromlist=['*'])
            print(f"  ✅ Imported {svc}")
        except ImportError as e:
            print(f"  ❌ Failed to import {svc}: {e}")
            all_passed = False
    return all_passed

def check_nodes_modularity():
    print("\n🔍 Checking Graph Nodes Modularity...")
    nodes = [
        "src.nodes.base",
        "src.nodes.planner",
        "src.nodes.writer",
        "src.nodes.reviewer",
        "src.nodes.evolver",
        "src.nodes.refiner",
        "src.nodes.loader"
    ]
    all_passed = True
    for node in nodes:
        try:
            __import__(node, fromlist=['*'])
            print(f"  ✅ Imported {node}")
        except ImportError as e:
            print(f"  ❌ Failed to import {node}: {e}")
            all_passed = False
    return all_passed

def main():
    print("🚀 Starting Optimization Verification...\n")
    
    results = [
        check_agent_inheritance(),
        check_vector_store(),
        check_service_layer(),
        check_nodes_modularity()
    ]
    
    print("\n" + "="*30)
    if all(results):
        print("✨ All checks passed! The codebase is structurally sound.")
        exit(0)
    else:
        print("⚠️ Some checks failed. Please review the logs.")
        exit(1)

if __name__ == "__main__":
    main()
