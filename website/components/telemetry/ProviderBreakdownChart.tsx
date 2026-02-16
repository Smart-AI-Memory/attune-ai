/**
 * Provider Breakdown Chart - Cost by provider visualization
 *
 * Displays provider usage with:
 * - Bar chart showing cost per provider
 * - Call count overlay
 * - Success rate indicators
 * - Interactive tooltips
 *
 * **Implementation:** Sprint 2 (Week 2)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ProviderBreakdownChartProps {
  /** Provider usage data */
  data: ProviderData[];
  /** Chart height in pixels */
  height?: number;
}

interface ProviderData {
  provider: string;
  callCount: number;
  totalCost: number;
  avgCost: number;
  errorCount: number;
  successRate: number;
}

export default function ProviderBreakdownChart({
  data,
  height = 300,
}: ProviderBreakdownChartProps) {
  // Prepare data for bar chart
  const chartData = data.map((item) => ({
    name: item.provider.charAt(0).toUpperCase() + item.provider.slice(1),
    cost: parseFloat(item.totalCost.toFixed(4)),
    calls: item.callCount,
    successRate: item.successRate * 100,
  }));

  return (
    <div className="provider-breakdown-chart">
      <h3 className="text-lg font-semibold text-gray-700 mb-4">
        Cost by Provider
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis dataKey="name" stroke="#666" style={{ fontSize: '12px' }} />
          <YAxis
            stroke="#666"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #ddd',
              borderRadius: '4px',
              padding: '8px',
            }}
            formatter={(value, name, props) => {
              if (typeof value !== 'number') return [value, name];
              const { calls, successRate } = props.payload;
              if (name === 'cost') {
                return [
                  <>
                    <div>Cost: ${value.toFixed(4)}</div>
                    <div>Calls: {calls}</div>
                    <div>Success: {successRate.toFixed(1)}%</div>
                  </>,
                  'Provider Stats',
                ];
              }
              return [value, name];
            }}
          />
          <Legend />
          <Bar dataKey="cost" fill="#4a9eff" name="Total Cost" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
