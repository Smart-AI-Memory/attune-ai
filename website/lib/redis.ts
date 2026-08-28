/**
 * Redis Client for Website Features
 *
 * Provides Redis connectivity for:
 * - Debug Wizard pattern storage
 * - Healthcare wizard session management
 * - Usage tracking and rate limiting
 *
 * Uses ioredis for standard Redis connections.
 * Gracefully falls back to in-memory storage when Redis is unavailable.
 */

import Redis from 'ioredis';

// ============================================================================
// Environment-Aware Key Prefixing
// ============================================================================

/**
 * Get the environment prefix for Redis keys
 * - Production (main branch on Vercel): 'prod:'
 * - Preview (PR deployments on Vercel): 'preview:'
 * - Development (local): 'dev:'
 */
function getEnvironmentPrefix(): string {
  const vercelEnv = process.env.VERCEL_ENV;

  if (vercelEnv === 'production') {
    return 'prod:';
  } else if (vercelEnv === 'preview') {
    return 'preview:';
  } else {
    // Local development or unset
    return 'dev:';
  }
}

/**
 * Prefix a Redis key with the environment
 * This ensures production and preview data are isolated
 */
function prefixKey(key: string): string {
  return `${getEnvironmentPrefix()}${key}`;
}

// Export for debugging/testing
export function getCurrentEnvironment(): { env: string; prefix: string } {
  return {
    env: process.env.VERCEL_ENV || 'development',
    prefix: getEnvironmentPrefix(),
  };
}

// Types for bug patterns
export interface StoredBugPattern {
  id: string;
  date: string;
  error_type: string;
  error_message: string;
  file_path: string;
  file_type: string;
  root_cause: string;
  fix_applied: string;
  fix_code: string | null;
  resolution_time_minutes: number;
  user_id?: string;
}

export interface WizardSession {
  wizard_id: string;
  wizard_type: string;
  current_step: number;
  total_steps: number;
  collected_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

// In-memory fallback storage
const memoryStore = {
  patterns: new Map<string, StoredBugPattern>(),
  sessions: new Map<string, WizardSession>(),
  usage: new Map<string, number>(),
};

// Redis client singleton
let redisClient: Redis | null = null;
let redisAvailable = false;
let connectionAttempted = false;

/**
 * Initialize Redis client
 */
function getRedisClient(): Redis | null {
  if (redisClient) return redisClient;
  if (connectionAttempted && !redisAvailable) return null;

  connectionAttempted = true;
  const redisUrl = process.env.REDIS_URL;

  if (!redisUrl) {
    console.log('REDIS_URL not set - using in-memory storage');
    redisAvailable = false;
    return null;
  }

  try {
    redisClient = new Redis(redisUrl, {
      maxRetriesPerRequest: 3,
      connectTimeout: 10000,
      retryStrategy: (times) => {
        if (times > 3) {
          console.error('Redis max retries reached');
          return null; // Stop retrying
        }
        return Math.min(times * 100, 3000);
      },
    });

    // Handle connection events
    redisClient.on('ready', () => {
      console.log('Redis connected successfully');
      redisAvailable = true;
    });

    redisClient.on('error', (err) => {
      console.error('Redis connection error:', err.message);
      redisAvailable = false;
    });

    redisClient.on('close', () => {
      console.log('Redis connection closed');
      redisAvailable = false;
    });

    // Check if already connected (ioredis connects automatically)
    if (redisClient.status === 'ready') {
      redisAvailable = true;
    }

    return redisClient;
  } catch (error) {
    console.error('Failed to initialize Redis client:', error);
    redisAvailable = false;
    return null;
  }
}

/**
 * Wait for Redis connection (with timeout)
 */
async function waitForConnection(timeoutMs: number = 2000): Promise<boolean> {
  const redis = getRedisClient();
  if (!redis) return false;
  if (redisAvailable) return true;

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      resolve(false);
    }, timeoutMs);

    const checkReady = () => {
      if (redis.status === 'ready') {
        clearTimeout(timeout);
        redisAvailable = true;
        resolve(true);
      }
    };

    redis.once('ready', () => {
      clearTimeout(timeout);
      redisAvailable = true;
      resolve(true);
    });

    // Check immediately in case already ready
    checkReady();
  });
}

/**
 * Check if Redis is available
 */
export function isRedisAvailable(): boolean {
  getRedisClient();
  return redisAvailable;
}

// ============================================================================
// Bug Pattern Storage
// ============================================================================

