// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for copying a project-scoped custom model.
 *
 * Browser-facing path:  POST /api/projects/{project}/models/{modelId}/copy
 * Upstream AIWB API:    POST /v1/projects/{project}/models/{modelId}/copy
 */

export { POST } from '@/lib/server/proxy-handler';
