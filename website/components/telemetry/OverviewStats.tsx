/**
 * Overview Stats Component
 *
 * Displays high-level telemetry metrics in a card grid.
 *
 * **Metrics:**
 * - Total Cost (all-time LLM spend)
 * - Total Calls (API call count)
 * - Success Rate (percentage of successful calls)
 * - Avg Latency (average response time)
 * - Total Tokens (input + output tokens)
 * - Total Workflows (workflow run count)
 *
 * **Implementation Status:** Sprint 1 (Week 1)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';

interface OverviewStatsProps {
  /** Total cost in USD */
  totalCost: number;
  /** Total API calls */
  totalCalls: number;
  /** Success rate (0-1) */
  successRate: number;
  /** Average latency in milliseconds */
  avgLatencyMs: number;
  /** Total tokens (input + output) */
  totalTokens: number;
  /** Total workflow runs */
  totalWorkflows: number;
}

export default function OverviewStats({
  totalCost,
  totalCalls,
  successRate,
  avgLatencyMs,
  totalTokens,
  totalWorkflows,
}: OverviewStatsProps) {
  return (
    <div className="overview-stats">
      <h2 className="text-xl font-semibold text-gray-700 mb-4">Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          title="Total Cost"
          value={`$${totalCost.toFixed(2)}`}
          subtitle="All-time LLM spend"
          icon="💰"
          trend={null}
        />
        <StatCard
          title="Total Calls"
          value={totalCalls.toLocaleString()}
          subtitle="API calls"
          icon="📞"
          trend={null}
        />
        <StatCard
          title="Success Rate"
          value={`${(successRate * 100).toFixed(1)}%`}
          subtitle="Call success rate"
          icon="✅"
          trend={successRate >= 0.95 ? 'good' : successRate >= 0.8 ? 'warning' : 'bad'}
        />
        <StatCard
          title="Avg Latency"
          value={`${avgLatencyMs.toFixed(0)}ms`}
          subtitle="Response time"
          icon="⚡"
          trend={avgLatencyMs <= 1000 ? 'good' : avgLatencyMs <= 3000 ? 'warning' : 'bad'}
        />
        <StatCard
          title="Total Tokens"
          value={formatLargeNumber(totalTokens)}
          subtitle="Input + output"
          icon="🔢"
          trend={null}
        />
        <StatCard
          title="Workflows"
          value={totalWorkflows.toLocaleString()}
          subtitle="Total runs"
          icon="🔄"
          trend={null}
        />
      </div>
    </div>
  );
}

/**
 * Stat Card Component
 */
interface StatCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: string;
  trend: 'good' | 'warning' | 'bad' | null;
}

function StatCard({ title, value, subtitle, icon, trend }: StatCardProps) {
  const trendColors = {
    good: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    bad: 'bg-red-50 border-red-200',
    null: 'bg-white border-gray-200',
  };

  const trendClass = trend ? trendColors[trend] : trendColors.null;

  return (
    <div
      className={`stat-card rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow border-2 ${trendClass}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>
      <p className="text-3xl font-bold text-gray-800 mb-1">{value}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  );
}

/**
 * Format large numbers with K/M/B suffixes
 */
function formatLargeNumber(num: number): string {
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toLocaleString();
}