// Base keys (will be prefixed with environment)
const PATTERNS_BASE_KEY = 'debug_wizard:patterns';
const PATTERNS_INDEX_BASE_KEY = 'debug_wizard:patterns:by_type';

// Dynamic key getters
const getPatternsKey = () => prefixKey(PATTERNS_BASE_KEY);
const getPatternsIndexKey = () => prefixKey(PATTERNS_INDEX_BASE_KEY);

/**
 * Store a resolved bug pattern
 */
export async function storeBugPattern(pattern: StoredBugPattern): Promise<boolean> {
  // Wait for Redis connection
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const patternsKey = getPatternsKey();
      const patternsIndexKey = getPatternsIndexKey();

      // Store pattern by ID
      await redis.hset(patternsKey, pattern.id, JSON.stringify(pattern));

      // Index by error type for faster lookups
      await redis.sadd(`${patternsIndexKey}:${pattern.error_type}`, pattern.id);

      // Keep only last 1000 patterns (FIFO)
      const allPatterns = await redis.hkeys(patternsKey);
      if (allPatterns.length > 1000) {
        const toRemove = allPatterns.slice(0, allPatterns.length - 1000);
        for (const id of toRemove) {
          await redis.hdel(patternsKey, id);
        }
      }

      return true;
    } catch (error) {
      console.error('Redis storeBugPattern error:', error);
      // Fall through to memory storage
    }
  }

  // Fallback to memory
  memoryStore.patterns.set(pattern.id, pattern);

  // Keep only last 100 in memory
  if (memoryStore.patterns.size > 100) {
    const keys = Array.from(memoryStore.patterns.keys());
    for (let i = 0; i < keys.length - 100; i++) {
      memoryStore.patterns.delete(keys[i]);
    }
  }

  return true;
}

/**
 * Find similar bug patterns
 */
export async function findSimilarPatterns(
  errorType: string,
  fileType: string,
  maxResults: number = 5
): Promise<StoredBugPattern[]> {
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const patternsKey = getPatternsKey();
      const patternsIndexKey = getPatternsIndexKey();

      // Get pattern IDs for this error type
      const patternIds = await redis.smembers(`${patternsIndexKey}:${errorType}`);

      if (patternIds.length === 0) {
        // Fall back to getting all patterns
        const allPatterns = await redis.hgetall(patternsKey);
        if (!allPatterns || Object.keys(allPatterns).length === 0) return [];

        return Object.values(allPatterns)
          .map(p => JSON.parse(p) as StoredBugPattern)
          .filter(p => p.error_type === errorType || p.file_type === fileType)
          .slice(0, maxResults);
      }

      // Get pattern details
      const patterns: StoredBugPattern[] = [];
      for (const id of patternIds.slice(0, maxResults * 2)) {
        const patternStr = await redis.hget(patternsKey, id);
        if (patternStr) {
          patterns.push(JSON.parse(patternStr));
        }
      }

      // Sort by relevance (same file type first)
      return patterns
        .sort((a, b) => {
          const aScore = (a.file_type === fileType ? 1 : 0);
          const bScore = (b.file_type === fileType ? 1 : 0);
          return bScore - aScore;
        })
        .slice(0, maxResults);
    } catch (error) {
      console.error('Redis findSimilarPatterns error:', error);
      // Fall through to memory
    }
  }

  // Fallback to memory
  return Array.from(memoryStore.patterns.values())
    .filter(p => p.error_type === errorType || p.file_type === fileType)
    .slice(0, maxResults);
}

/**
 * Get pattern statistics
 */
export async function getPatternStats(): Promise<{
  total: number;
  byType: Record<string, number>;
  mode: 'redis' | 'memory';
  environment?: string;
  keyPrefix?: string;
}> {
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const patternsKey = getPatternsKey();
      const allPatterns = await redis.hgetall(patternsKey);
      const patterns = allPatterns
        ? Object.values(allPatterns).map(p => JSON.parse(p) as StoredBugPattern)
        : [];

      const byType: Record<string, number> = {};
      for (const p of patterns) {
        byType[p.error_type] = (byType[p.error_type] || 0) + 1;
      }

      const envInfo = getCurrentEnvironment();
      return {
        total: patterns.length,
        byType,
        mode: 'redis',
        environment: envInfo.env,
        keyPrefix: envInfo.prefix,
      };
    } catch (error) {
      console.error('Redis getPatternStats error:', error);
    }
  }

  // Fallback to memory
  const byType: Record<string, number> = {};
  for (const p of memoryStore.patterns.values()) {
    byType[p.error_type] = (byType[p.error_type] || 0) + 1;
  }

  const envInfo = getCurrentEnvironment();
  return {
    total: memoryStore.patterns.size,
    byType,
    mode: 'memory',
    environment: envInfo.env,
    keyPrefix: envInfo.prefix,
  };
}

