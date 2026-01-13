from typing import Dict, Any
from ..schemas.state import NGEState
from ..agents.constants import NodeAction
from ..agents.writer import WriterAgent
from .base import BaseNode

class WriteNode(BaseNode):
    def __init__(self, writer: WriterAgent):
        self.writer = writer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        print("--- WRITING CHAPTER ---")
        draft = await self.writer.write_chapter(state, state.review_feedback)
        return {"current_draft": draft, "next_action": NodeAction.REVIEW}
