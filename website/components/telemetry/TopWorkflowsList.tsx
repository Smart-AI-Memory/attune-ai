/**
 * Top Workflows List - Most expensive workflows
 *
 * Displays workflows sorted by cost with:
 * - Workflow name and total cost
 * - Run count and average cost
 * - Savings amount and percentage
 * - Click-through to filter by workflow
 *
 * **Implementation:** Sprint 2 (Week 2)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';

interface TopWorkflowsListProps {
  /** Top workflows by cost */
  workflows: WorkflowSummary[];
  /** Maximum workflows to display */
  limit?: number;
  /** Callback when workflow is clicked */
  onWorkflowClick?: (workflowName: string) => void;
}

interface WorkflowSummary {
  workflowName: string;
  totalCost: number;
  runCount: number;
  avgCost: number;
  totalSavings: number;
}

export default function TopWorkflowsList({
  workflows,
  limit = 10,
  onWorkflowClick,
}: TopWorkflowsListProps) {
  const displayedWorkflows = workflows.slice(0, limit);

  if (workflows.length === 0) {
    return (
      <div className="top-workflows-list">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">
          Top Expensive Workflows
        </h3>
        <p className="text-gray-500 text-sm">
          No workflow data available yet
        </p>
      </div>
    );
  }

  return (
    <div className="top-workflows-list">
      <h3 className="text-lg font-semibold text-gray-700 mb-4">
        Top Expensive Workflows
      </h3>
      <div className="space-y-2">
        {displayedWorkflows.map((workflow, index) => (
          <WorkflowCard
            key={workflow.workflowName}
            workflow={workflow}
            rank={index + 1}
            onClick={
              onWorkflowClick
                ? () => onWorkflowClick(workflow.workflowName)
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Workflow Card Component
 */
interface WorkflowCardProps {
  workflow: WorkflowSummary;
  rank: number;
  onClick?: () => void;
}

function WorkflowCard({ workflow, rank, onClick }: WorkflowCardProps) {
  const savingsPercent =
    workflow.totalCost > 0
      ? (workflow.totalSavings / (workflow.totalCost + workflow.totalSavings)) *
        100
      : 0;

  return (
    <div
      className={`workflow-card bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-3">
          <div
            className={`rank-badge w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              rank === 1
                ? 'bg-yellow-100 text-yellow-800'
                : rank === 2
                ? 'bg-gray-100 text-gray-700'
                : rank === 3
                ? 'bg-orange-100 text-orange-700'
                : 'bg-blue-50 text-blue-700'
            }`}
          >
            {rank}
          </div>
          <div>
            <h4 className="text-base font-semibold text-gray-800">
              {workflow.workflowName}
            </h4>
            <p className="text-xs text-gray-500">
              {workflow.runCount} run{workflow.runCount !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900">
            ${workflow.totalCost.toFixed(2)}
          </p>
          <p className="text-xs text-gray-500">
            ${workflow.avgCost.toFixed(4)} avg
          </p>
        </div>
      </div>

      {workflow.totalSavings > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <div className="flex items-center justify-between text-xs">
            <span className="text-green-600 font-medium">
              💰 ${workflow.totalSavings.toFixed(2)} saved
            </span>
            <span className="text-gray-500">
              {savingsPercent.toFixed(1)}% savings
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
