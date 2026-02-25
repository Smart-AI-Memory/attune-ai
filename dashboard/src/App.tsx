import { useEffect, useState } from "react";
import Header from "./components/Header";
import StatCard from "./components/StatCard";
import ModelRouting from "./components/ModelRouting";
import SystemHealth from "./components/SystemHealth";
import WizardUsage from "./components/WizardUsage";
import MaturityLevel from "./components/MaturityLevel";
import AgentsView from "./views/AgentsView";
import WizardsView from "./views/WizardsView";
import RoutingView from "./views/RoutingView";
import SystemView from "./views/SystemView";
import { fetchHealth } from "./api";

function OverviewTab({ agentCount }: { agentCount: number }) {
  return (
    <>
      <div className="stats-row">
        <StatCard
          label="COST SAVINGS"
          value="81%"
          subtitle="vs. direct API calls"
          color="#22d3ee"
          trend={[40, 55, 60, 65, 70, 75, 78, 81]}
        />
        <StatCard
          label="TASKS COMPLETED"
          value="1247"
          subtitle="this month"
          color="#a78bfa"
          trend={[200, 400, 600, 750, 900, 1050, 1150, 1247]}
        />
        <StatCard
          label="AVG ITERATIONS"
          value="1.7"
          subtitle="83% fewer than manual"
          color="#c084fc"
          trend={[3.2, 2.8, 2.5, 2.2, 2.0, 1.9, 1.8, 1.7]}
        />
        <StatCard
          label="ACTIVE AGENTS"
          value={`${Math.min(agentCount, 4)}/4`}
          subtitle={`${Math.max(4 - agentCount, 0)} queued \u00b7 0 failed`}
          color="#fb923c"
          trend={[1, 2, 2, 3, 2, 4, 3, agentCount]}
        />
      </div>

      <div className="panels-row">
        <ModelRouting />
        <SystemHealth />
      </div>

      <div className="panels-row">
        <WizardUsage />
        <div className="panels-col">
          <MaturityLevel />
        </div>
      </div>
    </>
  );
}

function renderTab(tab: string, agentCount: number) {
  switch (tab) {
    case "Agents": return <AgentsView />;
    case "Wizards": return <WizardsView />;
    case "Routing": return <RoutingView />;
    case "System": return <SystemView />;
    default: return <OverviewTab agentCount={agentCount} />;
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [agentCount, setAgentCount] = useState(2);

  useEffect(() => {
    fetchHealth().then((h) => setAgentCount(h.active_agents || 2));
    const id = setInterval(() => {
      fetchHealth().then((h) => setAgentCount(h.active_agents || 2));
    }, 10_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        agentCount={agentCount}
      />
      {renderTab(activeTab, agentCount)}
    </div>
  );
}
