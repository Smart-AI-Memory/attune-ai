interface HeaderProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  agentCount: number;
}

const TABS = ["Overview", "Agents", "Wizards", "Routing", "System"];

export default function Header({ activeTab, onTabChange, agentCount }: HeaderProps) {
  const now = new Date();
  const time = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZoneName: "short",
  });

  return (
    <header className="header">
      <div className="header-brand">
        <div className="brand-icon">A</div>
        <div>
          <span className="brand-name">
            attune<span className="brand-accent">-ai</span>
          </span>
          <span className="brand-version">v3.5.0 &middot; INTELLIGENT FRAMEWORK</span>
        </div>
      </div>

      <nav className="header-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`tab ${activeTab === tab ? "tab-active" : ""}`}
            onClick={() => onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <div className="header-meta">
        <div className="agent-badge">
          <span className="agent-dot" />
          <span className="agent-count">{agentCount}</span>
          <span className="agent-label">agents</span>
        </div>
        <div className="header-time">{time}</div>
      </div>
    </header>
  );
}
