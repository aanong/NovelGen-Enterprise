"""
Unit tests for Registry Module
Tests the decorator-based registration system for Agents and Nodes
"""
import pytest
from src.core.registry import (
    register_agent,
    register_node,
    get_agent_class,
    get_node_class,
    list_agents,
    list_nodes,
    _AGENT_REGISTRY,
    _NODE_REGISTRY
)


class TestAgentRegistration:
    """Tests for agent registration functionality"""

    def setup_method(self):
        """Clean up registry before each test"""
        _AGENT_REGISTRY.clear()

    def teardown_method(self):
        """Clean up registry after each test"""
        _AGENT_REGISTRY.clear()

    def test_register_agent_decorator(self):
        """Test that @register_agent decorator registers a class"""
        @register_agent("test_agent")
        class TestAgent:
            pass

        assert "test_agent" in _AGENT_REGISTRY
        assert _AGENT_REGISTRY["test_agent"] is TestAgent

    def test_get_agent_class(self):
        """Test retrieving an agent class by name"""
        class TestAgent:
            pass

        _AGENT_REGISTRY["test_agent"] = TestAgent

        result = get_agent_class("test_agent")
        assert result is TestAgent

    def test_get_agent_class_not_found(self):
        """Test that get_agent_class returns None for unknown agents"""
        result = get_agent_class("nonexistent")
        assert result is None

    def test_list_agents(self):
        """Test listing all registered agents"""
        _AGENT_REGISTRY.clear()
        _AGENT_REGISTRY["agent1"] = type("Agent1", (), {})
        _AGENT_REGISTRY["agent2"] = type("Agent2", (), {})

        result = list_agents()
        assert "agent1" in result
        assert "agent2" in result
        assert len(result) == 2

    def test_list_agents_empty(self):
        """Test listing agents when registry is empty"""
        _AGENT_REGISTRY.clear()
        result = list_agents()
        assert result == []

    def test_register_multiple_agents(self):
        """Test registering multiple agents"""
        @register_agent("agent1")
        class Agent1:
            pass

        @register_agent("agent2")
        class Agent2:
            pass

        @register_agent("agent3")
        class Agent3:
            pass

        assert len(_AGENT_REGISTRY) == 3
        assert "agent1" in _AGENT_REGISTRY
        assert "agent2" in _AGENT_REGISTRY
        assert "agent3" in _AGENT_REGISTRY


class TestNodeRegistration:
    """Tests for node registration functionality"""

    def setup_method(self):
        """Clean up registry before each test"""
        _NODE_REGISTRY.clear()

    def teardown_method(self):
        """Clean up registry after each test"""
        _NODE_REGISTRY.clear()

    def test_register_node_decorator(self):
        """Test that @register_node decorator registers a class"""
        @register_node("test_node")
        class TestNode:
            pass

        assert "test_node" in _NODE_REGISTRY
        assert _NODE_REGISTRY["test_node"] is TestNode

    def test_get_node_class(self):
        """Test retrieving a node class by name"""
        class TestNode:
            pass

        _NODE_REGISTRY["test_node"] = TestNode

        result = get_node_class("test_node")
        assert result is TestNode

    def test_get_node_class_not_found(self):
        """Test that get_node_class returns None for unknown nodes"""
        result = get_node_class("nonexistent")
        assert result is None

    def test_list_nodes(self):
        """Test listing all registered nodes"""
        _NODE_REGISTRY.clear()
        _NODE_REGISTRY["node1"] = type("Node1", (), {})
        _NODE_REGISTRY["node2"] = type("Node2", (), {})

        result = list_nodes()
        assert "node1" in result
        assert "node2" in result
        assert len(result) == 2

    def test_list_nodes_empty(self):
        """Test listing nodes when registry is empty"""
        _NODE_REGISTRY.clear()
        result = list_nodes()
        assert result == []


class TestRegistryIsolation:
    """Tests to ensure registry isolation between agent and node registrations"""

    def setup_method(self):
        """Clean up registries before each test"""
        _AGENT_REGISTRY.clear()
        _NODE_REGISTRY.clear()

    def teardown_method(self):
        """Clean up registries after each test"""
        _AGENT_REGISTRY.clear()
        _NODE_REGISTRY.clear()

    def test_agent_and_node_registries_are_separate(self):
        """Test that agents and nodes don't pollute each other's registries"""
        @register_agent("my_agent")
        class MyAgent:
            pass

        @register_node("my_node")
        class MyNode:
            pass

        assert "my_agent" in _AGENT_REGISTRY
        assert "my_agent" not in _NODE_REGISTRY
        assert "my_node" in _NODE_REGISTRY
        assert "my_node" not in _AGENT_REGISTRY

    def test_get_agent_does_not_return_node(self):
        """Test that get_agent_class doesn't return nodes"""
        class MyNode:
            pass

        _NODE_REGISTRY["my_node"] = MyNode

        result = get_agent_class("my_node")
        assert result is None

    def test_get_node_does_not_return_agent(self):
        """Test that get_node_class doesn't return agents"""
        class MyAgent:
            pass

        _AGENT_REGISTRY["my_agent"] = MyAgent

        result = get_node_class("my_agent")
        assert result is None
