// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { generateClustersMock } from '@/__mocks__/utils/cluster-mock';
import { ClusterStatus } from '@amdenterpriseai/types';
import { doesClusterDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { describe, it, expect } from 'vitest';

describe('doesDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesClusterDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if an entry has status Verifying', () => {
    const clusters = generateClustersMock(1);
    clusters[0].status = ClusterStatus.VERIFYING;
    expect(doesClusterDataNeedToBeRefreshed(clusters)).toBe(true);
  });

  it('should return false if no entry has status Verifying', () => {
    const clusters = generateClustersMock(1);
    clusters[0].status = ClusterStatus.HEALTHY;
    expect(doesClusterDataNeedToBeRefreshed(clusters)).toBe(false);
  });
});
