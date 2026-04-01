// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';
import { RouteError } from '@amdenterpriseai/utils/server';

/**
 * Extracts the API path after /api/ from the request URL.
 * Example: /api/aims/123/deploy -> aims/123/deploy
 */
export function extractApiPath(req: NextRequest): string {
  const pathname = req.nextUrl.pathname;
  const match = pathname.match(/^\/api\/(.*)$/);
  if (!match || !match[1]) {
    throw new RouteError(400, 'Invalid API path');
  }
  return match[1];
}
