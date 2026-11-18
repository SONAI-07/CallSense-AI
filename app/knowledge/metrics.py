from prometheus_client import Counter, Histogram

ROUTE_TOTAL = Counter("knowledge_route_total", "Knowledge gate routing decisions", ["destination", "mode"])
GATE_SECONDS = Histogram("knowledge_gate_seconds", "Knowledge gate latency")
JEV_SECONDS = Histogram("knowledge_jev_seconds", "Jev decision latency")
JEV_FALLBACK = Counter("knowledge_jev_fallback_total", "Jev fallbacks to local cascade", ["reason"])