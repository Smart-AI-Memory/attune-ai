/**
 * JSONL Telemetry Parser
 *
 * Parses telemetry data from `.attune/*.jsonl` files.
 *
 * **Files:**
 * - `.attune/llm_calls.jsonl` - LLM API call records
 * - `.attune/workflow_runs.jsonl` - Workflow run records
 *
 * **Features:**
 * - Read and parse JSONL files line-by-line
 * - Filter records by date range, workflow name, provider
 * - Calculate aggregated metrics
 * - Handle malformed JSON gracefully
 * - Support streaming large files
 *
 * **Implementation Status:** Sprint 1 (Week 1)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Fair Source License 0.9
 */

import fs from 'fs';
import path from 'path';
import type {
  LLMCallRecord,
  WorkflowRunRecord,
  TelemetryStats,
  WorkflowSummary,
  ProviderStats,
  TierStats,
} from '@/components/telemetry/hooks/useTelemetryData';

export interface ParseOptions {
  /** Filter by date (only records after this date) */
  since?: Date;
  /** Filter by workflow name */
  workflowName?: string;
  /** Filter by provider */
  provider?: string;
  /** Maximum records to return */
  limit?: number;
}

/**
 * Parse LLM call records from JSONL file
 *
 * @param filePath Path to llm_calls.jsonl file
 * @param options Parse options
 * @returns Array of LLM call records
 */
export function parseLLMCalls(
  filePath: string,
  options: ParseOptions = {}
): LLMCallRecord[] {
  const { since, workflowName, provider, limit = 1000 } = options;

  if (!fs.existsSync(filePath)) {
    return [];
  }

  const records: LLMCallRecord[] = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  for (const line of lines) {
    if (!line.trim()) continue;

    try {
      const record = JSON.parse(line) as LLMCallRecord;

      // Apply filters
      if (since && new Date(record.timestamp) < since) {
        continue;
      }

      if (workflowName && record.workflowName !== workflowName) {
        continue;
      }

      if (provider && record.provider !== provider) {
        continue;
      }

      records.push(record);

      if (records.length >= limit) {
        break;
      }
    } catch (error) {
      // Skip malformed JSON lines
      console.warn(`Failed to parse LLM call record: ${error}`);
      continue;
    }
  }

  return records;
}

/**
 * Parse workflow run records from JSONL file
 *
 * @param filePath Path to workflow_runs.jsonl file
 * @param options Parse options
 * @returns Array of workflow run records
 */
export function parseWorkflowRuns(
  filePath: string,
  options: ParseOptions = {}
): WorkflowRunRecord[] {
  const { since, workflowName, limit = 100 } = options;

  if (!fs.existsSync(filePath)) {
    return [];
  }

  const records: WorkflowRunRecord[] = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  for (const line of lines) {
    if (!line.trim()) continue;

    try {
      const record = JSON.parse(line) as WorkflowRunRecord;

      // Apply filters
      if (since && new Date(record.startedAt) < since) {
        continue;
      }

      if (workflowName && record.workflowName !== workflowName) {
        continue;
      }

      records.push(record);

      if (records.length >= limit) {
        break;
      }
    } catch (error) {
      // Skip malformed JSON lines
      console.warn(`Failed to parse workflow run record: ${error}`);
      continue;
    }
  }

  return records;
}

/**
 * Load telemetry data from .attune directory
 *
 * @param empathyDir Path to .attune directory (default: ./.attune)
 * @param options Parse options
 * @returns Complete telemetry statistics
 */
export function loadTelemetryData(
  empathyDir: string = '.attune',
  options: ParseOptions = {}
): TelemetryStats {
  const callsFile = path.join(empathyDir, 'llm_calls.jsonl');
  const workflowsFile = path.join(empathyDir, 'workflow_runs.jsonl');

  // Parse files
  const calls = parseLLMCalls(callsFile, options);
  const workflows = parseWorkflowRuns(workflowsFile, options);

  // Calculate aggregated metrics
  const stats = calculateStats(calls, workflows);

  return stats;
}

/**
 * Calculate aggregated statistics from telemetry records
 */
