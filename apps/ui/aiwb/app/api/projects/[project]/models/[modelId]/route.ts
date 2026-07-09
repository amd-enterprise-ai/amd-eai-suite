// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for the custom model detail, update, and delete endpoints.
 *
 * Browser-facing path:  GET|PATCH|DELETE /api/projects/{project}/models/{modelId}
 * Upstream AIWB API:    GET|PATCH|DELETE /v1/projects/{project_name}/models/{model_name}
 *
 * GET returns the full custom model (composed onboarding status plus the joined
 * AIMProfile); PATCH updates display metadata and/or the runtime profile; DELETE
 * removes an onboarded custom model (204) or returns 409 when deployments still
 * reference it.
 *
 * Handlers are thin wrappers (not `export { … } from`) so Next always registers
 * every verb for this route in dev and production builds.
 */

import type { NextRequest } from 'next/server';

import {
  DELETE as proxyDelete,
  GET as proxyGet,
  PATCH as proxyPatch,
} from '@/lib/server/proxy-handler';

export function GET(request: NextRequest) {
  return proxyGet(request);
}

export function PATCH(request: NextRequest) {
  return proxyPatch(request);
}

export function DELETE(request: NextRequest) {
  return proxyDelete(request);
}
