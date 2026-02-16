/**
 * Cost Trend Chart - Daily cost visualization
 *
 * Displays LLM cost trends over time with:
 * - Line chart showing daily costs
 * - Cumulative cost overlay
 * - Interactive tooltips
 * - Date range filtering
 *
 * **Implementation:** Sprint 2 (Week 2)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface CostTrendChartProps {
  /** Daily cost data points */
  data: DailyCostData[];
  /** Chart height in pixels */
  height?: number;
}

interface DailyCostData {
  date: string;
  cost: number;
  calls: number;
}

export default function CostTrendChart({ data, height = 300 }: CostTrendChartProps) {
  // Calculate cumulative cost
  const dataWithCumulative = data.map((item, index) => ({
    ...item,
    cumulativeCost: data
      .slice(0, index + 1)
      .reduce((sum, d) => sum + d.cost, 0),
  }));

  return (
    <div className="cost-trend-chart">
      <h3 className="text-lg font-semibold text-gray-700 mb-4">
        Cost Trend (Last 7 Days)
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={dataWithCumulative}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="date"
            stroke="#666"
            style={{ fontSize: '12px' }}
          />
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
            formatter={(value) => typeof value === 'number' ? `$${value.toFixed(4)}` : value}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="cost"
            stroke="#4a9eff"
            strokeWidth={2}
            name="Daily Cost"
            dot={{ fill: '#4a9eff', r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="cumulativeCost"
            stroke="#b57edc"
            strokeWidth={2}
            strokeDasharray="5 5"
            name="Cumulative Cost"
            dot={{ fill: '#b57edc', r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
