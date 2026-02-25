interface TierInfo {
  name: string;
  percent: number;
  color: string;
  avgCost: string;
}

const TIERS: TierInfo[] = [
  { name: "Haiku 4.5", percent: 62, color: "#10b981", avgCost: "$0.12/task" },
  { name: "Sonnet 4.6", percent: 28, color: "#6366f1", avgCost: "$0.48/task" },
  { name: "Opus 4.6", percent: 10, color: "#8b5cf6", avgCost: "$2.10/task" },
];

export default function ModelRouting() {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Model Routing Distribution</h3>
        <span className="panel-badge">Intelligent escalation active</span>
      </div>
      <div className="routing-bar">
        {TIERS.map((tier) => (
          <div
            key={tier.name}
            className="routing-segment"
            style={{ width: `${tier.percent}%`, backgroundColor: tier.color }}
          >
            {tier.percent}%
          </div>
        ))}
      </div>
      <div className="routing-legend">
        {TIERS.map((tier) => (
          <div key={tier.name} className="routing-item">
            <span className="routing-dot" style={{ backgroundColor: tier.color }} />
            <div>
              <div className="routing-name">{tier.name}</div>
              <div className="routing-cost">Avg cost: {tier.avgCost}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
