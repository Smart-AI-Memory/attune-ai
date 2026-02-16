/**
 * Telemetry Panel - Main VSCode Webview Component
 *
 * Displays LLM usage telemetry in a webview tab within the main editor area.
 *
 * **Features:**
 * - Overview stats (total cost, calls, success rate)
 * - Activity feed (recent LLM calls with filtering)
 * - Cost charts (line, pie, bar)
 * - Top expensive workflows list
 * - Export to CSV
 * - Auto-refresh (60-second polling)
 *
 * **Access:**
 * - Status bar button: 📊 Telemetry
 * - Command palette: "Empathy: Open Telemetry Dashboard"
 *
 * **Implementation Status:** Sprint 1 (Week 1) - Foundation
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';

interface TelemetryPanelProps {
  /** Initial data load (optional) */
  initialData?: TelemetryData;
}

interface TelemetryData {
  totalCost: number;
  totalCalls: number;
  successRate: number;
  recentCalls: LLMCall[];
  workflows: WorkflowSummary[];
}

interface LLMCall {
  callId: string;
  timestamp: string;
  workflowName: string | null;
  provider: string;
  tier: string;
  modelId: string;
  inputTokens: number;
  outputTokens: number;
  estimatedCost: number;
  latencyMs: number;
  success: boolean;
  errorType?: string;
}

interface WorkflowSummary {
  workflowName: string;
  totalCost: number;
  runCount: number;
  avgCost: number;
}

export default function TelemetryPanel({ initialData }: TelemetryPanelProps) {
  // TODO: Sprint 1 implementation
  // - Load telemetry data from JSONL files
  // - Display overview stats
  // - Render activity feed
  // - Auto-refresh every 60 seconds

  return (
    <div className="telemetry-panel p-6 bg-gradient-to-br from-gray-50 to-blue-50 min-h-screen">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          📊 LLM Telemetry Dashboard
        </h1>
        <p className="text-gray-600">
          Real-time monitoring of LLM usage, costs, and performance
        </p>
      </header>

      {/* Overview Stats Section */}
      <section className="overview-stats mb-8">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="Total Cost"
            value={initialData?.totalCost ? `$${initialData.totalCost.toFixed(2)}` : '$0.00'}
            subtitle="All-time LLM spend"
            icon="💰"
          />
          <StatCard
            title="Total Calls"
            value={initialData?.totalCalls.toLocaleString() || '0'}
            subtitle="LLM API calls"
            icon="📞"
          />
          <StatCard
            title="Success Rate"
            value={initialData?.successRate ? `${(initialData.successRate * 100).toFixed(1)}%` : '0%'}
            subtitle="Call success rate"
            icon="✅"
          />
        </div>
      </section>

      {/* Activity Feed Section */}
      <section className="activity-feed mb-8">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Recent Activity</h2>
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-gray-500 text-sm">
            Activity feed will display recent LLM calls with filtering options.
          </p>
          <p className="text-gray-400 text-xs mt-2">
            Implementation: Sprint 1, Task 1.6
          </p>
        </div>
      </section>

      {/* Top Workflows Section */}
      <section className="top-workflows">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Top Expensive Workflows</h2>
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-gray-500 text-sm">
            List of workflows sorted by total cost.
          </p>
          <p className="text-gray-400 text-xs mt-2">
            Implementation: Sprint 2
          </p>
        </div>
      </section>
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
}

function StatCard({ title, value, subtitle, icon }: StatCardProps) {
  return (
    <div className="stat-card bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>
      <p className="text-3xl font-bold text-gray-800 mb-1">{value}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  );
}
