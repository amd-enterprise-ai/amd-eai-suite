// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for the custom model onboarding-status endpoint.
 *
 * Browser-facing path:  GET /api/projects/{project}/models/{modelId}/onboarding
 * Upstream AIWB API:    GET /v1/projects/{project_name}/models/{model_id}/onboarding
 *
 * Anticipates the AIWB API exposing the onboarding-status endpoint under the
 * project URL surface; the route will 404 against deployments that have not
 * yet shipped this endpoint.
 */

export { GET } from '@/lib/server/proxy-handler';
