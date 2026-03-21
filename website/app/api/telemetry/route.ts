/**
 * Telemetry API Route
 *
 * Serves telemetry data from `.attune/*.jsonl` files.
 *
 * **Endpoints:**
 * - GET /api/telemetry - Get aggregated telemetry statistics
 * - GET /api/telemetry?since=ISO_DATE - Filter by date
 * - GET /api/telemetry?workflow=NAME - Filter by workflow
 * - GET /api/telemetry?provider=NAME - Filter by provider
 *
 * **Implementation Status:** Sprint 1 (Week 1)
 *
 * Copyright 2025 Smart-AI-Memory
 * Licensed under Apache 2.0
 */

import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import { loadTelemetryData } from '@/lib/telemetry/parser';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    // Parse query parameters
    const sinceParam = searchParams.get('since');
    const workflowName = searchParams.get('workflow');
    const provider = searchParams.get('provider');
    const limitParam = searchParams.get('limit');

    const since = sinceParam ? new Date(sinceParam) : undefined;
    const limit = limitParam ? parseInt(limitParam, 10) : 1000;

    // Determine .attune directory path
    // In production, this should be configurable via environment variable
    const attuneDir = process.env.ATTUNE_DIR || path.join(process.cwd(), '..', '.attune');

    // Load telemetry data
    const stats = loadTelemetryData(attuneDir, {
      since,
      workflowName: workflowName || undefined,
      provider: provider || undefined,
      limit,
    });

    return NextResponse.json(stats);
  } catch (error) {
    console.error('Failed to load telemetry data:', error);

    return NextResponse.json(
      {
        error: 'Failed to load telemetry data',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get('origin') || '';
  const allowedOrigins = [
    'https://smartaimemory.com',
    'https://www.smartaimemory.com',
    ...(process.env.NODE_ENV === 'development' ? ['http://localhost:3000'] : []),
  ];
  const corsOrigin = allowedOrigins.includes(origin) ? origin : allowedOrigins[0];

  return NextResponse.json(
    {},
    {
      headers: {
        'Access-Control-Allow-Origin': corsOrigin,
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    }
  );
}
