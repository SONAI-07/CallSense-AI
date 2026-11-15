from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentResponse(BaseModel):
    id: int
    name: str
    language_code: str
    voice_id: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentStatsResponse(AgentResponse):
    calls: int
    connected: int
    interested: int
    meetings: int


class CampaignResponse(BaseModel):
    id: int
    agent_id: int
    name: str
    status: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)