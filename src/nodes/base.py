from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..schemas.state import NGEState

class BaseNode(ABC):
    """
    Base class for all graph nodes.
    """
    
    @abstractmethod
    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """
        Process the node.
        """
        pass
