import React from 'react';
import { DebateNode } from './DebateGraph';

export interface ExecutiveChairPanelProps {
  selectedNode: DebateNode | null;
  onPromoteNode: (nodeId: string) => void;
  onVetoNode: (nodeId: string) => void;
}

export const ExecutiveChairPanel: React.FC<ExecutiveChairPanelProps> = ({
  selectedNode,
  onPromoteNode,
  onVetoNode,
}) => {
  if (!selectedNode) {
    return (
      <div className="p-4 border border-slate-700 rounded bg-slate-800 text-slate-400 text-sm">
        Select a node from the Debate Graph to exercise Chair promotion controls.
      </div>
    );
  }

  return (
    <div className="p-4 border border-slate-700 rounded bg-slate-800 text-white">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-md font-bold text-blue-400">Executive Chair Control Panel</h4>
        <span className="text-xs text-slate-400">Node ID: {selectedNode.id}</span>
      </div>
      <div className="mb-4">
        <p className="text-sm font-semibold">{selectedNode.topic}</p>
        <p className="text-xs text-slate-300 mt-1">{selectedNode.proposal}</p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onPromoteNode(selectedNode.id)}
          className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
        >
          [Promote Plan Branch]
        </button>
        <button
          onClick={() => onVetoNode(selectedNode.id)}
          className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
        >
          [Veto Proposal]
        </button>
      </div>
    </div>
  );
};
