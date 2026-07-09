// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

type CachedAccess = {
  expiresAt: number;
  internalUrl: string;
};

export const DEFAULT_AUTHZ_CACHE_TTL_MS = 60_000;

function resolveTtlMs(): number {
  const raw = process.env.CHAT_AUTHZ_CACHE_TTL_MS;
  if (!raw) {
    return DEFAULT_AUTHZ_CACHE_TTL_MS;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : DEFAULT_AUTHZ_CACHE_TTL_MS;
}

// Process-local Map: each Next.js replica has its own cache. Acceptable because
// AIWB enforces authz on every miss and the TTL is short; cross-replica
// divergence only means slightly more AIWB lookups, never a stale allow.
const cache = new Map<string, CachedAccess>();

function cacheKey(userId: string, deploymentId: string): string {
  return `${userId}:${deploymentId}`;
}

function sweepExpired(now: number): void {
  cache.forEach((entry, key) => {
    if (entry.expiresAt <= now) {
      cache.delete(key);
    }
  });
}

export function getCachedAccess({
  userId,
  deploymentId,
}: {
  userId: string;
  deploymentId: string;
}): { internalUrl: string } | undefined {
  const key = cacheKey(userId, deploymentId);
  const entry = cache.get(key);
  const now = Date.now();
  if (!entry || entry.expiresAt <= now) {
    if (entry) {
      cache.delete(key);
    }
    return undefined;
  }
  return { internalUrl: entry.internalUrl };
}

export function setCachedAccess({
  userId,
  deploymentId,
  internalUrl,
  ttlMs,
}: {
  userId: string;
  deploymentId: string;
  internalUrl: string;
  ttlMs?: number;
}): void {
  const now = Date.now();
  sweepExpired(now);
  const effectiveTtl = ttlMs ?? resolveTtlMs();
  cache.set(cacheKey(userId, deploymentId), {
    internalUrl,
    expiresAt: now + effectiveTtl,
  });
}

export function clearAuthzCache(): void {
  cache.clear();
}
