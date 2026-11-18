from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.business_action import BusinessActionExecution
from app.models.call import Call
from app.models.usage_record import UsageRecord

# Published catalog until a plans table exists; keep in sync with frontend pricing.
PLAN_CATALOG = (
    "Starter $0/mo: 1 agent, 100 outbound minutes. "
    "Growth $18/mo ($15 billed annually): 5 agents, 1000 minutes, transcripts, WhatsApp/email actions, API keys. "
    "Enterprise: custom, unlimited agents/minutes, SSO, audit logs, SLA."
)


async def commercial(tenant_id: int) -> str:
    async with AsyncSessionLocal() as s:
        seconds = (await s.execute(
            select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
                UsageRecord.tenant_id == tenant_id, UsageRecord.usage_type == "CALL_DURATION")
        )).scalar()
    return f"Published plans: {PLAN_CATALOG}\nThis workspace billed call-seconds to date: {seconds}"


async def call_state(tenant_id: int, call_sid: str | None) -> str:
    if not call_sid:
        return "no active call"
    async with AsyncSessionLocal() as s:
        call = (await s.execute(select(Call).where(
            Call.tenant_id == tenant_id, Call.twilio_call_sid == call_sid))).scalar_one_or_none()
        if call is None:
            return "no active call"
        actions = (await s.execute(select(
            BusinessActionExecution.action, BusinessActionExecution.status
        ).where(BusinessActionExecution.call_id == call.id))).all()
    lines = "; ".join(f"{a}={st}" for a, st in actions) or "none yet"
    return f"call status={call.status}; actions: {lines}"