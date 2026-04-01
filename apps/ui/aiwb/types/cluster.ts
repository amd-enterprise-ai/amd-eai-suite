// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QuotaResourceType } from '@amdenterpriseai/types';

export type ClusterResources = {
  availableResources: QuotaResourceType;
  totalNodeCount: number;
};
