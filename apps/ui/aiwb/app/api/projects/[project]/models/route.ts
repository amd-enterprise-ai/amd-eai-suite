// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for listing custom models in a project.
 *
 * Browser-facing path:  GET /api/projects/{project}/models
 * Upstream AIWB API:    GET /v1/projects/{project}/models
 */

export { GET } from '@/lib/server/proxy-handler';
