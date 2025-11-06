// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getDeploymentStatus,
  isDeployed,
  isDeploying,
  isUndeploying,
  isNotDeployed,
  isDeploymentFailed,
  DeploymentStatus,
} from '@/utils/app/workload-deployment-status';
import { WorkloadStatus } from '@/types/enums/workloads';

describe('workload-deployment-status utils', () => {
  describe('getDeploymentStatus', () => {
    it('returns NOT_DEPLOYED when workload is null', () => {
      expect(getDeploymentStatus(null)).toBe(DeploymentStatus.NOT_DEPLOYED);
    });

    it('returns NOT_DEPLOYED when workload is undefined', () => {
      expect(getDeploymentStatus(undefined)).toBe(
        DeploymentStatus.NOT_DEPLOYED,
      );
    });

    it('returns NOT_DEPLOYED for DELETED status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.DELETED } as any),
      ).toBe(DeploymentStatus.NOT_DEPLOYED);
    });

    it('returns NOT_DEPLOYED for TERMINATED status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.TERMINATED } as any),
      ).toBe(DeploymentStatus.NOT_DEPLOYED);
    });

    it('returns DEPLOYING for PENDING status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.PENDING } as any),
      ).toBe(DeploymentStatus.DEPLOYING);
    });

    it('returns DEPLOYED for RUNNING status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.RUNNING } as any),
      ).toBe(DeploymentStatus.DEPLOYED);
    });

    it('returns UNDEPLOYING for DELETING status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.DELETING } as any),
      ).toBe(DeploymentStatus.UNDEPLOYING);
    });

    it('returns UNDEPLOYING for DELETE_FAILED status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.DELETE_FAILED } as any),
      ).toBe(DeploymentStatus.UNDEPLOYING);
    });

    it('returns DEPLOYMENT_FAILED for FAILED status', () => {
      expect(
        getDeploymentStatus({ status: WorkloadStatus.FAILED } as any),
      ).toBe(DeploymentStatus.DEPLOYMENT_FAILED);
    });
  });

  describe('helper functions', () => {
    it('isDeployed returns true for RUNNING status', () => {
      expect(isDeployed({ status: WorkloadStatus.RUNNING } as any)).toBe(true);
      expect(isDeployed({ status: WorkloadStatus.PENDING } as any)).toBe(false);
    });

    it('isDeploying returns true for PENDING status', () => {
      expect(isDeploying({ status: WorkloadStatus.PENDING } as any)).toBe(true);
      expect(isDeploying({ status: WorkloadStatus.RUNNING } as any)).toBe(
        false,
      );
    });

    it('isUndeploying returns true for DELETING status', () => {
      expect(isUndeploying({ status: WorkloadStatus.DELETING } as any)).toBe(
        true,
      );
      expect(isUndeploying({ status: WorkloadStatus.RUNNING } as any)).toBe(
        false,
      );
    });

    it('isNotDeployed returns true when no workload', () => {
      expect(isNotDeployed(null)).toBe(true);
      expect(isNotDeployed(undefined)).toBe(true);
      expect(isNotDeployed({ status: WorkloadStatus.RUNNING } as any)).toBe(
        false,
      );
    });

    it('isDeploymentFailed returns true for FAILED status', () => {
      expect(isDeploymentFailed({ status: WorkloadStatus.FAILED } as any)).toBe(
        true,
      );
      expect(
        isDeploymentFailed({ status: WorkloadStatus.RUNNING } as any),
      ).toBe(false);
    });
  });
});
