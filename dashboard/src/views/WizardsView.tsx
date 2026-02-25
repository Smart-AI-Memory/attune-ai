import { useEffect, useState } from "react";
import { fetchQualityMetrics, fetchUnderperforming } from "../api";
import type { QualityMetrics } from "../api";

interface WizardInfo {
  id: string;
  name: string;
  description: string;
  runs: number;
  avgQuality: number;
  color: string;
  stages: string[];
}

const WIZARDS: WizardInfo[] = [
  { id: "code-review", name: "Code Review", description: "Multi-pass code review with security, quality, and performance analysis", runs: 342, avgQuality: 0.89, color: "#22d3ee", stages: ["analysis", "generation", "validation"] },
  { id: "test-generation", name: "Test Generation", description: "Generate comprehensive test suites from source code analysis", runs: 287, avgQuality: 0.84, color: "#10b981", stages: ["analysis", "generation", "validation"] },
  { id: "debug-assistant", name: "Debug Assistant", description: "Autonomous error scanning and root cause analysis", runs: 198, avgQuality: 0.91, color: "#6366f1", stages: ["analysis", "generation", "validation"] },
  { id: "refactoring", name: "Refactoring", description: "Intelligent code restructuring with preservation guarantees", runs: 156, avgQuality: 0.82, color: "#f59e0b", stages: ["analysis", "generation", "validation"] },
  { id: "documentation", name: "Documentation", description: "Auto-generate docs, READMEs, and changelogs from code", runs: 134, avgQuality: 0.87, color: "#ef4444", stages: ["analysis", "generation", "validation"] },
];

function QualityBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="quality-bar-wrap">
      <div
        className="quality-bar-fill"
        style={{ width: `${value * 100}%`, backgroundColor: color }}
      />
      <span className="quality-bar-label">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

export default function WizardsView() {
  const [metrics, setMetrics] = useState<QualityMetrics[]>([]);
  const [underperforming, setUnderperforming] = useState<QualityMetrics[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchQualityMetrics().then(setMetrics);
    fetchUnderperforming().then(setUnderperforming);
    const id = setInterval(() => {
      fetchQualityMetrics().then(setMetrics);
      fetchUnderperforming().then(setUnderperforming);
    }, 10000);
    return () => clearInterval(id);
  }, []);

  const getWizardMetrics = (wizardId: string) =>
    metrics.filter((m) => m.workflow === wizardId);

  return (
    <div className="tab-content">
      <div className="tab-section">
        <div className="panel-header">
          <h3>Wizard Registry</h3>
          <span className="panel-badge">{WIZARDS.length} available</span>
        </div>
        <div className="wizard-grid">
          {WIZARDS.map((wiz) => {
            const wizMetrics = getWizardMetrics(wiz.id);
            const isExpanded = expanded === wiz.id;
            return (
              <div
                key={wiz.id}
                className={`wizard-card ${isExpanded ? "wizard-card-expanded" : ""}`}
                onClick={() => setExpanded(isExpanded ? null : wiz.id)}
              >
                <div className="wizard-card-header">
                  <div className="wizard-card-dot" style={{ backgroundColor: wiz.color, boxShadow: `0 0 10px ${wiz.color}` }} />
                  <div className="wizard-card-title">
                    <span className="wizard-card-name">{wiz.name}</span>
                    <span className="wizard-card-runs">{wiz.runs} runs</span>
                  </div>
                  <QualityBar value={wiz.avgQuality} color={wiz.color} />
                </div>
                <div className="wizard-card-desc">{wiz.description}</div>

                {isExpanded && (
                  <div className="wizard-card-detail">
                    <div className="wizard-stages-header">Stage Breakdown</div>
                    {wiz.stages.map((stage) => {
                      const stageMetrics = wizMetrics.filter((m) => m.stage === stage);
                      return (
                        <div key={stage} className="wizard-stage-row">
                          <span className="wizard-stage-name">{stage}</span>
                          <div className="wizard-stage-tiers">
                            {["cheap", "capable", "premium"].map((tier) => {
                              const m = stageMetrics.find((m) => m.tier === tier);
                              return (
                                <span key={tier} className="wizard-tier-chip">
                                  {tier}: {m ? `${(m.avg_quality * 100).toFixed(0)}%` : "—"}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {underperforming.length > 0 && (
        <div className="tab-section">
          <div className="panel-header">
            <h3>Underperforming Stages</h3>
            <span className="panel-badge warning-badge">Below 70% threshold</span>
          </div>
          <div className="underperforming-list">
            {underperforming.map((m, i) => (
              <div key={i} className="underperforming-row">
                <span className="underperforming-workflow">{m.workflow}</span>
                <span className="underperforming-stage">{m.stage}</span>
                <span className="underperforming-tier">{m.tier}</span>
                <span className="underperforming-score" style={{ color: m.avg_quality < 0.5 ? "#ef4444" : "#f59e0b" }}>
                  {(m.avg_quality * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