function calculateStats(
  calls: LLMCallRecord[],
  workflows: WorkflowRunRecord[]
): TelemetryStats {
  // Total cost
  const totalCost = calls.reduce((sum, c) => sum + c.estimatedCost, 0);

  // Success rate
  const successfulCalls = calls.filter((c) => c.success).length;
  const successRate = calls.length > 0 ? successfulCalls / calls.length : 0;

  // Average latency
  const totalLatency = calls.reduce((sum, c) => sum + c.latencyMs, 0);
  const avgLatencyMs = calls.length > 0 ? totalLatency / calls.length : 0;

  // Total tokens
  const totalTokens = calls.reduce(
    (sum, c) => sum + c.inputTokens + c.outputTokens,
    0
  );

  // Top workflows by cost
  const workflowMap = new Map<string, WorkflowSummary>();
  for (const wf of workflows) {
    const existing = workflowMap.get(wf.workflowName) || {
      workflowName: wf.workflowName,
      totalCost: 0,
      runCount: 0,
      avgCost: 0,
      totalSavings: 0,
    };

    existing.totalCost += wf.totalCost;
    existing.runCount += 1;
    existing.totalSavings += wf.savings;

    workflowMap.set(wf.workflowName, existing);
  }

  const topWorkflows = Array.from(workflowMap.values())
    .map((w) => ({
      ...w,
      avgCost: w.runCount > 0 ? w.totalCost / w.runCount : 0,
    }))
    .sort((a, b) => b.totalCost - a.totalCost)
    .slice(0, 10);

  // Provider breakdown
  const providerMap = new Map<string, ProviderStats>();
  for (const call of calls) {
    const existing = providerMap.get(call.provider) || {
      provider: call.provider,
      callCount: 0,
      totalCost: 0,
      avgCost: 0,
      errorCount: 0,
      successRate: 0,
    };

    existing.callCount += 1;
    existing.totalCost += call.estimatedCost;
    if (!call.success) {
      existing.errorCount += 1;
    }

    providerMap.set(call.provider, existing);
  }

  const providerBreakdown = Array.from(providerMap.values()).map((p) => ({
    ...p,
    avgCost: p.callCount > 0 ? p.totalCost / p.callCount : 0,
    successRate:
      p.callCount > 0 ? (p.callCount - p.errorCount) / p.callCount : 0,
  }));

  // Tier breakdown
  const tierMap = new Map<string, { count: number; cost: number }>();
  for (const call of calls) {
    const existing = tierMap.get(call.tier) || { count: 0, cost: 0 };
    existing.count += 1;
    existing.cost += call.estimatedCost;
    tierMap.set(call.tier, existing);
  }

  const totalCalls = calls.length;
  const tierBreakdown: TierStats[] = Array.from(tierMap.entries()).map(
    ([tier, stats]) => ({
      tier,
      count: stats.count,
      cost: stats.cost,
      percent: totalCalls > 0 ? (stats.count / totalCalls) * 100 : 0,
    })
  );

  // Recent calls (last 100)
  const recentCalls = calls.slice(-100).reverse();

  // Recent workflows (last 50)
  const recentWorkflows = workflows.slice(-50).reverse();

  return {
    totalCost,
    totalCalls: calls.length,
    totalWorkflows: workflows.length,
    successRate,
    avgLatencyMs,
    totalTokens,
    recentCalls,
    recentWorkflows,
    topWorkflows,
    providerBreakdown,
    tierBreakdown,
  };
}

/**
 * Watch telemetry files for changes
 *
 * @param empathyDir Path to .attune directory
 * @param onChange Callback when files change
 * @returns Cleanup function to stop watching
 */
export function watchTelemetryFiles(
  empathyDir: string,
  onChange: (stats: TelemetryStats) => void
): () => void {
  const callsFile = path.join(empathyDir, 'llm_calls.jsonl');
  const workflowsFile = path.join(empathyDir, 'workflow_runs.jsonl');

  const watchers: fs.FSWatcher[] = [];

  const handleChange = () => {
    const stats = loadTelemetryData(empathyDir);
    onChange(stats);
  };

  // Watch both files
  if (fs.existsSync(callsFile)) {
    const watcher = fs.watch(callsFile, handleChange);
    watchers.push(watcher);
  }

  if (fs.existsSync(workflowsFile)) {
    const watcher = fs.watch(workflowsFile, handleChange);
    watchers.push(watcher);
  }

  // Return cleanup function
  return () => {
    watchers.forEach((w) => w.close());
  };
}
