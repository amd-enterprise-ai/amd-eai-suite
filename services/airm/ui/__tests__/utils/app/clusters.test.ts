// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { generateClustersMock } from '@/__mocks__/utils/cluster-mock';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { doesDataNeedToBeRefreshed } from '@/utils/app/clusters';

describe('doesDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if an entry has status Verifying', () => {
    const clusters = generateClustersMock(1);
    clusters[0].status = ClusterStatus.VERIFYING;
    expect(doesDataNeedToBeRefreshed(clusters)).toBe(true);
  });

  it('should return false if no entry has status Verifying', () => {
    const clusters = generateClustersMock(1);
    clusters[0].status = ClusterStatus.HEALTHY;
    expect(doesDataNeedToBeRefreshed(clusters)).toBe(false);
  });
});
