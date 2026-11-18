from pydantic import BaseModel


class RouteDecision(BaseModel):
    p_llm_direct: float = 0.0
    p_tenant_rag: float = 0.0
    p_commercial_db: float = 0.0
    p_call_state_db: float = 0.0
    p_action_tool: float = 0.0
    p_deflect: float = 0.0
    p_product_intent: float = 0.0
    p_needs_grounding: float = 0.0
    confidence: float = 0.0

    def ranked(self) -> list[tuple[str, float]]:
        return sorted([
            ("llm_direct", self.p_llm_direct), ("tenant_rag", self.p_tenant_rag),
            ("commercial_db", self.p_commercial_db), ("call_state_db", self.p_call_state_db),
            ("action_tool", self.p_action_tool), ("deflect", self.p_deflect),
        ], key=lambda kv: -kv[1])