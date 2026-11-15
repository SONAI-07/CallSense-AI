from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.agent.action import BusinessAction
from app.agent.classification import CustomerClassification
from app.core.database import get_db
from app.models.agent import Agent
from app.models.business_action import BusinessActionExecution
from app.models.call import Call
from app.models.call_insights import CallInsight
from app.models.tenant import Tenant
from app.repositories.agent_repo import AgentRepository
from app.repositories.campaign_repo import CampaignRepository
from app.schemas.agent_schema import AgentResponse, AgentStatsResponse, CampaignResponse

router = APIRouter(prefix="/agents", tags=["agents"])
campaign_router = APIRouter(prefix="/campaigns", tags=["campaigns"])

agent_repository = AgentRepository()
campaign_repository = CampaignRepository()


@router.get("", response_model=list[AgentStatsResponse])
async def list_agents(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    agents = await agent_repository.list_for_tenant(session=db, tenant_id=tenant.id)
    out: list[AgentStatsResponse] = []
    for a in agents:
        calls = await db.scalar(
            select(func.count(Call.id)).where(Call.tenant_id == tenant.id, Call.agent_id == a.id)
        ) or 0
        connected = await db.scalar(
            select(func.count(Call.id)).where(
                Call.tenant_id == tenant.id, Call.agent_id == a.id, Call.status == "completed"
            )
        ) or 0
        interested = await db.scalar(
            select(func.count(CallInsight.id))
            .join(Call, Call.id == CallInsight.call_id)
            .where(
                Call.tenant_id == tenant.id,
                Call.agent_id == a.id,
                CallInsight.classification == CustomerClassification.STRONG.value,
            )
        ) or 0
        meetings = await db.scalar(
            select(func.count(BusinessActionExecution.id))
            .join(Call, Call.id == BusinessActionExecution.call_id)
            .where(
                Call.tenant_id == tenant.id,
                Call.agent_id == a.id,
                BusinessActionExecution.action == BusinessAction.SCHEDULE_FOLLOW_UP.value,
                BusinessActionExecution.status == "executed",
            )
        ) or 0
        out.append(
            AgentStatsResponse(
                id=a.id, name=a.name, language_code=a.language_code, voice_id=a.voice_id,
                is_active=a.is_active, created_at=a.created_at,
                calls=calls, connected=connected, interested=interested, meetings=meetings,
            )
        )
    return out


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    agent = await agent_repository.get_by_id_for_tenant(
        session=db, agent_id=agent_id, tenant_id=tenant.id
    )
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@campaign_router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await campaign_repository.list_for_tenant(session=db, tenant_id=tenant.id)