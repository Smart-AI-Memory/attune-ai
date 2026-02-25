import { useEffect, useState } from "react";
import { fetchAgents, fetchSignals, fetchApprovals } from "../api";
import type { AgentStatus, Signal, ApprovalRequest } from "../api";

const STATUS_COLORS: Record<string, string> = {
  running: "#10b981",
  idle: "#6366f1",
  error: "#ef4444",
  starting: "#fbbf24",
};

const FALLBACK_AGENTS: AgentStatus[] = [
  { agent_id: "code-review-agent", status: "running", progress: 0.72, current_task: "Reviewing pull request #847", display_name: "Code Reviewer" },
  { agent_id: "test-gen-agent", status: "running", progress: 0.45, current_task: "Generating tests for auth module", display_name: "Test Generator" },
  { agent_id: "security-scanner", status: "idle", progress: 1.0, current_task: "Last scan: 2m ago", display_name: "Security Scanner" },
  { agent_id: "doc-generator", status: "idle", progress: 1.0, current_task: "Waiting for assignments", display_name: "Doc Generator" },
];

const FALLBACK_SIGNALS: Signal[] = [
  { signal_type: "task_assigned", source_agent: "orchestrator", target_agent: "code-review-agent", timestamp: new Date(Date.now() - 30000).toISOString() },
  { signal_type: "result_ready", source_agent: "test-gen-agent", target_agent: "orchestrator", timestamp: new Date(Date.now() - 120000).toISOString() },
  { signal_type: "escalation", source_agent: "security-scanner", target_agent: "code-review-agent", timestamp: new Date(Date.now() - 300000).toISOString() },
  { signal_type: "heartbeat", source_agent: "doc-generator", target_agent: "orchestrator", timestamp: new Date(Date.now() - 10000).toISOString() },
];

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return `${Math.floor(diff / 3600000)}h ago`;
}

export default function AgentsView() {
  const [agents, setAgents] = useState<AgentStatus[]>(FALLBACK_AGENTS);
  const [signals, setSignals] = useState<Signal[]>(FALLBACK_SIGNALS);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);

  useEffect(() => {
    const load = () => {
      fetchAgents().then((a) => a.length > 0 && setAgents(a));
      fetchSignals(20).then((s) => s.length > 0 && setSignals(s));
      fetchApprovals().then(setApprovals);
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="tab-content">
      <div className="tab-section">
        <div className="panel-header">
          <h3>Active Agents</h3>
          <span className="panel-badge">{agents.length} registered</span>
        </div>
        <div className="agent-grid">
          {agents.map((agent) => {
            const color = STATUS_COLORS[agent.status] || "#6366f1";
            return (
              <div key={agent.agent_id} className="agent-card">
                <div className="agent-card-header">
                  <div className="agent-card-name">
                    <span className="agent-status-dot" style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }} />
                    {agent.display_name || agent.agent_id}
                  </div>
                  <span className="agent-card-status" style={{ color }}>
                    {agent.status.toUpperCase()}
                  </span>
                </div>
                <div className="agent-card-task">{agent.current_task}</div>
                <div className="agent-progress-wrap">
                  <div
                    className="agent-progress-bar"
                    style={{ width: `${agent.progress * 100}%`, backgroundColor: color }}
                  />
                </div>
                <div className="agent-card-footer">
                  <span className="agent-card-id">{agent.agent_id}</span>
                  <span className="agent-card-progress">{Math.round(agent.progress * 100)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {approvals.length > 0 && (
        <div className="tab-section">
          <div className="panel-header">
            <h3>Pending Approvals</h3>
            <span className="panel-badge approval-badge">{approvals.length} waiting</span>
          </div>
          <div className="approval-list">
            {approvals.map((req) => (
              <div key={req.request_id} className="approval-row">
                <div className="approval-info">
                  <span className="approval-type">{req.approval_type}</span>
                  <span className="approval-agent">from {req.agent_id}</span>
                </div>
                <span className="approval-time">{timeAgo(req.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="tab-section">
        <div className="panel-header">
          <h3>Recent Signals</h3>
          <span className="panel-badge">{signals.length} events</span>
        </div>
        <div className="signal-list">
          {signals.map((sig, i) => (
            <div key={i} className="signal-row">
              <span className="signal-type-badge">{sig.signal_type}</span>
              <span className="signal-route">
                <span className="signal-agent">{sig.source_agent}</span>
                <span className="signal-arrow">&rarr;</span>
                <span className="signal-agent">{sig.target_agent}</span>
              </span>
              <span className="signal-time">{timeAgo(sig.timestamp)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
