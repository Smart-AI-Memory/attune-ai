interface WizardStat {
  name: string;
  count: number;
  color: string;
  trend: number[];
}

const WIZARDS: WizardStat[] = [
  { name: "Code Review", count: 342, color: "#22d3ee", trend: [20, 35, 28, 42, 38, 50, 45] },
  { name: "Debug Assistant", count: 287, color: "#10b981", trend: [15, 22, 30, 25, 35, 32, 40] },
  { name: "Architecture", count: 198, color: "#6366f1", trend: [10, 18, 15, 22, 20, 28, 25] },
  { name: "Team Collaboration", count: 156, color: "#f59e0b", trend: [8, 12, 15, 10, 18, 20, 22] },
  { name: "Documentation", count: 134, color: "#ef4444", trend: [5, 10, 8, 12, 15, 10, 18] },
];

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const h = 20;
  const w = 50;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export default function WizardUsage() {
  const maxCount = Math.max(...WIZARDS.map((w) => w.count));

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Wizard Usage</h3>
        <span className="panel-badge">{WIZARDS.length} available</span>
      </div>
      <div className="wizard-list">
        {WIZARDS.map((wiz) => (
          <div key={wiz.name} className="wizard-row">
            <span className="wizard-name">{wiz.name}</span>
            <div className="wizard-bar-wrap">
              <div
                className="wizard-bar"
                style={{
                  width: `${(wiz.count / maxCount) * 100}%`,
                  backgroundColor: wiz.color,
                }}
              />
            </div>
            <MiniSparkline data={wiz.trend} color={wiz.color} />
            <span className="wizard-count">{wiz.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
