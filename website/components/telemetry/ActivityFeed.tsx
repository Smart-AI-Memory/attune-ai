/**
 * Activity Feed Component
 *
 * Displays recent LLM calls with filtering and click-through to source files.
 *
 * **Features:**
 * - Chronological list of recent LLM calls
 * - Filter by provider, tier, workflow, success/failure
 * - Color-coded by tier (cheap=green, capable=blue, premium=purple)
 * - Click to view call details
 * - Jump to source file (if workflow context available)
 * - Real-time updates (60-second auto-refresh)
 *
 * **Implementation Status:** Sprint 1 (Week 1)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React, { useState } from 'react';
import type { LLMCallRecord } from './hooks/useTelemetryData';

interface ActivityFeedProps {
  /** Recent LLM calls to display */
  calls: LLMCallRecord[];
  /** Maximum number of calls to display */
  limit?: number;
}

export default function ActivityFeed({ calls, limit = 50 }: ActivityFeedProps) {
  const [filterProvider, setFilterProvider] = useState<string | null>(null);
  const [filterTier, setFilterTier] = useState<string | null>(null);
  const [filterSuccess, setFilterSuccess] = useState<boolean | null>(null);

  // Apply filters
  let filteredCalls = calls;
  if (filterProvider) {
    filteredCalls = filteredCalls.filter((c) => c.provider === filterProvider);
  }
  if (filterTier) {
    filteredCalls = filteredCalls.filter((c) => c.tier === filterTier);
  }
  if (filterSuccess !== null) {
    filteredCalls = filteredCalls.filter((c) => c.success === filterSuccess);
  }

  // Limit results
  const displayedCalls = filteredCalls.slice(0, limit);

  return (
    <div className="activity-feed">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-700">Recent Activity</h2>
        <FilterControls
          filterProvider={filterProvider}
          setFilterProvider={setFilterProvider}
          filterTier={filterTier}
          setFilterTier={setFilterTier}
          filterSuccess={filterSuccess}
          setFilterSuccess={setFilterSuccess}
        />
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {displayedCalls.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">No activity yet</p>
            <p className="text-sm">
              Run a workflow to see LLM calls appear here
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {displayedCalls.map((call) => (
              <CallItem key={call.callId} call={call} />
            ))}
          </div>
        )}
      </div>

      {filteredCalls.length > limit && (
        <p className="text-sm text-gray-500 mt-2 text-center">
          Showing {limit} of {filteredCalls.length} calls
        </p>
      )}
    </div>
  );
}

/**
 * Filter Controls Component
 */
interface FilterControlsProps {
  filterProvider: string | null;
  setFilterProvider: (provider: string | null) => void;
  filterTier: string | null;
  setFilterTier: (tier: string | null) => void;
  filterSuccess: boolean | null;
  setFilterSuccess: (success: boolean | null) => void;
}

function FilterControls({
  filterProvider,
  setFilterProvider,
  filterTier,
  setFilterTier,
  filterSuccess,
  setFilterSuccess,
}: FilterControlsProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <select
        value={filterProvider || ''}
        onChange={(e) => setFilterProvider(e.target.value || null)}
        className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Providers</option>
        <option value="anthropic">Anthropic</option>
        <option value="openai">OpenAI</option>
        <option value="ollama">Ollama</option>
      </select>

      <select
        value={filterTier || ''}
        onChange={(e) => setFilterTier(e.target.value || null)}
        className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Tiers</option>
        <option value="cheap">Cheap</option>
        <option value="capable">Capable</option>
        <option value="premium">Premium</option>
      </select>

      <select
        value={filterSuccess === null ? '' : filterSuccess ? 'success' : 'failure'}
        onChange={(e) =>
          setFilterSuccess(
            e.target.value === '' ? null : e.target.value === 'success'
          )
        }
        className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Status</option>
        <option value="success">Success</option>
        <option value="failure">Failure</option>
      </select>
    </div>
  );
}

/**
 * Call Item Component
 */
interface CallItemProps {
  call: LLMCallRecord;
}

function CallItem({ call }: CallItemProps) {
  const tierColors = {
    cheap: 'bg-green-100 text-green-800 border-green-300',
    capable: 'bg-blue-100 text-blue-800 border-blue-300',
    premium: 'bg-purple-100 text-purple-800 border-purple-300',
  };

  const tierColor = tierColors[call.tier as keyof typeof tierColors] || 'bg-gray-100 text-gray-800 border-gray-300';

  return (
    <div className="call-item p-4 hover:bg-gray-50 transition-colors cursor-pointer">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-xs font-semibold rounded border ${tierColor}`}>
            {call.tier.toUpperCase()}
          </span>
          <span className="text-sm font-medium text-gray-700">
            {call.provider}/{call.modelId}
          </span>
          {call.fallbackUsed && (
            <span className="px-2 py-1 text-xs font-semibold rounded bg-orange-100 text-orange-800 border border-orange-300">
              FALLBACK
            </span>
          )}
          {!call.success && (
            <span className="px-2 py-1 text-xs font-semibold rounded bg-red-100 text-red-800 border border-red-300">
              FAILED
            </span>
          )}
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-gray-800">
            ${call.estimatedCost.toFixed(4)}
          </p>
          <p className="text-xs text-gray-500">{call.latencyMs}ms</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-600">
        <div>
          {call.workflowName && (
            <span className="font-medium">{call.workflowName}</span>
          )}
          {call.stepName && (
            <span className="text-gray-500"> → {call.stepName}</span>
          )}
        </div>
        <div className="text-xs text-gray-500">
          {formatTimestamp(call.timestamp)}
        </div>
      </div>

      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
        <span>Input: {call.inputTokens.toLocaleString()} tokens</span>
        <span>Output: {call.outputTokens.toLocaleString()} tokens</span>
        {call.retryCount > 0 && (
          <span className="text-orange-600">
            Retries: {call.retryCount}
          </span>
        )}
      </div>

      {!call.success && call.errorMessage && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <span className="font-semibold">{call.errorType}:</span>{' '}
          {call.errorMessage}
        </div>
      )}
    </div>
  );
}

/**
 * Format ISO timestamp to relative time
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString();
}
