// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Cluster } from '@/types/clusters';
import { ClusterStatus } from '@/types/enums/cluster-status';

export const doesDataNeedToBeRefreshed = (clusters: Cluster[]) => {
  return clusters.some((c) => c.status == ClusterStatus.VERIFYING);
};
