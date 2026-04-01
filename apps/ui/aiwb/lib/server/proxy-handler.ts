// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';
import {
  authenticateRoute,
  handleError,
  proxyRequest,
  RouteError,
} from '@amdenterpriseai/utils/server';

import { extractApiPath } from './route-utils';

// Allow URL-encoded IDs (e.g. %2F), dots, hyphens and underscores.
// Keep this constrained to avoid special characters used in traversal/protocol tricks.
const VALID_PATH_SEGMENT = /^[a-zA-Z0-9_.%-]+$/;

/**
 * Validates path segments to prevent SSRF attacks.
 * - Blocks path traversal attempts (../, .., etc.)
 * - Blocks protocol injection (http://, https://, file://, etc.)
 * - Blocks empty segments and special characters
 * - Only allows alphanumeric characters, hyphens, and underscores
 */
export function validatePathSegments(segments: string[]): void {
  for (const segment of segments) {
    // Block empty segments (would result in double slashes)
    if (!segment || segment.trim() === '') {
      throw new RouteError(400, 'Invalid path: empty segment');
    }

    // Block path traversal
    if (segment === '.' || segment === '..') {
      throw new RouteError(400, 'Invalid path: path traversal not allowed');
    }

    // Block protocol injection attempts
    if (segment.includes(':') || segment.includes('//')) {
      throw new RouteError(400, 'Invalid path: invalid characters');
    }

    // Only allow safe characters (including URL-encoded ids)
    if (!VALID_PATH_SEGMENT.test(segment)) {
      throw new RouteError(
        400,
        `Invalid path segment: only alphanumeric characters, dots, percents, hyphens, and underscores are allowed`,
      );
    }

    // Block percent-encoded whitespace (e.g. %20 for space, %09 for tab)
    if (/\s/.test(decodeURIComponent(segment))) {
      throw new RouteError(
        400,
        `Invalid path segment: only alphanumeric characters, dots, percents, hyphens, and underscores are allowed`,
      );
    }
  }
}

/**
 * Generic proxy handler that forwards requests to the backend API.
 * Auto-detects the path from the request URL.
 *
 * Example: POST /api/aims/232332/deploy → AIRM_API_SERVICE_URL/v1/aims/232332/deploy
 */
async function proxyHandler(req: NextRequest) {
  try {
    // Extract and validate path from URL
    const apiPath = extractApiPath(req);
    const segments = apiPath.split('/').filter(Boolean);

    // Validate all path segments to prevent SSRF attacks
    validatePathSegments(segments);

    const { accessToken } = await authenticateRoute();
    const baseUrl = `${process.env.AIRM_API_SERVICE_URL}/v1/${apiPath}`;

    // Additional safety check: ensure constructed URL is valid and points to expected host
    const targetUrl = new URL(baseUrl);
    const expectedUrl = new URL(process.env.AIRM_API_SERVICE_URL as string);
    if (targetUrl.origin !== expectedUrl.origin) {
      throw new RouteError(400, 'Invalid path: URL manipulation detected');
    }

    const json = await proxyRequest(req, baseUrl, accessToken as string);

    return NextResponse.json(json);
  } catch (error) {
    return handleError(error);
  }
}

export function GET(req: NextRequest) {
  return proxyHandler(req);
}

export function POST(req: NextRequest) {
  return proxyHandler(req);
}

export function PUT(req: NextRequest) {
  return proxyHandler(req);
}

export function DELETE(req: NextRequest) {
  return proxyHandler(req);
}

export function PATCH(req: NextRequest) {
  return proxyHandler(req);
}
