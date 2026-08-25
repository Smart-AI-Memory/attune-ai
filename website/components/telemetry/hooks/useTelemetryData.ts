/**
 * Telemetry Data Hook
 *
 * Fetches and manages telemetry data from JSONL files.
 *
 * **Features:**
 * - Load LLM call records from `.attune/llm_calls.jsonl`
 * - Load workflow run records from `.attune/workflow_runs.jsonl`
 *
 * - Auto-refresh every 60 seconds
 * - Filter by date range, workflow name, provider
 * - Calculate aggregated metrics
 *
 * **Implementation Status:** Sprint 1 (Week 1)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import { useCallback, useEffect, useState } from 'react';

export interface LLMCallRecord {
  callId: string;
  timestamp: string;
  workflowName: string | null;
  stepName: string | null;
  userId: string | null;
  sessionId: string | null;
  taskType: string;
  provider: string;
  tier: string;
  modelId: string;
  inputTokens: number;
  outputTokens: number;
  estimatedCost: number;
  actualCost: number | null;
  latencyMs: number;
  fallbackUsed: boolean;
  fallbackChain: string[];
  originalProvider: string | null;
  originalModel: string | null;
  retryCount: number;
  circuitBreakerState: string | null;
  success: boolean;
  errorType: string | null;
  errorMessage: string | null;
  metadata: Record<string, unknown>;
}

export interface WorkflowRunRecord {
  runId: string;
  workflowName: string;
  startedAt: string;
  completedAt: string | null;
  userId: string | null;
  sessionId: string | null;
  stages: WorkflowStageRecord[];
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCost: number;
  baselineCost: number;
  savings: number;
  savingsPercent: number;
  totalDurationMs: number;
  success: boolean;
  error: string | null;
  providersUsed: string[];
  tiersUsed: string[];
}

export interface WorkflowStageRecord {
  stageName: string;
  tier: string;
  modelId: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  latencyMs: number;
  success: boolean;
  skipped: boolean;
  skipReason: string | null;
  error: string | null;
}

export interface TelemetryStats {
  totalCost: number;
  totalCalls: number;
  totalWorkflows: number;
  successRate: number;
  avgLatencyMs: number;
  totalTokens: number;
  recentCalls: LLMCallRecord[];
  recentWorkflows: WorkflowRunRecord[];
  topWorkflows: WorkflowSummary[];
  providerBreakdown: ProviderStats[];
  tierBreakdown: TierStats[];
}

export interface WorkflowSummary {
  workflowName: string;
  totalCost: number;
  runCount: number;
  avgCost: number;
  totalSavings: number;
}

export interface ProviderStats {
  provider: string;
  callCount: number;
  totalCost: number;
  avgCost: number;
  errorCount: number;
  successRate: number;
}

export interface TierStats {
  tier: string;
  count: number;
  cost: number;
  percent: number;
}

interface UseTelemetryDataOptions {
  /** Auto-refresh interval in milliseconds (default: 60000 = 60s) */
  refreshInterval?: number;
  /** Maximum number of recent calls to fetch (default: 100) */
  limit?: number;
  /** Filter by workflow name */
  workflowName?: string | null;
  /** Filter by date range */
  since?: Date | null;
}

interface UseTelemetryDataResult {
  data: TelemetryStats | null;
  loading: boolean;
  error: Error | null;
  refresh: () => void;
}

/**
 * Hook to fetch and manage telemetry data
 *
 * @param options Configuration options
 * @returns Telemetry data, loading state, error state, and refresh function
 *
 * @example
 * ```tsx
 * const { data, loading, error, refresh } = useTelemetryData({
 *   refreshInterval: 60000,
 *   limit: 100,
 * });
 *
 * if (loading) return <div>Loading...</div>;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return (
 *   <div>
 *     <p>Total Cost: ${data.totalCost.toFixed(2)}</p>
 *     <button onClick={refresh}>Refresh</button>
 *   </div>
 * );
 * ```
 */
export function useTelemetryData(
  options: UseTelemetryDataOptions = {}
): UseTelemetryDataResult {
  const {
    refreshInterval = 60000,
    limit = 100,
    workflowName = null,
    since = null,
  } = options;

  const [data, setData] = useState<TelemetryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTelemetry = useCallback(() => {
    // Build query parameters
    const params = new URLSearchParams();
    if (since) {
      params.set('since', since.toISOString());
    }
    if (workflowName) {
      params.set('workflow', workflowName);
    }
    if (limit) {
      params.set('limit', limit.toString());
    }

    // Fetch from API; state updates happen in the promise callbacks once
    // the response arrives, never synchronously
    return fetch(`/api/telemetry?${params.toString()}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((stats: TelemetryStats) => {
        setData(stats);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [workflowName, since, limit]);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    void fetchTelemetry();
  }, [fetchTelemetry]);

  // Initial fetch (loading already starts true, so no state reset needed here)
  useEffect(() => {
    void fetchTelemetry();
  }, [fetchTelemetry]);

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval <= 0) return;

    const intervalId = setInterval(() => {
      refresh();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [refreshInterval, refresh]);

  return {
    data,
    loading,
    error,
    refresh,
  };
}
