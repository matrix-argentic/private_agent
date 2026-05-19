from pydantic import BaseModel
from typing import List


class IntentOutput(BaseModel):
    intent: str
    matched_tool_ids: List[str]
    matched_kb_ids: List[str]
