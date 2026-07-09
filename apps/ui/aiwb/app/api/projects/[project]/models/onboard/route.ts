// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for the custom model onboard endpoint.
 *
 * Browser-facing path:  POST /api/projects/{project}/models/onboard
 * Upstream AIWB API:    POST /v1/projects/{project_name}/models/onboard
 *
 * Anticipates the AIWB API exposing the custom model onboarding endpoint
 * under the project URL surface; the route will 404 against deployments
 * that have not yet shipped this endpoint.
 */

export { POST } from '@/lib/server/proxy-handler';
