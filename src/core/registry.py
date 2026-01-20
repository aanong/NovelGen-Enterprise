"""
Registry Module
Registry pattern for managing Agents and Nodes
"""

_AGENT_REGISTRY = {}
_NODE_REGISTRY = {}

def register_agent(name):
    """
    Decorator to register an Agent class
    
    Usage:
        @register_agent("writer")
        class WriterAgent(BaseAgent):
            ...
    """
    def decorator(cls):
        _AGENT_REGISTRY[name] = cls
        return cls
    return decorator

def register_node(name):
    """
    Decorator to register a Node class
    
    Usage:
        @register_node("write")
        class WriteNode(BaseNode):
            ...
    """
    def decorator(cls):
        _NODE_REGISTRY[name] = cls
        return cls
    return decorator

def get_agent_class(name: str):
    """Get an Agent class by name"""
    return _AGENT_REGISTRY.get(name)

def get_node_class(name: str):
    """Get a Node class by name"""
    return _NODE_REGISTRY.get(name)

def list_agents() -> list:
    """List all registered agent names"""
    return list(_AGENT_REGISTRY.keys())

def list_nodes() -> list:
    """List all registered node names"""
    return list(_NODE_REGISTRY.keys())
