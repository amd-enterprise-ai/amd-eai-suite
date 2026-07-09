// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * BFF route for the custom model preview endpoint.
 *
 * Browser-facing path:  POST /api/projects/{project}/models/preview
 * Upstream AIWB API:    POST /v1/projects/{project_name}/models/preview
 *
 * Anticipates the AIWB API aligning custom-model routes under the
 * project URL surface; until then this route will 404 against deployments
 * that still serve preview at /v1/namespaces/{namespace}/models/preview.
 */

export { POST } from '@/lib/server/proxy-handler';
