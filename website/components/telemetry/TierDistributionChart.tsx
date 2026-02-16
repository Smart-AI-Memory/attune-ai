/**
 * Tier Distribution Chart - Usage by tier visualization
 *
 * Displays tier distribution with:
 * - Pie chart showing tier percentages
 * - Color-coded by tier (cheap=green, capable=blue, premium=purple)
 * - Interactive tooltips with cost and call count
 *
 * **Implementation:** Sprint 2 (Week 2)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

'use client';

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TierDistributionChartProps {
  /** Tier distribution data */
  data: TierData[];
  /** Chart height in pixels */
  height?: number;
}

interface TierData {
  tier: string;
  count: number;
  cost: number;
  percent: number;
}

const TIER_COLORS = {
  cheap: '#73c991',
  capable: '#4a9eff',
  premium: '#b57edc',
};

export default function TierDistributionChart({
  data,
  height = 300,
}: TierDistributionChartProps) {
  // Prepare data for pie chart
  const chartData = data.map((item) => ({
    name: item.tier.charAt(0).toUpperCase() + item.tier.slice(1),
    value: item.count,
    cost: item.cost,
    percent: item.percent,
  }));

  return (
    <div className="tier-distribution-chart">
      <h3 className="text-lg font-semibold text-gray-700 mb-4">
        Tier Distribution
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent ?? 0).toFixed(1)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  TIER_COLORS[
                    entry.name.toLowerCase() as keyof typeof TIER_COLORS
                  ] || '#999'
                }
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #ddd',
              borderRadius: '4px',
              padding: '8px',
            }}
            formatter={(value, name, props) => {
              if (typeof value !== 'number') return [value, name];
              const { cost } = props.payload;
              return [
                <>
                  <div>Calls: {value}</div>
                  <div>Cost: ${cost?.toFixed?.(4) ?? '0.0000'}</div>
                </>,
                name,
              ];
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
