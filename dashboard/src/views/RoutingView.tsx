import { useEffect, useState } from "react";
import { fetchSignals, fetchEvents } from "../api";
import type { Signal, DashboardEvent } from "../api";

interface TierStat {
  name: string;
  tier: string;
  percent: number;
  cost: string;
  color: string;
  tasks: number;
  avgLatency: string;
}

const TIER_STATS: TierStat[] = [
  { name: "Haiku 4.5", tier: "cheap", percent: 62, cost: "$0.12/task", color: "#10b981", tasks: 773, avgLatency: "1.2s" },
  { name: "Sonnet 4.6", tier: "capable", percent: 28, cost: "$0.48/task", color: "#6366f1", tasks: 349, avgLatency: "3.8s" },
  { name: "Opus 4.6", tier: "premium", percent: 10, cost: "$2.10/task", color: "#8b5cf6", tasks: 125, avgLatency: "8.1s" },
];

const ESCALATION_REASONS = [
  { from: "Haiku", to: "Sonnet", reason: "Quality below threshold", count: 87, color: "#f59e0b" },
  { from: "Sonnet", to: "Opus", reason: "Complex reasoning required", count: 34, color: "#8b5cf6" },
  { from: "Haiku", to: "Sonnet", reason: "Multi-step analysis needed", count: 52, color: "#6366f1" },
  { from: "Sonnet", to: "Opus", reason: "Code generation > 200 lines", count: 18, color: "#ef4444" },
];

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return `${Math.floor(diff / 3600000)}h ago`;
}

export default function RoutingView() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [events, setEvents] = useState<DashboardEvent[]>([]);

  useEffect(() => {
    const load = () => {
      fetchSignals(30).then(setSignals);
      fetchEvents(20).then(setEvents);
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const totalCost = TIER_STATS.reduce(
    (sum, t) => sum + t.tasks * parseFloat(t.cost.replace("$", "").replace("/task", "")),
    0
  );
  const naiveCost = TIER_STATS.reduce((sum, t) => sum + t.tasks * 2.1, 0);
  const savings = ((1 - totalCost / naiveCost) * 100).toFixed(0);

  return (
    <div className="tab-content">
      <div className="routing-summary-row">
        <div className="routing-summary-card">
          <div className="routing-summary-value" style={{ color: "#22d3ee" }}>${totalCost.toFixed(0)}</div>
          <div className="routing-summary-label">Total Cost</div>
        </div>
        <div className="routing-summary-card">
          <div className="routing-summary-value" style={{ color: "#10b981" }}>{savings}%</div>
          <div className="routing-summary-label">Cost Savings</div>
        </div>
        <div className="routing-summary-card">
          <div className="routing-summary-value" style={{ color: "#a78bfa" }}>{TIER_STATS.reduce((s, t) => s + t.tasks, 0)}</div>
          <div className="routing-summary-label">Total Tasks</div>
        </div>
      </div>

      <div className="tab-section">
        <div className="panel-header">
          <h3>Tier Distribution</h3>
          <span className="panel-badge">Intelligent escalation active</span>
        </div>
        <div className="routing-bar" style={{ marginBottom: 24 }}>
          {TIER_STATS.map((tier) => (
            <div
              key={tier.name}
              className="routing-segment"
              style={{ width: `${tier.percent}%`, backgroundColor: tier.color }}
            >
              {tier.percent}%
            </div>
          ))}
        </div>

        <div className="tier-detail-grid">
          {TIER_STATS.map((tier) => (
            <div key={tier.name} className="tier-detail-card">
              <div className="tier-detail-header">
                <span className="tier-detail-dot" style={{ backgroundColor: tier.color, boxShadow: `0 0 8px ${tier.color}` }} />
                <span className="tier-detail-name">{tier.name}</span>
              </div>
              <div className="tier-detail-stats">
                <div className="tier-stat">
                  <span className="tier-stat-value">{tier.tasks}</span>
                  <span className="tier-stat-label">tasks</span>
                </div>
                <div className="tier-stat">
                  <span className="tier-stat-value">{tier.cost}</span>
                  <span className="tier-stat-label">avg cost</span>
                </div>
                <div className="tier-stat">
                  <span className="tier-stat-value">{tier.avgLatency}</span>
                  <span className="tier-stat-label">latency</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="tab-section">
        <div className="panel-header">
          <h3>Escalation Reasons</h3>
          <span className="panel-badge">{ESCALATION_REASONS.reduce((s, r) => s + r.count, 0)} total</span>
        </div>
        <div className="escalation-list">
          {ESCALATION_REASONS.map((esc, i) => (
            <div key={i} className="escalation-row">
              <div className="escalation-route">
                <span className="escalation-from">{esc.from}</span>
                <span className="escalation-arrow">&rarr;</span>
                <span className="escalation-to">{esc.to}</span>
              </div>
              <span className="escalation-reason">{esc.reason}</span>
              <span className="escalation-count" style={{ color: esc.color }}>{esc.count}x</span>
            </div>
          ))}
        </div>
      </div>

      {(signals.length > 0 || events.length > 0) && (
        <div className="tab-section">
          <div className="panel-header">
            <h3>Live Event Stream</h3>
            <span className="panel-badge">{signals.length + events.length} recent</span>
          </div>
          <div className="event-stream">
            {events.slice(0, 10).map((evt, i) => (
              <div key={i} className="event-row">
                <span className="event-type-badge">{evt.event_type}</span>
                <span className="event-source">{evt.source}</span>
                <span className="event-time">{timeAgo(evt.timestamp)}</span>
              </div>
            ))}
            {signals.slice(0, 10).map((sig, i) => (
              <div key={`s-${i}`} className="event-row">
                <span className="event-type-badge signal-badge">{sig.signal_type}</span>
                <span className="event-source">{sig.source_agent} &rarr; {sig.target_agent}</span>
                <span className="event-time">{timeAgo(sig.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
