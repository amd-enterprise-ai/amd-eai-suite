// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF proxy: GET /api/projects/{project}/models/runtime-profile-options →
 * /v1/.../runtime-profile-options. Returns the base-image runtime matrix the
 * onboard wizard presets from. Its own folder so Next routes it ahead of the
 * sibling `[modelId]` route; thin wrapper so GET is always registered.
 */

import type { NextRequest } from 'next/server';

import { GET as proxyGet } from '@/lib/server/proxy-handler';

export function GET(request: NextRequest) {
  return proxyGet(request);
}
