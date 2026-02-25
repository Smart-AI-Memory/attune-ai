interface Level {
  number: number;
  label: string;
  isCurrent: boolean;
}

const LEVELS: Level[] = [
  { number: 5, label: "Autonomous", isCurrent: false },
  { number: 4, label: "Predictive", isCurrent: false },
  { number: 3, label: "Collaborative", isCurrent: true },
  { number: 2, label: "Guided", isCurrent: false },
  { number: 1, label: "Reactive", isCurrent: false },
];

export default function MaturityLevel() {
  return (
    <div className="panel">
      <h3>AI Maturity Level</h3>
      <div className="maturity-list">
        {LEVELS.map((level) => (
          <div
            key={level.number}
            className={`maturity-row ${level.isCurrent ? "maturity-current" : ""}`}
          >
            <span
              className={`maturity-badge ${level.isCurrent ? "maturity-badge-active" : ""}`}
            >
              {level.number}
            </span>
            <span className="maturity-label">{level.label}</span>
            {level.isCurrent && (
              <span className="maturity-tag">CURRENT</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
