import { useEffect, useState } from "react";
import { fetchServiceHealth } from "../api";
import type { ServiceHealth } from "../api";

function statusClass(status: string): string {
  return `status-${status.toLowerCase()}`;
}

export default function SystemHealth() {
  const [services, setServices] = useState<ServiceHealth[]>([]);

  useEffect(() => {
    const load = () => fetchServiceHealth().then(setServices);
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="panel">
      <h3>System Health</h3>
      <div className="health-list">
        {services.map((svc) => (
          <div key={svc.name} className="health-row">
            <div className="health-left">
              <span className={`health-dot ${statusClass(svc.status)}`} />
              <span className="health-name">{svc.name}</span>
            </div>
            <div className="health-right">
              <span className="health-latency">
                {svc.latency_ms != null ? `${svc.latency_ms}ms` : "—"}
              </span>
              <span className={`health-status ${statusClass(svc.status)}`}>
                {svc.status}
              </span>
            </div>
          </div>
        ))}
        {services.length === 0 && (
          <div className="health-row health-loading">Loading…</div>
        )}
      </div>
    </div>
  );
}
