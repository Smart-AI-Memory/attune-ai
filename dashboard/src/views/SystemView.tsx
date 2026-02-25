import { useEffect, useState } from "react";
import { fetchHealth, fetchEvents, fetchServiceHealth } from "../api";
import type { HealthData, DashboardEvent, ServiceHealth } from "../api";

const STATUS_COLORS: Record<string, string> = {
  HEALTHY: "#10b981",
  WARNING: "#f59e0b",
  DOWN: "#ef4444",
};

interface ConfigItem {
  key: string;
  value: string;
  category: string;
}

const CONFIG: ConfigItem[] = [
  { key: "Escalation threshold", value: "0.7", category: "Routing" },
  { key: "Max tier", value: "premium", category: "Routing" },
  { key: "Default tier", value: "cheap", category: "Routing" },
  { key: "Heartbeat interval", value: "5s", category: "Agents" },
  { key: "Heartbeat timeout", value: "30s", category: "Agents" },
  { key: "Max concurrent agents", value: "4", category: "Agents" },
  { key: "Redis host", value: "localhost:6379", category: "Infrastructure" },
  { key: "Event retention", value: "24h", category: "Infrastructure" },
  { key: "Cache TTL", value: "3600s", category: "Infrastructure" },
];

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return `${Math.floor(diff / 3600000)}h ago`;
}

export default function SystemView() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [services, setServices] = useState<ServiceHealth[]>([]);

  useEffect(() => {
    const load = () => {
      fetchHealth().then(setHealth);
      fetchEvents(15).then(setEvents);
      fetchServiceHealth().then(setServices);
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const healthyCount = services.filter((s) => s.status === "HEALTHY").length;
  const warningCount = services.filter((s) => s.status === "WARNING").length;
  const downCount = services.filter((s) => s.status === "DOWN").length;

  return (
    <div className="tab-content">
      <div className="system-summary-row">
        <div className="system-summary-card">
          <div className="system-summary-icon" style={{ color: "#10b981" }}>
            {health?.status === "healthy" ? "\u2713" : health?.status === "degraded" ? "!" : "\u2717"}
          </div>
          <div>
            <div className="system-summary-value" style={{
              color: health?.status === "healthy" ? "#10b981" : health?.status === "degraded" ? "#f59e0b" : "#ef4444"
            }}>
              {health?.status?.toUpperCase() || "CHECKING..."}
            </div>
            <div className="system-summary-label">System Status</div>
          </div>
        </div>
        <div className="system-summary-card">
          <div className="system-summary-icon" style={{ color: health?.redis_available ? "#10b981" : "#ef4444" }}>
            {health?.redis_available ? "\u2713" : "\u2717"}
          </div>
          <div>
            <div className="system-summary-value" style={{ color: health?.redis_available ? "#10b981" : "#ef4444" }}>
              {health?.redis_available ? "CONNECTED" : "DISCONNECTED"}
            </div>
            <div className="system-summary-label">Redis</div>
          </div>
        </div>
        <div className="system-summary-card summary-stats">
          <div className="summary-stat-item">
            <span style={{ color: "#10b981" }}>{healthyCount}</span> healthy
          </div>
          <div className="summary-stat-item">
            <span style={{ color: "#f59e0b" }}>{warningCount}</span> warning
          </div>
          <div className="summary-stat-item">
            <span style={{ color: "#ef4444" }}>{downCount}</span> down
          </div>
        </div>
      </div>

      <div className="tab-section">
        <div className="panel-header">
          <h3>Service Health</h3>
          <span className="panel-badge">
            {services.length > 0 ? `${services.length} services` : "loading..."}
          </span>
        </div>
        <div className="service-grid">
          {services.map((svc) => {
            const color = STATUS_COLORS[svc.status] ?? "#6b7280";
            return (
              <div key={svc.name} className="service-card">
                <div className="service-card-header">
                  <span className="service-dot" style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }} />
                  <span className="service-name">{svc.name}</span>
                  <span className="service-status" style={{ color }}>{svc.status}</span>
                </div>
                <div className="service-desc">{svc.description}</div>
                <div className="service-meta">
                  {svc.latency_ms != null && (
                    <span>Latency: <strong>{svc.latency_ms}ms</strong></span>
                  )}
                  {svc.buffer_size != null && (
                    <span>Buffer: <strong>{svc.buffer_size}</strong></span>
                  )}
                </div>
              </div>
            );
          })}
          {services.length === 0 && (
            <div className="empty-state">
              Loading service health — start the dashboard API to see live data
            </div>
          )}
        </div>
      </div>

      <div className="panels-row">
        <div className="tab-section">
          <div className="panel-header">
            <h3>Configuration</h3>
            <span className="panel-badge">Runtime</span>
          </div>
          <div className="config-list">
            {CONFIG.map((item) => (
              <div key={item.key} className="config-row">
                <span className="config-category">{item.category}</span>
                <span className="config-key">{item.key}</span>
                <span className="config-value">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="tab-section">
          <div className="panel-header">
            <h3>Recent Events</h3>
            <span className="panel-badge">{events.length} events</span>
          </div>
          <div className="event-stream">
            {events.length > 0 ? events.map((evt, i) => (
              <div key={i} className="event-row">
                <span className="event-type-badge">{evt.event_type}</span>
                <span className="event-source">{evt.source}</span>
                <span className="event-time">{timeAgo(evt.timestamp)}</span>
              </div>
            )) : (
              <div className="empty-state">No events — start the dashboard API to see live data</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
