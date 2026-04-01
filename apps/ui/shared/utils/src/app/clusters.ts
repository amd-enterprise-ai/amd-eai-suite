// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Cluster } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';

export const doesClusterDataNeedToBeRefreshed = (clusters: Cluster[]) => {
  return clusters.some((c) => c.status == ClusterStatus.VERIFYING);
};