// ============================================================================
// Wizard Session Management
// ============================================================================

// Base key (will be prefixed with environment)
const SESSIONS_BASE_KEY = 'wizard:sessions';
const SESSION_TTL = 3600; // 1 hour

// Dynamic key getter
const getSessionsKey = () => prefixKey(SESSIONS_BASE_KEY);

/**
 * Store wizard session
 */
export async function storeWizardSession(session: WizardSession): Promise<boolean> {
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const sessionsKey = getSessionsKey();
      await redis.setex(
        `${sessionsKey}:${session.wizard_id}`,
        SESSION_TTL,
        JSON.stringify(session)
      );
      return true;
    } catch (error) {
      console.error('Redis storeWizardSession error:', error);
    }
  }

  // Fallback to memory
  memoryStore.sessions.set(session.wizard_id, session);
  return true;
}

/**
 * Get wizard session
 */
export async function getWizardSession(wizardId: string): Promise<WizardSession | null> {
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const sessionsKey = getSessionsKey();
      const sessionStr = await redis.get(`${sessionsKey}:${wizardId}`);
      if (sessionStr) {
        return JSON.parse(sessionStr);
      }
      return null;
    } catch (error) {
      console.error('Redis getWizardSession error:', error);
    }
  }

  // Fallback to memory
  return memoryStore.sessions.get(wizardId) || null;
}

/**
 * Update wizard session
 */
export async function updateWizardSession(
  wizardId: string,
  updates: Partial<WizardSession>
): Promise<WizardSession | null> {
  const existing = await getWizardSession(wizardId);
  if (!existing) return null;

  const updated: WizardSession = {
    ...existing,
    ...updates,
    updated_at: new Date().toISOString(),
  };

  await storeWizardSession(updated);
  return updated;
}

/**
 * Delete wizard session
 */
export async function deleteWizardSession(wizardId: string): Promise<boolean> {
  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const sessionsKey = getSessionsKey();
      await redis.del(`${sessionsKey}:${wizardId}`);
      return true;
    } catch (error) {
      console.error('Redis deleteWizardSession error:', error);
    }
  }

  // Fallback to memory
  memoryStore.sessions.delete(wizardId);
  return true;
}

// ============================================================================
// Usage Tracking
// ============================================================================

// Base key (will be prefixed with environment)
const USAGE_BASE_KEY = 'usage:daily';

// Dynamic key getter
const getUsageKey = () => prefixKey(USAGE_BASE_KEY);

/**
 * Increment usage counter for a user/IP
 */
export async function incrementUsage(
  identifier: string,
  feature: string
): Promise<number> {
  const today = new Date().toISOString().slice(0, 10);
  const usageKey = getUsageKey();
  const key = `${usageKey}:${today}:${feature}:${identifier}`;

  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const count = await redis.incr(key);
      // Expire at end of day
      await redis.expire(key, 86400);
      return count;
    } catch (error) {
      console.error('Redis incrementUsage error:', error);
    }
  }

  // Fallback to memory
  const current = memoryStore.usage.get(key) || 0;
  memoryStore.usage.set(key, current + 1);
  return current + 1;
}

/**
 * Get current usage count
 */
export async function getUsage(
  identifier: string,
  feature: string
): Promise<number> {
  const today = new Date().toISOString().slice(0, 10);
  const usageKey = getUsageKey();
  const key = `${usageKey}:${today}:${feature}:${identifier}`;

  const connected = await waitForConnection();
  const redis = getRedisClient();

  if (redis && connected) {
    try {
      const count = await redis.get(key);
      return parseInt(count as string) || 0;
    } catch (error) {
      console.error('Redis getUsage error:', error);
    }
  }

  // Fallback to memory
  return memoryStore.usage.get(key) || 0;
}

/**
 * Check if usage limit exceeded
 */
export async function isUsageLimitExceeded(
  identifier: string,
  feature: string,
  limit: number
): Promise<boolean> {
  const usage = await getUsage(identifier, feature);
  return usage >= limit;
}
