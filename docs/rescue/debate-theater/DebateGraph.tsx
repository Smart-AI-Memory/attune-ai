import React, { useEffect, useState } from 'react';

export interface DebateNode {
  id: string;
  agent: 'claude' | 'antigravity' | 'codex';
  topic: string;
  proposal: string;
  relation: 'supports' | 'challenges' | 'refines';
  parentNodeId?: string;
}

export interface DebateGraphProps {
  nodes: DebateNode[];
  onSelectNode: (node: DebateNode) => void;
}

export const DebateGraph: React.FC<DebateGraphProps> = ({ nodes, onSelectNode }) => {
  const getAgentColor = (agent: string) => {
    switch (agent) {
      case 'claude': return '#3b82f6'; // Blue
      case 'antigravity': return '#10b981'; // Green
      case 'codex': return '#8b5cf6'; // Purple
      default: return '#6b7280';
    }
  };

  return (
    <div className="debate-graph-container border rounded-lg p-4 bg-slate-900 text-white min-h-[400px]">
      <h3 className="text-lg font-semibold mb-4 border-b border-slate-700 pb-2">
        Visual Debate Theater — Real-Time Multi-Agent Graph
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {nodes.map((node) => (
          <div
            key={node.id}
            onClick={() => onSelectNode(node)}
            className="cursor-pointer p-4 rounded border border-slate-700 bg-slate-800 hover:border-blue-500 transition-all"
            style={{ borderLeftWidth: '4px', borderLeftColor: getAgentColor(node.agent) }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase font-bold tracking-wider" style={{ color: getAgentColor(node.agent) }}>
                {node.agent}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
                {node.relation}
              </span>
            </div>
            <h4 className="font-medium text-sm mb-1">{node.topic}</h4>
            <p className="text-xs text-slate-400 line-clamp-2">{node.proposal}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
