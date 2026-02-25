export interface HealthData {
  status: string;
  redis_available: boolean;
  active_agents: number;
  pending_approvals: number;
  timestamp: string;
}

export interface AgentStatus {
  agent_id: string;
  status: string;
  progress: number;
  current_task: string;
  display_name?: string;
  last_seen?: string;
}

export interface QualityMetrics {
  workflow: string;
  stage: string;
  tier: string;
  avg_quality: number;
  sample_count: number;
}

export interface Signal {
  signal_type: string;
  source_agent: string;
  target_agent: string;
  timestamp: string;
  payload?: Record<string, unknown>;
}

export interface ApprovalRequest {
  request_id: string;
  approval_type: string;
  agent_id: string;
  context: Record<string, unknown>;
  timestamp: string;
  timeout_seconds: number;
}

export interface ServiceHealth {
  name: string;
  description: string;
  status: "HEALTHY" | "WARNING" | "DOWN";
  latency_ms: number | null;
  buffer_size?: number;
}

export interface DashboardEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
  source: string;
}

async function fetchJSON<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchHealth(): Promise<HealthData> {
  return fetchJSON("/api/health", {
    status: "unavailable",
    redis_available: false,
    active_agents: 0,
    pending_approvals: 0,
    timestamp: new Date().toISOString(),
  });
}

export function fetchAgents(): Promise<AgentStatus[]> {
  return fetchJSON("/api/agents", []);
}

export function fetchQualityMetrics(): Promise<QualityMetrics[]> {
  return fetchJSON("/api/feedback/workflows", []);
}

export function fetchSignals(limit = 50): Promise<Signal[]> {
  return fetchJSON(`/api/signals?limit=${limit}`, []);
}

export function fetchApprovals(): Promise<ApprovalRequest[]> {
  return fetchJSON("/api/approvals", []);
}

export function fetchEvents(limit = 30): Promise<DashboardEvent[]> {
  return fetchJSON(`/api/events?limit=${limit}`, []);
}

export function fetchUnderperforming(threshold = 0.7): Promise<QualityMetrics[]> {
  return fetchJSON(`/api/feedback/underperforming?threshold=${threshold}`, []);
}

export function fetchServiceHealth(): Promise<ServiceHealth[]> {
  return fetchJSON("/api/system/services", []);
}
